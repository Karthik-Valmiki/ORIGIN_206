import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RoleOut(BaseModel):
    id: uuid.UUID
    role_name: str

    model_config = {"from_attributes": True}


class UserOut(BaseModel):
    id: uuid.UUID
    full_name: str
    email: str
    is_active: bool
    roles: list[RoleOut]
    created_at: datetime

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=100, strip_whitespace=True)
    email: EmailStr
    password: str = Field(
        ...,
        min_length=8,
        max_length=72,
        description="Password must be between 8 and 72 characters (Bcrypt limit)",
    )
    role_name: str = Field(default="OFFICER")


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

