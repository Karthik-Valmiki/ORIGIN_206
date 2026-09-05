from pydantic import BaseModel, EmailStr


class SetupRequest(BaseModel):
    admin_email: EmailStr
    admin_password: str
    admin_full_name: str
