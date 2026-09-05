from typing import Any
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, computed_field, model_validator


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

    @computed_field
    @property
    def role(self) -> str:
        return self.roles[0].role_name if self.roles else "OFFICER"

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
    role: str | None = None

    @model_validator(mode="before")
    @classmethod
    def reconcile_role(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "role" in data and "role_name" not in data:
                data["role_name"] = data["role"]
        return data


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

