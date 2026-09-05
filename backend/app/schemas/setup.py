from pydantic import BaseModel, EmailStr, Field


class SetupRequest(BaseModel):
    admin_email: EmailStr
    admin_password: str = Field(
        ...,
        min_length=8,
        max_length=72,
        description="Password must be between 8 and 72 characters",
    )
    admin_full_name: str = Field(..., min_length=1, max_length=100, strip_whitespace=True)

