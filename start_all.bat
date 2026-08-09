@echo off
echo Starting AI Backlink Engine...
echo =======================================

echo Connecting to Cloud Databases (Neon Postgres & Upstash Redis)...

echo Starting Discovery Engine...
start "Discovery Engine" cmd /k "python discovery\main.py"

echo Starting LLM Pipeline Worker...
start "LLM Pipeline" cmd /k "python llm_pipeline\worker.py"

echo Starting LLM Parser Worker...
start "LLM Parser" cmd /k "python llm_pipeline\parser_worker.py"

echo Starting Execution Router (Playwright)...
start "Execution Router" cmd /k "python execution_router\worker.py"

echo Starting Intern Panel Dashboard...
start "Intern Panel" cmd /k "cd dashboard && python -m uvicorn main:app --host 0.0.0.0 --port 8000"

echo =======================================
echo All services started!
echo You can access the Dashboard at: http://localhost:8000
echo - Check the "Discovered Sites" tab to approve new platforms.
echo - Approving a site will instantly launch a browser for you to log in!
echo =======================================
pause
