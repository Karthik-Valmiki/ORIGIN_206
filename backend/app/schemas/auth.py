from pydantic import BaseModel, field_validator
from typing import List
import uuid

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class TokenData(BaseModel):
    id: str | None = None

class UserResponse(BaseModel):
    id: uuid.UUID
    full_name: str
    email: str
    roles: List[str]

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
