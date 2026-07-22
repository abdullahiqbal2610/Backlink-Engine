@echo off
echo Starting Gaper.io Backlink AI Engine...
echo =======================================

echo Connecting to Cloud Databases (Neon Postgres & Upstash Redis)...

echo Starting Discovery Engine...
start "Discovery Engine" cmd /k "C:\Users\abdul\AppData\Local\Programs\Python\Python311\python.exe C:\Users\abdul\OneDrive\Desktop\myStuff\gaper\backlink_ai_engine\discovery\main.py"

echo Starting LLM Pipeline Worker...
start "LLM Pipeline" cmd /k "C:\Users\abdul\AppData\Local\Programs\Python\Python311\python.exe C:\Users\abdul\OneDrive\Desktop\myStuff\gaper\backlink_ai_engine\llm_pipeline\worker.py"

echo Starting Execution Router (Playwright)...
start "Execution Router" cmd /k "C:\Users\abdul\AppData\Local\Programs\Python\Python311\python.exe C:\Users\abdul\OneDrive\Desktop\myStuff\gaper\backlink_ai_engine\execution_router\worker.py"

echo Starting Intern Panel Dashboard...
start "Intern Panel" cmd /k "cd C:\Users\abdul\OneDrive\Desktop\myStuff\gaper\backlink_ai_engine\dashboard && C:\Users\abdul\AppData\Local\Programs\Python\Python311\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000"

echo =======================================
echo All services started!
echo You can access the dashboard at: http://localhost:8000
echo =======================================
pause
