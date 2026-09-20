from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

class AuditLogOut(BaseModel):
    id: uuid.UUID
    user_id: Optional[uuid.UUID]
    action: str
    entity_name: str
    entity_id: Optional[uuid.UUID]
    payload: Optional[Dict[str, Any]]
    created_at: datetime
    
    class Config:
        from_attributes = True

class AuditLogListOut(BaseModel):
    data: List[AuditLogOut]
    total: int
