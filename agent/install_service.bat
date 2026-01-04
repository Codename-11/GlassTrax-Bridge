@echo off
REM GlassTrax Agent - Windows Service Installation
REM Uses NSSM (Non-Sucking Service Manager) to install agent as Windows Service
REM
REM Prerequisites:
REM   1. Download NSSM from https://nssm.cc/download
REM   2. Extract nssm.exe to this directory or add to PATH
REM
REM The service will:
REM   - Start automatically on Windows boot
REM   - Restart automatically if it crashes
REM   - Run under the SYSTEM account

setlocal

cd /d "%~dp0.."
set PROJECT_DIR=%CD%
set SERVICE_NAME=GlassTraxAgent
set PYTHON_PATH=%PROJECT_DIR%\python32\python.exe

echo.
echo ========================================
echo   GlassTrax Agent - Service Installer
echo ========================================
echo.
echo Project Directory: %PROJECT_DIR%
echo Python Path: %PYTHON_PATH%
echo Service Name: %SERVICE_NAME%
echo.

REM Check if NSSM is available
where nssm >nul 2>&1
if %ERRORLEVEL% neq 0 (
    if exist "%~dp0nssm.exe" (
        set NSSM_PATH=%~dp0nssm.exe
    ) else (
        echo ERROR: NSSM not found!
        echo.
        echo Please download NSSM from https://nssm.cc/download
        echo and place nssm.exe in this directory or add to PATH.
        echo.
        pause
        exit /b 1
    )
) else (
    set NSSM_PATH=nssm
)

REM Check if service already exists
sc query %SERVICE_NAME% >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo Service already exists. Stopping and removing...
    %NSSM_PATH% stop %SERVICE_NAME% >nul 2>&1
    %NSSM_PATH% remove %SERVICE_NAME% confirm >nul 2>&1
    timeout /t 2 >nul
)

echo Installing service...

REM Install service
%NSSM_PATH% install %SERVICE_NAME% "%PYTHON_PATH%" -m uvicorn agent.main:app --host 0.0.0.0 --port 8001

REM Configure service
%NSSM_PATH% set %SERVICE_NAME% AppDirectory "%PROJECT_DIR%"
%NSSM_PATH% set %SERVICE_NAME% Description "GlassTrax Agent - ODBC Query Service for GlassTrax ERP"
%NSSM_PATH% set %SERVICE_NAME% DisplayName "GlassTrax Agent"
%NSSM_PATH% set %SERVICE_NAME% Start SERVICE_AUTO_START

REM Configure restart on failure
%NSSM_PATH% set %SERVICE_NAME% AppExit Default Restart
%NSSM_PATH% set %SERVICE_NAME% AppRestartDelay 5000

REM Configure logging (optional - logs to Windows Event Log by default)
REM Uncomment to log to files:
REM %NSSM_PATH% set %SERVICE_NAME% AppStdout "%PROJECT_DIR%\logs\agent.log"
REM %NSSM_PATH% set %SERVICE_NAME% AppStderr "%PROJECT_DIR%\logs\agent.error.log"
REM %NSSM_PATH% set %SERVICE_NAME% AppStdoutCreationDisposition 4
REM %NSSM_PATH% set %SERVICE_NAME% AppStderrCreationDisposition 4

echo.
echo Service installed successfully!
echo.

REM Start the service
echo Starting service...
%NSSM_PATH% start %SERVICE_NAME%

timeout /t 3 >nul

REM Check status
sc query %SERVICE_NAME% | find "RUNNING" >nul
if %ERRORLEVEL% equ 0 (
    echo.
    echo ========================================
    echo   Service is running!
    echo ========================================
    echo.
    echo The agent is now running as a Windows Service.
    echo It will start automatically when Windows boots.
    echo.
    echo Agent URL: http://localhost:8001
    echo Health Check: http://localhost:8001/health
    echo API Docs: http://localhost:8001/docs
    echo.
    echo To manage the service:
    echo   - Stop:    net stop %SERVICE_NAME%
    echo   - Start:   net start %SERVICE_NAME%
    echo   - Remove:  uninstall_service.bat
    echo.
) else (
    echo.
    echo WARNING: Service installed but may not be running.
    echo Check Windows Event Viewer for errors.
    echo.
)

pause
