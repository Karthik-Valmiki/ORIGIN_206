from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

import uuid
from pydantic import BaseModel, EmailStr, field_validator

class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    roles: List[str]

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    roles: Optional[List[str]] = None

class UserOut(BaseModel):
    id: uuid.UUID
    full_name: str
    email: EmailStr
    is_active: bool
    roles: List[str]
    created_at: datetime
    
    @field_validator("roles", mode="before")
    @classmethod
    def extract_roles(cls, v):
        if not v:
            return []
        if isinstance(v[0], str):
            return v
        return [role.role_name for role in v]
    
    class Config:
        from_attributes = True

class PasswordReset(BaseModel):
    new_password: str
