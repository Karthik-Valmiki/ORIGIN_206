from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..models.rbac import User
from ..models.inspection import Inspection, Image
from ..schemas.inspection import InspectionOut, InspectionListOut, InspectionDetailOut
from ..core.dependencies import get_current_user, require_officer_or_admin
from ..services.inspection import create_inspection_record, create_image_record, get_inspection
from ..services.image_storage import save_upload
from ..services.queue import enqueue_inspection_job
from ..services.audit import log_audit_event
from ..config import settings
import uuid

router = APIRouter(prefix="/inspections", tags=["Inspections"])

def validate_image(file: UploadFile):
    # MIME magic byte validation would go here
    # For now, simplistic validation
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed")

@router.post("/", response_model=InspectionOut, status_code=status.HTTP_202_ACCEPTED)
def create_inspection(
    category_id: uuid.UUID = Form(...),
    product_name: str = Form(None),
    location: str = Form(None),
    is_imported: bool = Form(False),
    notes: str = Form(None),
    images: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_officer_or_admin)
):
    if len(images) == 0 or len(images) > 4:
        raise HTTPException(status_code=400, detail="Must provide between 1 and 4 images")
        
    for img in images:
        validate_image(img)

    # 1. Create inspection record
    inspection = create_inspection_record(
        db=db,
        officer_id=current_user.id,
        category_id=category_id,
        product_name=product_name,
        location=location,
        is_imported=is_imported,
        notes=notes
    )
    
    # 2. Store images
    for idx, img in enumerate(images):
        file_path = save_upload(inspection.id, idx, img, settings.UPLOAD_DIR)
        create_image_record(db, inspection.id, file_path)
        
    # 3. Enqueue Job
    enqueue_inspection_job(inspection.id)
    
    log_audit_event(db, current_user.id, "CREATE_INSPECTION", "inspections", inspection.id)
    
    # Refresh to get DB trigger generated inspection_number
    db.refresh(inspection)
    return inspection

@router.get("/", response_model=InspectionListOut)
def list_inspections(
    skip: int = 0, limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Inspection)
    roles = [r.role_name for r in current_user.roles]
    if "ADMIN" not in roles:
        query = query.filter(Inspection.officer_id == current_user.id)
        
    total = query.count()
    inspections = query.order_by(Inspection.created_at.desc()).offset(skip).limit(limit).all()
    
    return {"data": inspections, "total": total}

@router.get("/{inspection_id}", response_model=InspectionDetailOut)
def get_inspection_endpoint(
    inspection_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return get_inspection(db, inspection_id, current_user)

@router.post("/{inspection_id}/retry", status_code=status.HTTP_202_ACCEPTED)
def retry_inspection(
    inspection_id: uuid.UUID,
    images: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_officer_or_admin)
):
    inspection = get_inspection(db, inspection_id, current_user)
    
    if inspection.status != "PROCESSING_FAILED":
        raise HTTPException(status_code=400, detail="Only failed inspections can be retried by the officer")
        
    if len(images) == 0 or len(images) > 4:
        raise HTTPException(status_code=400, detail="Must provide between 1 and 4 images")
        
    for img in images:
        validate_image(img)
        
    # Count existing images to continue index
    existing_count = db.query(Image).filter(Image.inspection_id == inspection.id).count()
    
    for idx, img in enumerate(images):
        file_path = save_upload(inspection.id, existing_count + idx, img, settings.UPLOAD_DIR)
        create_image_record(db, inspection.id, file_path)
        
    # Reset status
    inspection.status = "PENDING"
    db.commit()
    
    enqueue_inspection_job(inspection.id)
    log_audit_event(db, current_user.id, "RETRY_INSPECTION_WITH_IMAGES", "inspections", inspection.id)
    
    return {"status": "retry_accepted"}
