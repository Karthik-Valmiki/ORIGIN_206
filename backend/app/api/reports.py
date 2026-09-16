from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.rbac import User
from ..models.operations import Report
from ..core.dependencies import get_current_user
from ..services.inspection import get_inspection
import uuid
import os

router = APIRouter(prefix="/inspections", tags=["Reports"])

@router.get("/{inspection_id}/report")
def download_report(
    inspection_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify ownership
    get_inspection(db, inspection_id, current_user)
    
    report = db.query(Report).filter(Report.inspection_id == inspection_id).first()
    if not report or not os.path.exists(report.report_storage_key):
        raise HTTPException(status_code=404, detail="Report not generated yet or file missing")
        
    return FileResponse(report.report_storage_key, filename=f"report_{inspection_id}.pdf")
