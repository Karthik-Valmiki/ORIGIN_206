from pydantic import BaseModel
from typing import List, Optional, Any, Dict
from datetime import datetime
import uuid

class InspectionCreate(BaseModel):
    category_id: str
    product_name: Optional[str] = None
    location: Optional[str] = None
    is_imported: bool = False
    notes: Optional[str] = None
    # For file uploads, we use Form() and UploadFile in the router instead of this schema
    # but this is for reference or if we accept JSON first

class InspectionOut(BaseModel):
    id: uuid.UUID
    inspection_number: Optional[str]
    officer_id: Optional[uuid.UUID]
    product_category_id: uuid.UUID
    rule_id: uuid.UUID
    status: str
    product_name: Optional[str]
    location: Optional[str]
    is_imported: bool
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class InspectionListOut(BaseModel):
    data: List[InspectionOut]
    total: int

class FindingOut(BaseModel):
    id: uuid.UUID
    finding_type: str
    status: str
    details: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True

class ImageOut(BaseModel):
    id: uuid.UUID
    file_path: str
    ocr_status: str
    
    class Config:
        from_attributes = True

class InspectionDetailOut(InspectionOut):
    images: List[ImageOut] = []
    findings: List[FindingOut] = []
    
    class Config:
        from_attributes = True
