from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid

class ReviewCreate(BaseModel):
    action: str = Field(pattern="^(ACCEPT|OVERRIDE|REQUEST_REINSPECTION)$")
    comments: str = Field(min_length=10)

class ReviewOut(BaseModel):
    id: uuid.UUID
    inspection_id: uuid.UUID
    officer_id: Optional[uuid.UUID]
    action: str
    comments: Optional[str]
    reviewed_at: datetime
    
    class Config:
        from_attributes = True
