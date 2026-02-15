@echo off
setlocal

echo Starting AI for Seniors desktop app...

where ollama >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Ollama not found. Install Ollama first.
  exit /b 1
)

curl -s http://127.0.0.1:11434/api/tags >nul 2>nul
if errorlevel 1 (
  start "Ollama" /min cmd /c "ollama serve"
  timeout /t 2 >nul
)

if exist .venv\Scripts\python.exe (
  set PY=.venv\Scripts\python.exe
) else (
  set PY=python
)

%PY% server\desktop_app.py

endlocal
