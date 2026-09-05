import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: str
    password: str


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
    full_name: str
    email: str
    password: str
    role_name: str = "OFFICER"


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
