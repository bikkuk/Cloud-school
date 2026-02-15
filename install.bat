@echo off
setlocal

echo === AI for Seniors Offline USB Installer ===

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python not found. Install Python 3.10+ first.
  exit /b 1
)

python --version

echo.
if not exist .venv (
  echo Creating local virtual environment in project folder...
  python -m venv .venv
)

call .venv\Scripts\activate.bat
if errorlevel 1 (
  echo [ERROR] Could not activate virtual environment.
  exit /b 1
)

echo Installing local dependencies...
python -m pip install --upgrade pip
python -m pip install -r server\requirements.txt
if errorlevel 1 (
  echo [ERROR] Dependency install failed.
  exit /b 1
)

echo.
echo Verifying Tkinter for desktop GUI wrapper...
python -c "import tkinter" >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Tkinter is missing from this Python installation.
  echo Install a standard Python build that includes Tkinter.
  exit /b 1
)

where ollama >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Ollama is not installed.
  echo Install Ollama once, then run: ollama pull qwen2.5:7b
  exit /b 1
)

echo Checking for model qwen2.5:7b...
ollama list | findstr /C:"qwen2.5:7b" >nul
if errorlevel 1 (
  echo [WARNING] qwen2.5:7b not found locally.
  echo Run once with internet:
  echo    ollama pull qwen2.5:7b
  echo Then this app runs offline from USB.
) else (
  echo Model found. System is ready for offline use.
)

echo.
echo Install complete. Run start.bat to launch desktop GUI.
endlocal
