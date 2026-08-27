from datetime import datetime
from pydantic import BaseModel, UUID4


class UserCreate(BaseModel):
    email: str
    display_name: str
    department: str | None = None
    password: str
    group_ids: list[UUID4] = []


class UserUpdate(BaseModel):
    display_name: str | None = None
    department: str | None = None
    status: str | None = None


class UserGroupUpdate(BaseModel):
    group_ids: list[UUID4]


class ResetPasswordRequest(BaseModel):
    new_password: str


class GroupInfo(BaseModel):
    id: UUID4
    name: str
    category: str

    model_config = {"from_attributes": True}


class UserResponse(BaseModel):
    id: UUID4
    email: str
    display_name: str
    department: str | None = None
    status: str
    roles: list[str] = []
    groups: list[GroupInfo] = []
    last_login_at: datetime | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class GroupCreate(BaseModel):
    name: str
    category: str
    description: str | None = None
    role_ids: list[UUID4] = []


class GroupUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    description: str | None = None
    role_ids: list[UUID4] | None = None
    status: str | None = None


class GroupMemberAdd(BaseModel):
    user_ids: list[UUID4]


class GroupRoleInfo(BaseModel):
    id: UUID4
    name: str

    model_config = {"from_attributes": True}


class GroupMemberInfo(BaseModel):
    id: UUID4
    display_name: str
    email: str
    department: str | None = None
    joined_at: datetime | None = None

    model_config = {"from_attributes": True}


class GroupResponse(BaseModel):
    id: UUID4
    name: str
    category: str
    description: str | None = None
    status: str
    is_default: bool = False
    roles: list[GroupRoleInfo] = []
    member_count: int = 0
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class GroupDetailResponse(GroupResponse):
    members: list[GroupMemberInfo] = []