from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from ..models.rbac import User
from ..models.inspection import Inspection
from ..core.dependencies import require_admin
from ..services.queue import enqueue_inspection_job
from ..services.audit import log_audit_event
import uuid

router = APIRouter(prefix="/admin", tags=["Admin Operations"])

@router.get("/stats")
def get_stats(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    status_counts = db.query(Inspection.status, func.count(Inspection.id)).group_by(Inspection.status).all()
    stats = {status: count for status, count in status_counts}
    
    return {
        "inspection_counts_by_status": stats,
        "total_inspections": sum(stats.values())
    }

@router.get("/failed-jobs")
def get_failed_jobs(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    failed = db.query(Inspection).filter(Inspection.status == "PROCESSING_FAILED").order_by(Inspection.updated_at.desc()).all()
    return [{"id": str(i.id), "inspection_number": i.inspection_number, "updated_at": i.updated_at} for i in failed]

@router.post("/inspections/{inspection_id}/requeue", status_code=status.HTTP_202_ACCEPTED)
def requeue_inspection(
    inspection_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    inspection = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")
        
    if inspection.status != "PROCESSING_FAILED":
        raise HTTPException(status_code=400, detail="Only failed inspections can be requeued by admin")
        
    inspection.status = "PENDING"
    db.commit()
    
    enqueue_inspection_job(inspection.id)
    log_audit_event(db, current_user.id, "ADMIN_REQUEUE", "inspections", inspection.id)
    
    return {"status": "requeued"}
