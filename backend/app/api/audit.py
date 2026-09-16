from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.rbac import User
from ..models.operations import AuditLog
from ..schemas.audit import AuditLogListOut
from ..core.dependencies import require_admin

router = APIRouter(prefix="/admin/audit-logs", tags=["Audit"])

@router.get("", response_model=AuditLogListOut)
def list_audit_logs(
    skip: int = 0, limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    total = db.query(AuditLog).count()
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()
    
    return {"data": logs, "total": total}
