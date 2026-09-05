"""
Inspections API — Automated LMPC Verification Workflow.

Workflow:
  1. POST /inspections          → create inspection (status: PENDING)
  2. POST /inspections/{id}/images → upload image(s); pipeline auto-starts
     status transitions: PENDING → PROCESSING → COMPLIANT | NON_COMPLIANT
  3. GET  /inspections/{id}     → poll for results (fields, findings, verdict)

No manual submit or admin review step.
"""

import asyncio
import os
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status, BackgroundTasks, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, get_db, require_role
from app.models.user import User
from app.models.inspection import Inspection, Image, ProductCategory, RuleVersion, AuditLog
from app.schemas.inspection import (
    InspectionCreate,
    InspectionDetailOut,
    InspectionOut,
    ImageUploadResponse,
)
from app.services.pipeline_svc import run_pipeline_for_image
from app.config import settings

router = APIRouter(prefix="/inspections", tags=["inspections"])

# Statuses in which the pipeline is still running (no new uploads allowed)
_LOCKED_STATUSES = {"PROCESSING", "COMPLIANT", "NON_COMPLIANT", "PROCESSING_FAILED"}


def _check_access(inspection: Inspection, current_user: User):
    """Officers can only access their own inspections; Admins see everything."""
    user_roles = {r.role_name.upper() for r in current_user.roles}
    if "ADMIN" not in user_roles and inspection.officer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: you do not have permission to access this inspection.",
        )


# ── List inspections ─────────────────────────────────────────────────────────

@router.get("", response_model=list[InspectionOut])
async def list_inspections(
    status_filter: str | None = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, le=100),
    current_user: User = Depends(require_role("OFFICER", "ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    """
    Officers see only their own inspections.
    Admins see all inspections across all officers.
    """
    q = select(Inspection).options(selectinload(Inspection.product_category))
    if "ADMIN" not in {r.role_name for r in current_user.roles}:
        q = q.where(Inspection.officer_id == current_user.id)
    if status_filter:
        q = q.where(Inspection.status == status_filter.upper())
    q = q.order_by(Inspection.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


# ── Create inspection ────────────────────────────────────────────────────────

@router.post("", response_model=InspectionOut, status_code=status.HTTP_201_CREATED)
async def create_inspection(
    inspection_in: InspectionCreate,
    current_user: User = Depends(require_role("OFFICER", "ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new inspection record (status: PENDING). Upload images next."""
    category = await db.get(ProductCategory, inspection_in.product_category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product category '{inspection_in.product_category_id}' not found.",
        )

    result = await db.execute(
        select(RuleVersion).where(RuleVersion.is_active.is_(True)).limit(1)
    )
    rule_version = result.scalar_one_or_none()
    if not rule_version:
        raise HTTPException(status_code=400, detail="No active rule version found in the system.")

    new_inspection = Inspection(
        officer_id=current_user.id,
        product_category_id=inspection_in.product_category_id,
        rule_version_id=rule_version.id,
        status="PENDING",
    )
    db.add(new_inspection)
    await db.commit()
    await db.refresh(new_inspection, ["product_category"])
    return new_inspection


# ── Upload image → triggers pipeline automatically ───────────────────────────

@router.post("/{inspection_id}/images", response_model=ImageUploadResponse)
async def upload_image(
    inspection_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(require_role("OFFICER", "ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload an image for an inspection.
    The LMPC verification pipeline starts automatically in the background.
    Once all images finish processing, the inspection is automatically
    stamped COMPLIANT or NON_COMPLIANT — no manual step required.
    """
    result = await db.execute(
        select(Inspection).where(Inspection.id == inspection_id)
    )
    inspection = result.scalar_one_or_none()
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found.")

    _check_access(inspection, current_user)

    # Only allow uploads while the inspection is still PENDING
    if inspection.status in _LOCKED_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot upload images: inspection status is '{inspection.status}'. "
                "Pipeline has already run. Start a new inspection to re-verify."
            ),
        )

    # Validate file type
    allowed_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}
    file_extension = Path(file.filename or "image.jpg").suffix.lower()
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{file_extension}'. Allowed: {', '.join(allowed_extensions)}",
        )

    # Save file
    new_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(settings.UPLOAD_DIR, new_filename)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    with open(file_path, "wb") as buf:
        shutil.copyfileobj(file.file, buf)

    # Create image record
    new_image = Image(
        inspection_id=inspection_id,
        file_path=file_path,
        is_valid_file=True,
        preprocessing_status="UNPROCESSED",
        ocr_status="PENDING",
    )
    db.add(new_image)

    db.add(AuditLog(
        user_id=current_user.id,
        action="IMAGE_UPLOAD",
        entity_name="inspections",
        entity_id=inspection_id,
        payload={"filename": file.filename, "saved_as": new_filename},
    ))
    await db.commit()
    await db.refresh(new_image)

    # Trigger background pipeline (CV → OCR → Field Extraction → Auto-Verdict)
    background_tasks.add_task(run_pipeline_for_image, new_image.id)

    return ImageUploadResponse(
        image_id=new_image.id,
        status="ACCEPTED",
        message=(
            "Image accepted. The LMPC verification pipeline has started. "
            "Poll GET /inspections/{id} until status changes to COMPLIANT or NON_COMPLIANT."
        ),
    )


# ── Get inspection detail ────────────────────────────────────────────────────

@router.get("/{inspection_id}", response_model=InspectionDetailOut)
async def get_inspection(
    inspection_id: uuid.UUID,
    current_user: User = Depends(require_role("OFFICER", "ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns full inspection detail including:
    - Status (PENDING | PROCESSING | COMPLIANT | NON_COMPLIANT | PROCESSING_FAILED)
    - Uploaded images with preprocessing & OCR status
    - Extracted LMPC fields (MRP, Net Quantity, Manufacturer, etc.)
    - Per-rule findings (PASS | FAIL | INFO)
    """
    result = await db.execute(
        select(Inspection)
        .where(Inspection.id == inspection_id)
        .options(
            selectinload(Inspection.product_category),
            selectinload(Inspection.images),
            selectinload(Inspection.extracted_fields),
            selectinload(Inspection.findings),
            selectinload(Inspection.reviews),
        )
    )
    inspection = result.scalar_one_or_none()
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found.")

    _check_access(inspection, current_user)
    return inspection
