# backend/routers/auth.py
from fastapi import APIRouter, Cookie, HTTPException, Response
from pydantic import BaseModel

from models import LoginRequest, UserSession, UserResponse
from services.auth import (
    get_user_by_username, verify_password, create_session,
    delete_session, get_session, get_user_by_id, is_first_user,
    create_user
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginResponse(BaseModel):
    user: UserSession
    session_id: str


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest, response: Response):
    """用户登录"""
    user = await get_user_by_username(req.username)

    if not user:
        raise HTTPException(401, "用户名或密码错误")

    if user.get("deleted_at"):
        raise HTTPException(401, "账户已被禁用")

    if not verify_password(req.password, user["password"]):
        raise HTTPException(401, "用户名或密码错误")

    # 首个用户自动成为管理员
    check_admin = user["is_admin"]
    if not check_admin and await is_first_user():
        # 更新为管理员
        from services.auth import update_user
        await update_user(user["id"], is_admin=True)
        user["is_admin"] = 1
        check_admin = True

    session_id = create_session(user["id"], user["username"], bool(check_admin))

    # 设置 Cookie
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        max_age=86400,  # 24 hours
        samesite="lax"
    )

    return LoginResponse(
        user=UserSession(
            id=user["id"],
            username=user["username"],
            is_admin=bool(check_admin)
        ),
        session_id=session_id
    )


@router.post("/logout")
async def logout(response: Response, session_id: str = Cookie(None)):
    """用户登出"""
    if session_id:
        delete_session(session_id)

    response.delete_cookie("session_id")
    return {"message": "已登出"}


@router.get("/me", response_model=UserSession)
async def get_current_user(session_id: str = Cookie(None)):
    """获取当前登录用户"""
    if not session_id:
        raise HTTPException(401, "未登录")

    session = get_session(session_id)
    if not session:
        raise HTTPException(401, "登录已过期")

    user = await get_user_by_id(session["user_id"])
    if not user:
        raise HTTPException(401, "用户不存在")

    return UserSession(
        id=user["id"],
        username=user["username"],
        is_admin=bool(user["is_admin"])
    )