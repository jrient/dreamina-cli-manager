# backend/models.py
from pydantic import BaseModel
from typing import Optional


class AccountInfo(BaseModel):
    id: str
    filename: str


class CreditResponse(BaseModel):
    account_id: str
    credit: str


class TaskCreate(BaseModel):
    account_id: str
    prompt: Optional[str] = ""
    duration: int = 5
    ratio: str = "16:9"
    model_version: str = "seedance2.0fast"


class TaskResponse(BaseModel):
    id: str
    account_id: str
    status: str
    submit_id: Optional[str] = None
    result_url: Optional[str] = None
    error_msg: Optional[str] = None
    prompt: Optional[str] = None
    params: Optional[str] = None
    created_at: str
    updated_at: str
    project_id: Optional[str] = None
    label: Optional[str] = None
    creator_id: Optional[str] = None
    creator_name: Optional[str] = None
    episode: Optional[int] = None


class ProjectCreate(BaseModel):
    name: str


class ProjectUpdate(BaseModel):
    name: str


class ProjectResponse(BaseModel):
    id: str
    name: str
    deleted_at: Optional[str] = None
    created_at: str
    updated_at: str
    episode_count: Optional[int] = 50
    creator_id: Optional[str] = None
    my_role: Optional[str] = None  # 当前用户在项目中的角色：owner / member，admin 为 owner
    creator_name: Optional[str] = None  # 项目拥有者用户名


class ProjectStats(BaseModel):
    task_count: int
    material_count: int


class MaterialCreate(BaseModel):
    name: str
    type: str  # 'image' / 'audio'


class MaterialUpdate(BaseModel):
    name: str


class MaterialResponse(BaseModel):
    id: str
    project_id: str
    name: str
    type: str
    file_path: str
    created_at: str


# ==================== 用户认证相关模型 ====================

class UserCreate(BaseModel):
    username: str
    password: str


class UserUpdate(BaseModel):
    password: Optional[str] = None
    is_admin: Optional[bool] = None


class UserResponse(BaseModel):
    id: str
    username: str
    is_admin: bool
    deleted_at: Optional[str] = None
    created_at: str
    updated_at: str


class LoginRequest(BaseModel):
    username: str
    password: str


class UserSession(BaseModel):
    id: str
    username: str
    is_admin: bool


class MemberAdd(BaseModel):
    user_id: str
    role: str = "collaborator"


class MemberResponse(BaseModel):
    user_id: str
    username: str
    role: str
    accounts: list[str] = []


class AccountAssignment(BaseModel):
    accounts: list[str]


class ProjectSettingsUpdate(BaseModel):
    episode_count: Optional[int] = None