from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.rbac import User
from ..models.inspection import Image
from ..core.dependencies import get_current_user
from ..services.inspection import get_inspection
from ..config import settings
import uuid
import os

router = APIRouter(prefix="/images", tags=["Images"])

@router.get("/{image_id}/file")
def get_image_file(
    image_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    image = db.query(Image).filter(Image.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
        
    # Check ownership
    get_inspection(db, image.inspection_id, current_user)
    
    if not os.path.exists(image.file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")
        
    return FileResponse(image.file_path)

@router.get("/{image_id}/preprocessed")
def get_preprocessed_image(
    image_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    image = db.query(Image).filter(Image.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
        
    get_inspection(db, image.inspection_id, current_user)
    
    # Deriving preprocessed path (this matches what the worker will write)
    ext = image.file_path.split('.')[-1]
    base_name = os.path.basename(image.file_path).replace("_original", "_preprocessed")
    preprocessed_path = os.path.join(os.path.dirname(image.file_path), base_name)
    
    if not os.path.exists(preprocessed_path):
        # Fallback to original if preprocessing didn't complete or failed
        if os.path.exists(image.file_path):
            return FileResponse(image.file_path)
        raise HTTPException(status_code=404, detail="File not found on disk")
        
    return FileResponse(preprocessed_path)
