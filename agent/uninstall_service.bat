@echo off
REM GlassTrax API Agent - Windows Service Uninstaller
REM Stops and removes the GlassTrax API Agent Windows Service

setlocal

set SERVICE_NAME=GlassTraxAPIAgent

echo.
echo ========================================
echo   GlassTrax API Agent - Service Uninstaller
echo ========================================
echo.

REM Check if NSSM is available
where nssm >nul 2>&1
if %ERRORLEVEL% neq 0 (
    if exist "%~dp0nssm.exe" (
        set NSSM_PATH=%~dp0nssm.exe
    ) else (
        echo ERROR: NSSM not found!
        echo.
        echo Please ensure nssm.exe is in this directory or in PATH.
        echo.
        pause
        exit /b 1
    )
) else (
    set NSSM_PATH=nssm
)

REM Check if service exists
sc query %SERVICE_NAME% >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Service '%SERVICE_NAME%' is not installed.
    echo.
    pause
    exit /b 0
)

echo Stopping service...
%NSSM_PATH% stop %SERVICE_NAME% >nul 2>&1
timeout /t 2 >nul

echo Removing service...
%NSSM_PATH% remove %SERVICE_NAME% confirm

echo.
echo ========================================
echo   Service removed successfully!
echo ========================================
echo.
echo The GlassTrax API Agent service has been uninstalled.
echo You can reinstall it with install_service.bat
echo.

pause
