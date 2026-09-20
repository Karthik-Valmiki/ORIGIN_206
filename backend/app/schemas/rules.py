from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

class LMPCRuleBase(BaseModel):
    name: str
    category_id: Optional[uuid.UUID] = None
    rule_data: Dict[str, Any]
    effective_from: Optional[datetime] = None

class LMPCRuleCreate(LMPCRuleBase):
    pass

class LMPCRuleOut(LMPCRuleBase):
    id: uuid.UUID
    version: int
    status: str
    category_name: Optional[str] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class RuleValidationResult(BaseModel):
    valid: bool
    errors: Optional[list[str]] = None
