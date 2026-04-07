# backend/routers/accounts.py
import asyncio
import json
import os
import re
import shutil
import signal
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from models import AccountInfo, CreditResponse
from services.dreamina import get_credit, is_account_logged_in, ACCOUNT_HOME_BASE
from config import ACCOUNTS_DIR

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


class AccountStatus(BaseModel):
    id: str
    filename: Optional[str] = None
    logged_in: bool
    credit: Optional[str] = None


class CreateAccountRequest(BaseModel):
    account_id: str


class ImportCredentialsRequest(BaseModel):
    account_id: str
    credentials_json: str


@router.get("", response_model=list[AccountStatus])
async def list_accounts():
    """List all accounts with login status."""
    accounts = []

    if ACCOUNT_HOME_BASE.exists():
        for account_dir in sorted(ACCOUNT_HOME_BASE.iterdir()):
            if account_dir.is_dir():
                account_id = account_dir.name
                logged_in = is_account_logged_in(account_id)
                credit = None
                if logged_in:
                    try:
                        credit = await get_credit(account_id)
                    except Exception:
                        pass
                accounts.append(AccountStatus(
                    id=account_id,
                    logged_in=logged_in,
                    credit=credit
                ))

    return accounts


@router.post("", response_model=AccountStatus)
async def create_account(req: CreateAccountRequest):
    """Create a new account."""
    account_id = req.account_id.strip()
    if not account_id:
        raise HTTPException(400, "Account ID cannot be empty")

    if not re.match(r'^[\w\-\u4e00-\u9fa5]+$', account_id):
        raise HTTPException(400, "账号 ID 只能包含字母、数字、下划线、横线和中文")

    account_home = ACCOUNT_HOME_BASE / account_id
    if account_home.exists():
        raise HTTPException(409, f"账号 '{account_id}' 已存在")

    account_home.mkdir(parents=True, exist_ok=True)
    (account_home / ".dreamina_cli").mkdir(parents=True, exist_ok=True)

    return AccountStatus(id=account_id, logged_in=False, credit=None)


@router.delete("/{account_id}")
async def delete_account(account_id: str):
    """Delete an account."""
    account_home = ACCOUNT_HOME_BASE / account_id
    if not account_home.exists():
        raise HTTPException(404, f"账号 '{account_id}' 不存在")

    shutil.rmtree(account_home)
    return {"message": f"账号 '{account_id}' 已删除"}


@router.post("/{account_id}/logout")
async def logout_account(account_id: str):
    """Logout an account by deleting its credential file."""
    cred_path = ACCOUNT_HOME_BASE / account_id / ".dreamina_cli" / "credential.json"
    if cred_path.exists():
        cred_path.unlink()
    return {"message": f"账号 '{account_id}' 已退出登录"}


@router.get("/{account_id}/credit", response_model=CreditResponse)
async def get_account_credit(account_id: str):
    """Get credit balance for an account."""
    if not is_account_logged_in(account_id):
        raise HTTPException(400, f"账号 '{account_id}' 未登录")
    try:
        credit = await get_credit(account_id)
    except Exception as e:
        raise HTTPException(502, detail=str(e))
    return CreditResponse(account_id=account_id, credit=credit)


@router.post("/{account_id}/refresh-credit")
async def refresh_account_credit(account_id: str):
    """Refresh credit balance for an account."""
    if not is_account_logged_in(account_id):
        raise HTTPException(400, f"账号 '{account_id}' 未登录")
    try:
        credit = await get_credit(account_id)
    except Exception as e:
        raise HTTPException(502, detail=str(e))
    return {"account_id": account_id, "credit": credit}


@router.post("/{account_id}/start-login")
async def start_login(account_id: str):
    """Run dreamina login --debug in container, extract URLs, then kill the process.

    This mimics running `dreamina login --debug` locally, getting the URLs,
    then immediately terminating the command (not waiting for callback).
    """
    account_home = ACCOUNT_HOME_BASE / account_id
    if not account_home.exists():
        raise HTTPException(404, f"账号 '{account_id}' 不存在")

    # Set HOME for this account
    env = os.environ.copy()
    env["HOME"] = str(account_home)

    # Kill any lingering dreamina processes to free the port
    try:
        kill_proc = await asyncio.create_subprocess_shell(
            "pkill -9 dreamina 2>/dev/null || true",
        )
        await kill_proc.wait()
        # Wait a moment for port to be released
        await asyncio.sleep(0.5)
    except Exception:
        pass

    # Use shell with timeout to run dreamina login --debug
    # This captures output before the process is killed
    proc = await asyncio.create_subprocess_shell(
        "timeout 3 dreamina login --debug 2>&1 || cat /dev/stdin",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    stdout, stderr = await proc.communicate()
    output = stdout.decode()

    # Extract random_secret_key from output
    key_match = re.search(r'random_secret_key=([a-f0-9]+)', output)
    random_secret_key = key_match.group(1) if key_match else None

    if not random_secret_key:
        # Check for port bind error
        if "bind: address already in use" in output:
            raise HTTPException(500, "端口被占用，请稍后重试或重启容器")
        raise HTTPException(500, f"无法获取登录密钥，请重试。\n\n输出:\n{output[:500]}")

    # Build URLs with the extracted key
    login_url = f"https://jimeng.jianying.com/dreamina/cli/v1/dreamina_cli_login?aid=513695&random_secret_key={random_secret_key}&web_version=7.5.0&login=true"
    json_url = f"https://jimeng.jianying.com/dreamina/cli/v1/dreamina_cli_login?aid=513695&random_secret_key={random_secret_key}&web_version=7.5.0"

    return {
        "account_id": account_id,
        "random_secret_key": random_secret_key,
        "login_url": login_url,
        "json_url": json_url,
        "instructions": [
            f"1. 点击下方「获取凭证 JSON」链接",
            f"2. 在浏览器中登录你的即梦账号（如已登录则直接显示 JSON）",
            f"3. 复制页面显示的完整 JSON 内容",
            f"4. 将 JSON 粘贴到下方输入框",
            f"5. 点击「导入凭证」完成登录"
        ]
    }


@router.post("/{account_id}/import-credentials")
async def import_account_credentials(account_id: str, req: ImportCredentialsRequest):
    """Import credentials JSON using dreamina import_login_response --file."""
    account_home = ACCOUNT_HOME_BASE / account_id
    if not account_home.exists():
        raise HTTPException(404, f"账号 '{account_id}' 不存在")

    # Validate JSON
    try:
        data = json.loads(req.credentials_json)
    except json.JSONDecodeError as e:
        raise HTTPException(400, f"JSON 格式错误: {str(e)}")

    # Check required fields
    if "auth_token" not in data:
        raise HTTPException(400, "JSON 缺少 auth_token 字段，请确保复制的是完整的凭证内容")

    # Save to temp file
    temp_dir = account_home / "tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / "credential.json"
    temp_path.write_text(req.credentials_json)

    try:
        # Set HOME for this account
        env = os.environ.copy()
        env["HOME"] = str(account_home)

        # Run dreamina import_login_response --file
        proc = await asyncio.create_subprocess_exec(
            "dreamina", "import_login_response", "--file", str(temp_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout, stderr = await proc.communicate()
        output = stdout.decode() + "\n" + stderr.decode()

        if proc.returncode != 0:
            if "random_secret_key" in output.lower():
                raise HTTPException(400, "凭证已过期，请重新点击「登录」按钮获取新链接")
            raise HTTPException(400, f"导入失败: {output.strip()}")

        # Verify by getting credit
        try:
            credit = await get_credit(account_id)
            return {
                "success": True,
                "account_id": account_id,
                "credit": credit,
                "message": "登录成功！"
            }
        except Exception as e:
            raise HTTPException(400, f"凭证验证失败: {str(e)}")
    finally:
        # Clean up temp file
        if temp_path.exists():
            temp_path.unlink()