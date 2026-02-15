@echo off
setlocal

echo Starting AI Agent Studio...

if not exist .venv\Scripts\activate.bat (
  echo [ERROR] Missing virtual environment. Run install.bat first.
  exit /b 1
)

call .venv\Scripts\activate.bat
python agent_studio\app.py

endlocal
