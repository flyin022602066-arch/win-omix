@echo off
REM SPDX-License-Identifier: Apache-2.0
REM Windows batch launcher for oMLX

setlocal enabledelayedexpansion

REM Configuration
set OMLX_VERSION=1.0.0-windows
set OMLX_NAME=oMLX Windows
set PYTHON_EXEC=python
set VENV_DIR=venv

REM Colors
set "GREEN=[32m"
set "YELLOW=[33m"
set "RED=[31m"
set "RESET=[0m"

REM Title
echo %GREEN%
echo ========================================
echo %OMLX_NAME% v%OMLX_VERSION%
echo ========================================
echo %RESET%

REM Check Python installation
where %PYTHON_EXEC% >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo %RED%Error: Python not found!%RESET%
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Check Python version
for /f "tokens=2" %%i in ('%PYTHON_EXEC% --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Python version: %PYTHON_VERSION%

REM Check if virtual environment exists
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo %YELLOW%Virtual environment not found. Creating...%RESET%
    %PYTHON_EXEC% -m venv %VENV_DIR%
    
    if %ERRORLEVEL% neq 0 (
        echo %RED%Failed to create virtual environment%RESET%
        pause
        exit /b 1
    )
    
    echo %GREEN%Virtual environment created successfully%RESET%
)

REM Activate virtual environment
call %VENV_DIR%\Scripts\activate.bat

REM Check if omlx is installed
%PYTHON_EXEC% -c "import omlx" 2>nul
if %ERRORLEVEL% neq 0 (
    echo %YELLOW%oMLX not installed. Installing...%RESET%
    
    REM Upgrade pip first
    %PYTHON_EXEC% -m pip install --upgrade pip
    
    REM Install omlx-windows
    %PYTHON_EXEC% -m pip install -e . -f pyproject.windows.toml
    
    if %ERRORLEVEL% neq 0 (
        echo %RED%Failed to install oMLX%RESET%
        pause
        exit /b 1
    )
    
    echo %GREEN%oMLX installed successfully%RESET%
)

REM Parse command line arguments
set COMMAND=%1
shift

if "%COMMAND%"=="" (
    goto :menu
)

if "%COMMAND%"=="serve" (
    goto :serve
)

if "%COMMAND%"=="tray" (
    goto :tray
)

if "%COMMAND%"=="service" (
    goto :service
)

if "%COMMAND%"=="install" (
    goto :install_deps
)

if "%COMMAND%"=="update" (
    goto :update
)

if "%COMMAND%"=="clean" (
    goto :clean
)

echo %RED%Unknown command: %COMMAND%%RESET%
goto :menu

:menu
echo.
echo Available commands:
echo   serve [options]    - Start inference server
echo   tray              - Start system tray application
echo   service [cmd]     - Manage Windows service (install/start/stop/status)
echo   install           - Install dependencies
echo   update            - Update oMLX
echo   clean             - Clean temporary files
echo   help              - Show this help
echo.
set /p COMMAND="Enter command (or press Enter for 'serve'): "
if "%COMMAND%"=="" set COMMAND=serve
goto :dispatch

:dispatch
if "%COMMAND%"=="serve" goto :serve
if "%COMMAND%"=="tray" goto :tray
if "%COMMAND%"=="service" goto :service
if "%COMMAND%"=="install" goto :install_deps
if "%COMMAND%"=="update" goto :update
if "%COMMAND%"=="clean" goto :clean
echo %RED%Unknown command%RESET%
goto :end

:serve
echo %GREEN%Starting oMLX server...%RESET%
%PYTHON_EXEC% -m omlx.cli serve %*
goto :end

:tray
echo %GREEN%Starting system tray application...%RESET%
start "" %PYTHON_EXEC% -m omlx.tray_app
echo Tray application started in background
goto :end

:service
set SERVICE_CMD=%1
shift

if "%SERVICE_CMD%"=="install" (
    echo %GREEN%Installing Windows service...%RESET%
    %PYTHON_EXEC% -m omlx.integrations.windows_service install %*
    goto :end
)

if "%SERVICE_CMD%"=="uninstall" (
    echo %GREEN%Uninstalling Windows service...%RESET%
    %PYTHON_EXEC% -m omlx.integrations.windows_service uninstall
    goto :end
)

if "%SERVICE_CMD%"=="start" (
    echo %GREEN%Starting service...%RESET%
    %PYTHON_EXEC% -m omlx.integrations.windows_service start
    goto :end
)

if "%SERVICE_CMD%"=="stop" (
    echo %GREEN%Stopping service...%RESET%
    %PYTHON_EXEC% -m omlx.integrations.windows_service stop
    goto :end
)

if "%SERVICE_CMD%"=="status" (
    echo %GREEN%Service status:%RESET%
    %PYTHON_EXEC% -m omlx.integrations.windows_service status
    goto :end
)

echo %RED%Usage: omlx service [install^|uninstall^|start^|stop^|status]%RESET%
goto :end

:install_deps
echo %GREEN%Installing dependencies...%RESET%
%PYTHON_EXEC% -m pip install --upgrade pip
%PYTHON_EXEC% -m pip install -e . -f pyproject.windows.toml
echo %GREEN%Dependencies installed%RESET%
goto :end

:update
echo %GREEN%Updating oMLX...%RESET%
%PYTHON_EXEC% -m pip install --upgrade -e . -f pyproject.windows.toml
echo %GREEN%oMLX updated%RESET%
goto :end

:clean
echo %GREEN%Cleaning temporary files...%RESET%
if exist ".eggs" rmdir /s /q ".eggs"
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "*.egg-info" del /q "*.egg-info"
echo %GREEN%Clean complete%RESET%
goto :end

:end
echo.
echo %GREEN%Done.%RESET%
if not "%COMMAND%"=="tray" (
    pause
)
exit /b 0
