@echo off
setlocal

echo Starting AI for Seniors local server...
if not exist .venv\Scripts\activate.bat (
  echo [WARNING] .venv not found. Using system python.
  start "" http://127.0.0.1:5000
  python server\app.py
  exit /b %errorlevel%
)

call .venv\Scripts\activate.bat
start "" http://127.0.0.1:5000
python server\app.py

endlocal
