from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid

class ImageOut(BaseModel):
    id: uuid.UUID
    inspection_id: uuid.UUID
    is_valid_file: bool
    resolution_width: Optional[int]
    resolution_height: Optional[int]
    blur_score: Optional[float]
    glare_score: Optional[float]
    preprocessing_status: str
    ocr_status: str
    uploaded_at: datetime
    
    class Config:
        from_attributes = True
