@echo off
setlocal
cd /d "%~dp0"

echo === Cloud School Installer (Seniors + Agent Studio) ===

echo.
where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python was not found. Please install Python 3.10+ first.
  exit /b 1
)

python --version

echo.
if exist .venv (
  set /p RECREATE_VENV=.venv already exists. Recreate it? [y/N]: 
  if /I "%RECREATE_VENV%"=="y" (
    echo Removing existing .venv...
    rmdir /S /Q .venv
  )
)

if not exist .venv (
  echo Creating virtual environment...
  python -m venv .venv
  if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment.
    exit /b 1
  )
)

call .venv\Scripts\activate.bat
if errorlevel 1 (
  echo [ERROR] Failed to activate virtual environment.
  exit /b 1
)

echo Upgrading pip...
python -m pip install --upgrade pip
if errorlevel 1 (
  echo [ERROR] Failed to upgrade pip.
  exit /b 1
)

echo.
echo Installing AI for Seniors backend dependencies...
python -m pip install -r server\requirements.txt
if errorlevel 1 (
  echo [ERROR] Failed to install server dependencies.
  exit /b 1
)

echo.
echo Verifying Tkinter availability for Agent Studio...
python -c "import tkinter; print('Tkinter OK')"
if errorlevel 1 (
  echo [ERROR] Tkinter is not available in this Python installation.
  echo Please install a standard Python build from python.org with Tk support.
  exit /b 1
)

echo.
where ollama >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Ollama is not installed.
  echo Install Ollama first, then re-run install.bat.
  exit /b 1
)

echo Ollama detected.
echo.
echo Checking Ollama service reachability...
ollama list >nul 2>nul
if errorlevel 1 (
  echo [WARNING] Could not query Ollama right now.
  set /p START_OLLAMA=Do you want to continue anyway? [y/N]: 
  if /I not "%START_OLLAMA%"=="y" (
    echo Install cancelled. Start Ollama, then run install.bat again.
    exit /b 1
  )
)

echo.
set /p PULL_DEFAULT=Ensure model qwen2.5:7b is installed now? [Y/n]: 
if "%PULL_DEFAULT%"=="" set PULL_DEFAULT=Y
if /I "%PULL_DEFAULT%"=="y" (
  ollama pull qwen2.5:7b
)

echo.
set /p PULL_OPTIONAL=Install optional model llama3.1:8b now? [y/N]: 
if /I "%PULL_OPTIONAL%"=="y" (
  ollama pull llama3.1:8b
)

echo.
echo Validating final model list...
ollama list

echo.
echo Install complete.
echo Choose what to start:
echo   - Seniors web module: start.bat or start_seniors.bat
echo   - Agent Studio desktop: start_studio.bat
echo   - School of Thoughts page: start_school_of_thoughts.bat

endlocal
