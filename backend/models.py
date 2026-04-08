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