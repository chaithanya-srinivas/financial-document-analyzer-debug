# celery_app.py
from __future__ import annotations
import os
from pathlib import Path
from celery import Celery

# --- load .env for the worker process ---
def _load_dotenv_if_present():
    p = Path(".env")
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip()
            if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                v = v[1:-1]
            os.environ.setdefault(k, v)
_load_dotenv_if_present()
# ----------------------------------------

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
celery_app = Celery("finanalyzer", broker=REDIS_URL, backend=REDIS_URL)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    task_always_eager=os.getenv("CELERY_EAGER", "0") == "1",  # set CELERY_EAGER=1 to debug without worker
    include=["tasks_worker"],  # auto-register our tasks
)
