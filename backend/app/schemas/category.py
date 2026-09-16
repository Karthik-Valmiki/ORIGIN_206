from pydantic import BaseModel
from typing import Optional

class CategoryCreate(BaseModel):
    category_name: str
    description: Optional[str] = None

class CategoryUpdate(BaseModel):
    category_name: Optional[str] = None
    description: Optional[str] = None

import uuid

class CategoryOut(BaseModel):
    id: uuid.UUID
    category_name: str
    description: Optional[str]
    
    class Config:
        from_attributes = True
