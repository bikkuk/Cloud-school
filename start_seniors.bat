@echo off
setlocal
cd /d "%~dp0"

echo Starting AI for Seniors local server...
if exist .venv\Scripts\activate.bat (
  call .venv\Scripts\activate.bat
) else (
  echo [WARNING] .venv not found. Using system python.
)

start "" http://127.0.0.1:5000
python server\app.py

endlocal
