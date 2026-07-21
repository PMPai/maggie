from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    display_name: str
    organization_id: str
    roles: list[str]


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str
