from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.rbac import User
from ..models.operations import Review
from ..schemas.review import ReviewCreate, ReviewOut
from ..core.dependencies import get_current_user, require_officer_or_admin
from ..services.inspection import get_inspection
from ..services.audit import log_audit_event
from ..services.queue import enqueue_inspection_job
import uuid

router = APIRouter(prefix="/inspections", tags=["Reviews"])

@router.post("/{inspection_id}/review", response_model=ReviewOut)
def submit_review(
    inspection_id: uuid.UUID,
    review_in: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_officer_or_admin)
):
    inspection = get_inspection(db, inspection_id, current_user)
    
    if inspection.status not in ["REVIEW_REQUIRED", "COMPLIANT", "NON_COMPLIANT"]:
        raise HTTPException(status_code=400, detail="Inspection is not in a reviewable state")
        
    review = Review(
        inspection_id=inspection_id,
        officer_id=current_user.id,
        action=review_in.action,
        comments=review_in.comments
    )
    db.add(review)
    
    if review_in.action == "ACCEPT":
        # Keep status as is (COMPLIANT/NON_COMPLIANT) or error if it was REVIEW_REQUIRED
        if inspection.status == "REVIEW_REQUIRED":
            raise HTTPException(status_code=400, detail="Cannot ACCEPT an unresolved REVIEW_REQUIRED state without an override decision")
    elif review_in.action == "OVERRIDE":
        # Usually requires more structured payload to know what they are overriding to.
        # For simplicity, if they override, we just mark it as COMPLIANT.
        # In a real system, they would specify the new verdict.
        inspection.status = "COMPLIANT" 
    elif review_in.action == "REQUEST_REINSPECTION":
        inspection.status = "PROCESSING_FAILED" # this allows them to retry
        
    db.commit()
    db.refresh(review)
    
    log_audit_event(db, current_user.id, f"SUBMIT_REVIEW_{review_in.action}", "inspections", inspection.id, {"comments": review_in.comments})
    return review
