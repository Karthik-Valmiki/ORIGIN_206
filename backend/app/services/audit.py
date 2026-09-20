from sqlalchemy.orm import Session
from ..models.operations import AuditLog
from typing import Dict, Any, Optional
import uuid

def log_audit_event(
    db: Session,
    user_id: Optional[uuid.UUID],
    action: str,
    entity_name: str,
    entity_id: Optional[uuid.UUID] = None,
    payload: Optional[Dict[str, Any]] = None
):
    audit_log = AuditLog(
        user_id=user_id,
        action=action,
        entity_name=entity_name,
        entity_id=entity_id,
        payload=payload
    )
    db.add(audit_log)
    db.commit()
