from __future__ import annotations

import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from pydantic import BaseModel

# ---- minimal .env loader ----
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

from db import init_db, session_scope
from models import User, Job, Analysis
from celery_app import celery_app
from tasks_worker import process_pdf_job

app = FastAPI(title="Financial Document Analyzer (Queued + DB)")

@app.on_event("startup")
def _startup():
    init_db()

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "mock": os.getenv("MOCK_LLM", "0") == "1",
        "crewai": os.getenv("CREWAI_ENABLED", "0") == "1",
        "db": os.getenv("DB_URL", "sqlite:///./finanalyzer.db"),
        "broker": os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    }

@app.post("/analyze")
async def analyze_financial_document(
    file: UploadFile = File(...),
    query: str = Form(default="Analyze this financial document for investment insights"),
    email: Optional[str] = Form(default=None),
    name: Optional[str] = Form(default=None),
):
    data_dir = Path("data"); data_dir.mkdir(parents=True, exist_ok=True)
    file_id = str(uuid.uuid4())
    file_path = data_dir / f"financial_document_{file_id}.pdf"

    try:
        content = await file.read()
        file_path.write_bytes(content)
        query = (query or "").strip() or "Analyze this financial document for investment insights"

        with session_scope() as session:
            # upsert user if provided
            user_id = None
            if email:
                user = session.query(User).filter_by(email=email).one_or_none()
                if not user:
                    user = User(email=email, name=name)
                    session.add(user)
                    session.flush()  # to get user.id
                user_id = user.id

            # create job
            job = Job(
                id=str(uuid.uuid4()),
                user_id=user_id,
                created_at=datetime.utcnow(),
                status="pending",
                error=None,
                file_path=str(file_path),
                query=query,
            )
            session.add(job)
            session.flush()
            job_id = job.id

        # enqueue Celery job
        process_pdf_job.delay(job_id=job_id, file_path=str(file_path), query=query, user_id=user_id)

        return {"job_id": job_id, "status": "pending"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing financial document: {e}")

@app.get("/result/{job_id}")
async def get_result(job_id: str):
    with session_scope() as session:
        job = session.get(Job, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found.")
        if job.status != "done":
            return {"job_id": job.id, "status": job.status, "error": job.error}
        analysis = session.query(Analysis).filter_by(job_id=job_id).one_or_none()
        result_json = analysis.result_json if analysis else None
        return {"job_id": job.id, "status": "done", "result": (None if result_json is None else __import__("json").loads(result_json))}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)