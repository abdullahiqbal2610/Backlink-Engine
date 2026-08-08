@echo off
echo Starting Gaper Backlink Engine Local Workers...
echo ===============================================

echo Starting Discovery Worker...
start "Discovery Worker (Serper/RSS)" cmd /k "python discovery/worker.py"

echo Starting LLM Drafter Worker...
start "LLM Drafter (Gemini)" cmd /k "python llm_drafter/worker.py"

echo Starting Execution Router...
start "Execution Router (Playwright)" cmd /k "python execution_router/worker.py"

echo All workers started in separate windows! You can now see the live logs.
pause
