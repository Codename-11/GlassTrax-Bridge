@echo off
REM GlassTrax API Agent - Manual Startup Script
REM Run this to start the agent manually (for development/testing)
REM For production, use install_service.bat to run as Windows Service

cd /d "%~dp0.."

echo.
echo ========================================
echo   GlassTrax API Agent
echo ========================================
echo.
echo Starting agent on port 8001...
echo Press Ctrl+C to stop
echo.

REM Use bundled 32-bit Python for ODBC compatibility
python32\python.exe -m uvicorn agent.main:app --host 0.0.0.0 --port 8001

pause
