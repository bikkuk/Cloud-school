@echo off
setlocal
cd /d "%~dp0"

echo Starting AI Agent Studio...

if exist .venv\Scripts\activate.bat (
  call .venv\Scripts\activate.bat
) else (
  echo [WARNING] .venv not found. Using system python.
)

python -m agent_studio.app
if errorlevel 1 (
  echo [ERROR] Studio failed to start.
  echo Tip: Run install.bat, ensure Python 3.10+ and Ollama are installed.
  exit /b 1
)

endlocal
