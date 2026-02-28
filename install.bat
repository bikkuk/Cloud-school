@echo off
setlocal

echo === AI Agent Studio Installer (Offline-First) ===

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python was not found. Please install Python 3.10+ first.
  exit /b 1
)

python --version

echo.
if not exist .venv (
  echo Creating virtual environment...
  python -m venv .venv
)

call .venv\Scripts\activate.bat
if errorlevel 1 (
  echo [ERROR] Failed to activate virtual environment.
  exit /b 1
)

echo Upgrading pip...
python -m pip install --upgrade pip

echo Installing AI for Seniors backend dependencies...
python -m pip install -r server\requirements.txt
if errorlevel 1 (
  echo [ERROR] Failed to install Python dependencies.
  exit /b 1
)

echo.
where ollama >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Ollama is not installed.
  echo Install Ollama first, then run: ollama pull qwen2.5:7b
  exit /b 1
)

echo Ollama detected.

echo Checking for local models...
ollama list | findstr /C:"qwen2.5:7b" >nul
if errorlevel 1 (
  echo [WARNING] Model qwen2.5:7b not found locally.
  echo Run once: ollama pull qwen2.5:7b
) else (
  echo Model qwen2.5:7b is installed.
)

ollama list | findstr /C:"llama3.1:8b" >nul
if errorlevel 1 (
  echo [WARNING] Model llama3.1:8b not found locally.
  echo Optional: ollama pull llama3.1:8b
) else (
  echo Model llama3.1:8b is installed.
)

echo.
echo Install complete.
echo Next step: run start.bat
endlocal
