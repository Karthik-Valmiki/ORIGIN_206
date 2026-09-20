from sqlalchemy.orm import Session
from fastapi import HTTPException
from ..models.inspection import Inspection, Image
from ..models.rules import LMPCRule
from ..models.product import ProductCategory
from datetime import datetime
import uuid

def create_inspection_record(
    db: Session,
    officer_id: uuid.UUID,
    category_id: uuid.UUID,
    product_name: str = None,
    location: str = None,
    is_imported: bool = False,
    notes: str = None
) -> Inspection:
    
    # 1. Verify Category
    category = db.query(ProductCategory).filter(ProductCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
        
    # 2. Get applicable rule version for today
    active_rule = db.query(LMPCRule).filter(
        LMPCRule.status == "PUBLISHED",
        (LMPCRule.category_id == category_id) | (LMPCRule.category_id.is_(None))
    ).order_by(LMPCRule.version.desc()).first()
    
    if not active_rule:
        raise HTTPException(status_code=500, detail="No active rule configured in the system")

    inspection = Inspection(
        officer_id=officer_id,
        product_category_id=category_id,
        rule_id=active_rule.id,
        product_name=product_name,
        location=location,
        is_imported=is_imported,
        notes=notes,
        status="PENDING"
    )
    db.add(inspection)
    db.commit()
    db.refresh(inspection)
    
    return inspection

def create_image_record(db: Session, inspection_id: uuid.UUID, file_path: str) -> Image:
    image = Image(
        inspection_id=inspection_id,
        file_path=file_path,
        preprocessing_status="UNPROCESSED",
        ocr_status="PENDING"
    )
    db.add(image)
    db.commit()
    db.refresh(image)
    return image

def get_inspection(db: Session, inspection_id: uuid.UUID, current_user):
    inspection = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")
        
    roles = [r.role_name for r in current_user.roles]
    if "ADMIN" not in roles and inspection.officer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this inspection")
        
    return inspection
