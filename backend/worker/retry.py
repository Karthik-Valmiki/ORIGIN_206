import time
from sqlalchemy.orm import Session
from app.models.inspection import Inspection

MAX_RETRIES = 3
RETRY_DELAYS = [0, 30, 120] # seconds

def handle_failure(db: Session, inspection_id: str, attempt: int, error_msg: str):
    """
    Handles retries. If max retries reached, sets status to PROCESSING_FAILED.
    """
    if attempt >= MAX_RETRIES:
        inspection = db.query(Inspection).filter(Inspection.id == inspection_id).first()
        if inspection:
            inspection.status = "PROCESSING_FAILED"
            # We could store error_msg in notes or a dedicated error column
            if inspection.notes:
                inspection.notes += f"\n[SYSTEM ERROR]: {error_msg}"
            else:
                inspection.notes = f"[SYSTEM ERROR]: {error_msg}"
            db.commit()
        return False # no more retries
        
    delay = RETRY_DELAYS[attempt - 1]
    time.sleep(delay)
    return True # should retry
