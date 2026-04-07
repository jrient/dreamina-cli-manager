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