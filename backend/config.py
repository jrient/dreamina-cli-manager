# backend/config.py
import os
from pathlib import Path

ACCOUNTS_DIR = Path(os.getenv("ACCOUNTS_DIR", "/app/accounts"))
CONFIG_BASE = Path(os.getenv("CONFIG_BASE", "/app/configs"))
DB_PATH = Path(os.getenv("DB_PATH", "/app/db/tasks.db"))
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/app/uploads"))
RESULTS_DIR = Path(os.getenv("RESULTS_DIR", "/app/results"))
MATERIALS_DIR = UPLOAD_DIR / "materials"
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "600"))

# Ensure runtime directories exist
CONFIG_BASE.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
MATERIALS_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)