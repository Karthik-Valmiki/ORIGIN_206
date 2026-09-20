from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.product import ProductCategory
from ..models.rbac import User
from ..schemas.category import CategoryCreate, CategoryUpdate, CategoryOut
from ..core.dependencies import require_admin, get_current_user
from ..services.audit import log_audit_event
import uuid

router = APIRouter(prefix="/categories", tags=["Categories"])

@router.get("/", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(ProductCategory).all()

@router.post("/", response_model=CategoryOut)
def create_category(cat_in: CategoryCreate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    if db.query(ProductCategory).filter(ProductCategory.category_name == cat_in.category_name).first():
        raise HTTPException(status_code=400, detail="Category already exists")
        
    cat = ProductCategory(**cat_in.model_dump())
    db.add(cat)
    db.commit()
    db.refresh(cat)
    
    log_audit_event(db, current_user.id, "CREATE_CATEGORY", "product_categories", cat.id)
    return cat

@router.patch("/{cat_id}", response_model=CategoryOut)
def update_category(cat_id: uuid.UUID, cat_in: CategoryUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    cat = db.query(ProductCategory).filter(ProductCategory.id == cat_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
        
    if cat_in.category_name is not None:
        cat.category_name = cat_in.category_name
    if cat_in.description is not None:
        cat.description = cat_in.description
        
    db.commit()
    db.refresh(cat)
    
    log_audit_event(db, current_user.id, "UPDATE_CATEGORY", "product_categories", cat.id)
    return cat
