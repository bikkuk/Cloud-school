@echo off
setlocal

echo === AI for Seniors Offline Installer ===

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python was not found. Please install Python 3.10+ first.
  exit /b 1
)

python --version

echo.
echo Installing Python dependencies...
python -m pip install --upgrade pip
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

echo Checking for local model qwen2.5:7b...
ollama list | findstr /C:"qwen2.5:7b" >nul
if errorlevel 1 (
  echo [WARNING] Model qwen2.5:7b not found locally.
  echo Run this once (internet needed only for first download):
  echo    ollama pull qwen2.5:7b
) else (
  echo Model qwen2.5:7b is installed.
)

echo.
echo Install complete.
echo Next step: run start.bat
endlocal
