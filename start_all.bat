@echo off
echo Starting AI Backlink Engine...
echo =======================================

echo Connecting to Cloud Databases (Neon Postgres & Upstash Redis)...

echo Initializing Database Schema...
C:\Users\abdul\AppData\Local\Programs\Python\Python311\python.exe C:\Users\abdul\.gemini\antigravity-ide\brain\404d635a-ec4b-4d10-950a-a464afcf263d\scratch\run_sql.py

echo Starting Discovery Engine...
start "Discovery Engine" cmd /k "C:\Users\abdul\AppData\Local\Programs\Python\Python311\python.exe C:\Users\abdul\OneDrive\Desktop\myStuff\gaper\backlink_ai_engine\discovery\main.py"

echo Starting LLM Pipeline Worker...
start "LLM Pipeline" cmd /k "C:\Users\abdul\AppData\Local\Programs\Python\Python311\python.exe C:\Users\abdul\OneDrive\Desktop\myStuff\gaper\backlink_ai_engine\llm_pipeline\worker.py"

echo Starting LLM Parser Worker...
start "LLM Parser" cmd /k "C:\Users\abdul\AppData\Local\Programs\Python\Python311\python.exe C:\Users\abdul\OneDrive\Desktop\myStuff\gaper\backlink_ai_engine\llm_pipeline\parser_worker.py"

echo Starting Execution Router (Playwright)...
start "Execution Router" cmd /k "C:\Users\abdul\AppData\Local\Programs\Python\Python311\python.exe C:\Users\abdul\OneDrive\Desktop\myStuff\gaper\backlink_ai_engine\execution_router\worker.py"

echo Starting Intern Panel Dashboard...
start "Intern Panel" cmd /k "cd C:\Users\abdul\OneDrive\Desktop\myStuff\gaper\backlink_ai_engine\dashboard && C:\Users\abdul\AppData\Local\Programs\Python\Python311\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000"

echo =======================================
echo All services started!
echo You can access the Dashboard at: http://localhost:8000
echo - Check the "Discovered Sites" tab to approve new platforms.
echo - Approving a site will instantly launch a browser for you to log in!
echo =======================================
pause
