# backend/services/dreamina.py
import asyncio
import json
import os
import re
import shutil
from pathlib import Path
from typing import Optional

# Dreamina 账号配置目录（每个账号独立的 HOME）
ACCOUNT_HOME_BASE = Path("/root/.dreamina_accounts")


class ConcurrencyLimitError(Exception):
    """即梦并发限制，任务需排队等待"""
    pass

# Regex patterns for parsing dreamina CLI output
SUBMIT_ID_RE = re.compile(r'(?:submit[_\s]id|task[_\s]id)[:\s]+([a-f0-9]{8,})', re.I)
RESULT_URL_RE = re.compile(r'https?://\S+\.(?:mp4|mov|webm)\S*', re.I)
STATUS_RE = re.compile(r'status[:\s]+(\w+)', re.I)
CREDIT_RE = re.compile(r'(?:credit|balance)[:\s]+([\d.]+)', re.I)


def get_account_env(account_id: str) -> dict:
    """Return environment with HOME set for the given account.

    Each account has its own ~/.dreamina_cli/ directory under /root/.dreamina_accounts/<account_id>/
    This allows multiple dreamina sessions to coexist in one container.
    """
    account_home = ACCOUNT_HOME_BASE / account_id
    account_home.mkdir(parents=True, exist_ok=True)

    # Create .dreamina_cli directory
    dreamina_cli_dir = account_home / ".dreamina_cli"
    dreamina_cli_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["HOME"] = str(account_home)
    return env


def get_account_credential_path(account_id: str) -> Path:
    """Return the credential.json path for an account."""
    return ACCOUNT_HOME_BASE / account_id / ".dreamina_cli" / "credential.json"


def is_account_logged_in(account_id: str) -> bool:
    """Check if an account has valid credentials."""
    cred_path = get_account_credential_path(account_id)
    return cred_path.exists()


async def import_credentials(account_id: str, credentials_json: str) -> tuple[bool, str]:
    """Import dreamina credentials using the CLI import_login_response command.

    Returns (success, error_message).
    """
    returncode, stdout, stderr = await run_cli(
        ["import_login_response"],
        account_id=account_id,
        stdin=credentials_json
    )
    if returncode != 0:
        return False, stderr or stdout or "Import failed"
    return True, ""


async def run_cli(args: list[str], account_id: str, stdin: Optional[str] = None) -> tuple[int, str, str]:
    """Run dreamina CLI with account isolation. Returns (returncode, stdout, stderr)."""
    env = get_account_env(account_id)
    proc = await asyncio.create_subprocess_exec(
        "/root/.local/bin/dreamina", *args,
        stdin=asyncio.subprocess.PIPE if stdin else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    stdin_bytes = stdin.encode() if stdin else None
    stdout, stderr = await proc.communicate(input=stdin_bytes)
    return proc.returncode, stdout.decode(), stderr.decode()


async def ensure_account_initialized(account_id: str) -> None:
    """Check if account is logged in (has valid credential.json).

    Raises an error if not logged in, with instructions for how to login.
    """
    if is_account_logged_in(account_id):
        return

    raise RuntimeError(
        f"账号 '{account_id}' 未登录。请在容器内执行登录命令：\n"
        f"  docker exec -it dreamina-backend bash -c 'HOME=/root/.dreamina_accounts/{account_id} dreamina login'\n"
        f"登录成功后即可使用该账号。"
    )


async def get_credit(account_id: str) -> str:
    """Return credit balance string for account."""
    await ensure_account_initialized(account_id)
    returncode, stdout, stderr = await run_cli(["user_credit"], account_id=account_id)
    if returncode != 0:
        raise RuntimeError(f"user_credit failed: {stderr or stdout}")
    m = CREDIT_RE.search(stdout)
    return m.group(1) if m else stdout.strip()


async def submit_multimodal2video(
    account_id: str,
    image_paths: list[str],
    video_paths: list[str],
    audio_paths: list[str],
    prompt: str,
    duration: int,
    ratio: str,
    model_version: str,
) -> str:
    """Submit a multimodal2video task. Returns submit_id."""
    await ensure_account_initialized(account_id)

    args = ["multimodal2video"]
    for p in image_paths:
        args += ["--image", p]
    for p in video_paths:
        args += ["--video", p]
    for p in audio_paths:
        args += ["--audio", p]
    if prompt:
        args += ["--prompt", prompt]
    args += ["--duration", str(duration)]
    if ratio:
        args += ["--ratio", ratio]
    if model_version:
        args += ["--model_version", model_version]
    args += ["--poll", "5"]  # 等待5秒获取初始状态反馈

    returncode, stdout, stderr = await run_cli(args, account_id=account_id)
    combined = stdout + "\n" + stderr

    # Check for immediate failure from poll result
    try:
        data = json.loads(stdout.strip())
        if isinstance(data, dict):
            gen_status = data.get("gen_status", "")
            if gen_status == "fail":
                fail_reason = data.get("fail_reason", "Unknown error")
                # 检查是否为并发限制错误
                if "ExceedConcurrencyLimit" in fail_reason or "ret=1310" in fail_reason:
                    raise ConcurrencyLimitError(fail_reason)
                raise RuntimeError(f"任务提交失败: {fail_reason}")
            # Return submit_id from poll result
            submit_id = data.get("submit_id")
            if submit_id:
                return submit_id
    except json.JSONDecodeError:
        pass

    if returncode != 0:
        raise RuntimeError(f"multimodal2video failed: {combined.strip()}")

    m = SUBMIT_ID_RE.search(combined)
    if not m:
        # Try to find any hex-looking ID if regex misses
        fallback = re.search(r'\b([a-f0-9]{12,})\b', combined)
        if fallback:
            return fallback.group(1)
        raise RuntimeError(f"Could not parse submit_id from output: {combined.strip()}")

    return m.group(1)


async def query_result(account_id: str, submit_id: str) -> dict:
    """Query task status. Returns dict with keys: status, result_url, error_msg."""
    await ensure_account_initialized(account_id)
    returncode, stdout, stderr = await run_cli(
        ["query_result", f"--submit_id={submit_id}"], account_id=account_id
    )
    combined = stdout + "\n" + stderr

    # Try JSON parse first
    try:
        data = json.loads(stdout.strip())
        if isinstance(data, dict):
            # Check gen_status or status field
            raw_status = data.get("gen_status") or data.get("status") or "processing"
            result_url = data.get("result_url") or data.get("url") or data.get("video_url")
            error_msg = data.get("error") or data.get("message")

            # Check nested result_json.videos[0].video_url
            if not result_url:
                result_json = data.get("result_json") or {}
                videos = result_json.get("videos") or []
                if videos and isinstance(videos, list):
                    result_url = videos[0].get("video_url")

            # Normalize status
            if raw_status in ("success", "succeeded", "completed", "done"):
                status = "success"
            elif raw_status in ("fail", "failed", "error"):
                status = "failed"
            elif raw_status in ("pending", "queued", "waiting", "submitted"):
                status = "pending"
            else:
                status = "processing"

            return {"status": status, "result_url": result_url, "error_msg": error_msg}
    except (json.JSONDecodeError, ValueError):
        pass

    # Fallback: regex parse
    status_match = STATUS_RE.search(combined)
    raw_status = status_match.group(1).lower() if status_match else "processing"

    # Normalize status to our four states
    if raw_status in ("success", "succeeded", "completed", "done"):
        status = "success"
    elif raw_status in ("fail", "failed", "error"):
        status = "failed"
    elif raw_status in ("pending", "queued", "waiting"):
        status = "pending"
    else:
        status = "processing"

    url_match = RESULT_URL_RE.search(combined)
    result_url = url_match.group(0) if url_match else None

    error_msg = None
    if status == "failed":
        error_msg = combined.strip()

    return {"status": status, "result_url": result_url, "error_msg": error_msg}