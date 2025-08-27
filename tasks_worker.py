from __future__ import annotations
import json
from celery_app import celery_app
from db import session_scope
from models import Job, Analysis
from task import run_analysis  # uses mock LLM when MOCK_LLM=1

@celery_app.task(name="process_pdf_job")
def process_pdf_job(job_id: str, file_path: str, query: str, user_id: str | None = None):
    with session_scope() as session:
        job = session.get(Job, job_id)
        if not job:
            return {"error": f"Job {job_id} not found"}

        try:
            result = run_analysis(query=query, file_path=file_path)  # dict
            # store analysis
            analysis = Analysis(
                job_id=job_id,
                result_json=json.dumps(result, ensure_ascii=False),
                company=(result.get("metadata") or {}).get("company"),
                quarter=(result.get("metadata") or {}).get("quarter"),
                year=(result.get("metadata") or {}).get("year"),
                recommendation_action=(result.get("recommendation") or {}).get("action"),
                confidence=(result.get("recommendation") or {}).get("confidence"),
                pages=(result.get("metadata") or {}).get("pages"),
            )
            session.add(analysis)

            # update job
            job.status = "done"
            job.error = None
            session.add(job)

            return {"ok": True}
        except Exception as e:
            job.status = "error"
            job.error = str(e)
            session.add(job)
            return {"error": str(e)}