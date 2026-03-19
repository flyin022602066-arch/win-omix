@echo off
REM SPDX-License-Identifier: Apache-2.0
REM Quick setup script for oMLX Windows

setlocal enabledelayedexpansion

echo ========================================
echo oMLX Windows - Quick Setup
echo ========================================
echo.

REM Check Python installation
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python not found!
    echo.
    echo Please install Python 3.10+ from:
    echo https://www.python.org/downloads/
    echo.
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo [OK] Python found
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PY_VER=%%i
echo      Version: %PY_VER%
echo.

REM Check Python version (basic check)
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python 3.10+ required!
    echo Current version: %PY_VER%
    pause
    exit /b 1
)

echo [OK] Python version is compatible
echo.

REM Create virtual environment
if not exist "venv" (
    echo [STEP 1/4] Creating virtual environment...
    python -m venv venv
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created
) else (
    echo [SKIP] Virtual environment already exists
)
echo.

REM Activate virtual environment
echo [STEP 2/4] Activating virtual environment...
call venv\Scripts\activate.bat
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to activate virtual environment
    pause
    exit /b 1
)
echo [OK] Virtual environment activated
echo.

REM Upgrade pip
echo [STEP 3/4] Upgrading pip...
python -m pip install --upgrade pip --quiet
if %ERRORLEVEL% neq 0 (
    echo [WARNING] Failed to upgrade pip (continuing...)
) else (
    echo [OK] pip upgraded
)
echo.

REM Install dependencies
echo [STEP 4/4] Installing oMLX Windows dependencies...
echo This may take several minutes...
echo.

python -m pip install -r requirements-windows.txt

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Failed to install dependencies
    echo.
    echo Try manual installation:
    echo   1. pip install onnxruntime-directml
    echo   2. pip install llama-cpp-python
    echo   3. pip install transformers accelerate
    echo   4. pip install pywin32 pystray
    echo.
    pause
    exit /b 1
)

echo [OK] Dependencies installed
echo.

REM Create default directories
echo [SETUP] Creating default directories...
if not exist "%USERPROFILE%\.omlx" mkdir "%USERPROFILE%\.omlx"
if not exist "%USERPROFILE%\.omlx\models" mkdir "%USERPROFILE%\.omlx\models"
if not exist "%USERPROFILE%\.omlx\logs" mkdir "%USERPROFILE%\.omlx\logs"
echo [OK] Directories created
echo.

REM Summary
echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo Next steps:
echo.
echo 1. Download models to:
echo    %USERPROFILE%\.omlx\models
echo.
echo 2. Start the server:
echo    omlx-windows.bat serve
echo.
echo 3. Or start the tray application:
echo    omlx-windows.bat tray
echo.
echo 4. Access admin panel:
echo    http://localhost:8000/admin
echo.
echo For help:
echo    omlx-windows.bat help
echo.
echo ========================================
echo.

pause
