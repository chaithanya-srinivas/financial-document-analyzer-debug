Financial Document Analyzer - Debug Assignment
Project Overview
This project is a financial document analysis system that processes corporate reports,
financial statements, and investment documents. It uses a modular design with FastAPI,
Celery, Redis, and CrewAI agents to provide analysis, recommendations, and risk assessment.
Bugs Found and Fixes
1. Dependency Conflicts
Bug: crewai, crewai-tools, and embedchain required different versions of chromadb
and pypdf.
Fix: Downgraded to Python 3.10, pinned versions in requirements-locked.txt,
installed compatible pypdf, pdfplumber, and pillow.
2. Wrong Imports
Bug: from crewai.agents import Agent caused ImportError.
Fix: Updated to correct CrewAI import paths.
3. Circular Imports
Bug: main.py and tools.py imported each other.
Fix: Refactored helper functions into proper modules to remove circular dependency.
4. Regex Crash
Bug: Regex used recursion (?1) not supported in Python’s re.
Fix: Rewrote regex safely for JSON block extraction.
5. FastAPI Form Upload Error
Bug: Runtime error requiring python-multipart.
Fix: Installed python-multipart.
6. Celery Unregistered Task
Bug: Worker error Received unregistered task process pdf job.
Fix: Ran Celery with explicit import:
celery -A celery_app . celery_app worker -I tasks_worker --
loglevel = info -- concurrency =2
1
7. OpenAI API Key Error
Bug: Missing API key raised The api key client option must be set.
Fix: Added .env with MOCK LLM=1 for offline mode. Real mode requires OPENAI API KEY.
8. Jobs Stuck in Pending
Bug: Results endpoint always showed pending.
Fix: Worker now updates job results in database after processing.
Setup and Usage
1. Clone Repository
git clone < repo - url >
cd financial - document - analyzer - debug
2. Create Virtual Environment
python3 .10 -m venv venv
source venv / bin / activate
3. Install Requirements
pip install -r requirements - locked . txt
4. Create .env File
# Mock mode ( no API key required )
MOCK_LLM =1
# If using real OpenAI API :
# OPENAI_API_KEY = sk - xxxx
5. Start Redis
redis - server
6. Start API Server
uvicorn main : app -- reload
2
7. Start Celery Worker
celery -A celery_app . celery_app worker -I tasks_worker -- loglevel =
info -- concurrency =2
API Documentation
1. Health Check
curl -s http ://127.0.0.1:8000/ health
Response:
{" status ": " ok "}
2. Upload Document for Analysis
curl -s -F " file = @data / sample . pdf " -F " email = tester@example . com " -F
" name = Tester " http ://127.0.0.1:8000/ analyze
Response:
{
" job_id ": "1234 -5678 -90 ab " ,
" status ": " pending "
}
3. Poll Job Status and Result
curl -s http ://127.0.0.1:8000/ result / < job_id > | python -m json . tool
Response when done:
{
" job_id ": "1234 -5678 -90 ab " ,
" status ": " done " ,
" result ": {
" metadata ": {
" company ": " UnknownCo " ,
" quarter ": " Q ?" ,
" pages ": 30
} ,
" recommendation ": {
" action ": " buy " ,
" rationale ": " Mock analysis using keywords " ,
3
" confidence ": 65
} ,
" risks ": [
{
" name ": " Data completeness " ,
" severity ": " medium "
}
] ,
" limitations ": " This is a mock result generated without calling
the model ."
}
}
Delivered Features
• Upload financial PDF documents
• Asynchronous background job queue with Celery
• Persistent job tracking with Redis/DB
• AI-powered analysis (mock or real OpenAI)
• Investment recommendations
• Risk assessment
• Market insights