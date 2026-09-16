from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.rbac import User, Role, UserRole
from ..schemas.user import UserCreate, UserUpdate, UserOut, PasswordReset
from ..core.dependencies import require_admin
from ..core.security import get_password_hash
from ..services.audit import log_audit_event
import uuid

router = APIRouter(prefix="/admin/users", tags=["User Admin"])

@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    users = db.query(User).all()
    return users

@router.post("", response_model=UserOut)
def create_user(user_in: UserCreate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
        
    db_user = User(
        full_name=user_in.full_name,
        email=user_in.email,
        password_hash=get_password_hash(user_in.password)
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Assign roles
    for role_name in user_in.roles:
        role = db.query(Role).filter(Role.role_name == role_name).first()
        if role:
            db.add(UserRole(user_id=db_user.id, role_id=role.id))
            
    db.commit()
    db.refresh(db_user)
    
    log_audit_event(db, current_user.id, "CREATE_USER", "users", db_user.id)
    return db_user

@router.patch("/{user_id}/deactivate")
def deactivate_user(user_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    db.commit()
    log_audit_event(db, current_user.id, "DEACTIVATE_USER", "users", user.id)
    return {"status": "deactivated"}

@router.patch("/{user_id}/activate")
def activate_user(user_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = True
    db.commit()
    log_audit_event(db, current_user.id, "ACTIVATE_USER", "users", user.id)
    return {"status": "activated"}
