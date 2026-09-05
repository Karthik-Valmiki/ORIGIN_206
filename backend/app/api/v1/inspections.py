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
from app.models.inspection import Inspection, Image, ProductCategory, RuleVersion, Review, AuditLog
from app.schemas.inspection import (
    InspectionCreate,
    InspectionDetailOut,
    InspectionOut,
    ImageUploadResponse,
    ReviewCreate,
    ReviewOut,
)
from app.services.pipeline_svc import run_pipeline_for_image
from app.config import settings

router = APIRouter(prefix="/inspections", tags=["inspections"])


@router.get("", response_model=list[InspectionOut])
async def list_my_inspections(
    status_filter: str | None = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, le=100),
    current_user: User = Depends(require_role("OFFICER", "ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    """Officers see only their own inspections; Admins see all."""
    q = select(Inspection).options(selectinload(Inspection.product_category))
    if "ADMIN" not in {r.role_name for r in current_user.roles}:
        q = q.where(Inspection.officer_id == current_user.id)
    if status_filter:
        q = q.where(Inspection.status == status_filter.upper())
    q = q.order_by(Inspection.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("", response_model=InspectionOut, status_code=status.HTTP_201_CREATED)
async def create_inspection(
    inspection_in: InspectionCreate,
    current_user: User = Depends(require_role("OFFICER", "ADMIN")),
    db: AsyncSession = Depends(get_db)
):
    # For prototype, assume a generic rule version is active
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
        status="PENDING"
    )
    db.add(new_inspection)
    await db.commit()
    await db.refresh(new_inspection, ['product_category'])
    return new_inspection


@router.post("/{inspection_id}/images", response_model=ImageUploadResponse)
async def upload_image(
    inspection_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(require_role("OFFICER", "ADMIN")),
    db: AsyncSession = Depends(get_db)
):
    # 1. Verify inspection exists
    result = await db.execute(select(Inspection).where(Inspection.id == inspection_id))
    inspection = result.scalar_one_or_none()
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")

    # 2. Save file locally
    file_extension = Path(file.filename).suffix
    new_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(settings.UPLOAD_DIR, new_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 3. Create image record
    new_image = Image(
        inspection_id=inspection_id,
        file_path=file_path,
        is_valid_file=True,
        preprocessing_status="UNPROCESSED",
        ocr_status="PENDING"
    )
    db.add(new_image)
    await db.commit()
    await db.refresh(new_image)

    # 4. Trigger background pipeline (CV + OCR)
    background_tasks.add_task(run_pipeline_for_image, new_image.id)

    return ImageUploadResponse(
        image_id=new_image.id,
        status="ACCEPTED",
        message="Image uploaded and pipeline triggered."
    )


@router.get("/{inspection_id}", response_model=InspectionDetailOut)
async def get_inspection(
    inspection_id: uuid.UUID,
    current_user: User = Depends(require_role("OFFICER", "ADMIN")),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Inspection)
        .where(Inspection.id == inspection_id)
        .options(
            selectinload(Inspection.product_category),
            selectinload(Inspection.images),
            selectinload(Inspection.extracted_fields),
            selectinload(Inspection.findings),
            selectinload(Inspection.reviews)
        )
    )
    inspection = result.scalar_one_or_none()
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")

    return inspection


@router.post("/{inspection_id}/submit", response_model=InspectionOut)
async def submit_inspection(
    inspection_id: uuid.UUID,
    current_user: User = Depends(require_role("OFFICER", "ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    """
    Officer submits the inspection after uploading all images.
    Race-condition guard: rejects if any image is still mid-pipeline.
    """
    result = await db.execute(
        select(Inspection)
        .where(Inspection.id == inspection_id)
        .options(selectinload(Inspection.images), selectinload(Inspection.product_category))
    )
    inspection = result.scalar_one_or_none()
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found.")
    if inspection.status != "PENDING":
        raise HTTPException(
            status_code=400,
            detail=f"Inspection is already '{inspection.status}', cannot submit.",
        )
    if not inspection.images:
        raise HTTPException(status_code=400, detail="Upload at least one image before submitting.")

    # Guard: reject if OCR / CV pipeline is still running
    still_processing = [
        img for img in inspection.images
        if img.ocr_status in ("PENDING", "PROCESSING")
        or img.preprocessing_status == "PROCESSING"
    ]
    if still_processing:
        raise HTTPException(
            status_code=409,
            detail=f"{len(still_processing)} image(s) still processing. Retry in a moment.",
        )

    inspection.status = "SUBMITTED"
    db.add(AuditLog(
        user_id=current_user.id,
        action="SUBMIT_INSPECTION",
        entity_name="inspections",
        entity_id=inspection_id,
        payload={"previous_status": "PENDING", "image_count": len(inspection.images)},
    ))
    await db.commit()
    await db.refresh(inspection, ["product_category"])
    return inspection


@router.post("/{inspection_id}/review", response_model=ReviewOut)
async def review_inspection(
    inspection_id: uuid.UUID,
    review_in: ReviewCreate,
    current_user: User = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    """
    Admin reviews a SUBMITTED inspection.
    Valid actions: ACCEPT | REJECT | REQUEST_REINSPECTION
    """
    VALID_ACTIONS = {"ACCEPT", "REJECT", "REQUEST_REINSPECTION"}
    if review_in.action not in VALID_ACTIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid action. Must be one of: {sorted(VALID_ACTIONS)}",
        )

    result = await db.execute(select(Inspection).where(Inspection.id == inspection_id))
    inspection = result.scalar_one_or_none()
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found.")
    if inspection.status != "SUBMITTED":
        raise HTTPException(
            status_code=400,
            detail=f"Can only review SUBMITTED inspections, current: '{inspection.status}'.",
        )

    status_map = {
        "ACCEPT": "APPROVED",
        "REJECT": "REJECTED",
        "REQUEST_REINSPECTION": "PENDING",
    }
    previous = inspection.status
    inspection.status = status_map[review_in.action]

    review = Review(
        inspection_id=inspection_id,
        officer_id=current_user.id,
        action=review_in.action,
        comments=review_in.comments,
    )
    db.add(review)
    db.add(AuditLog(
        user_id=current_user.id,
        action=f"REVIEW_{review_in.action}",
        entity_name="inspections",
        entity_id=inspection_id,
        payload={"previous_status": previous, "new_status": inspection.status},
    ))
    await db.commit()
    await db.refresh(review)
    return review
