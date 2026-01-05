@echo off
REM GlassTrax DSN Inspection Tool Wrapper
REM Uses bundled 32-bit Python for Pervasive ODBC compatibility

setlocal

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."

REM Check if python32 exists
if not exist "%PROJECT_ROOT%\python32\python.exe" (
    echo ERROR: python32 not found at %PROJECT_ROOT%\python32\python.exe
    echo Please ensure 32-bit Python is installed in the python32 directory.
    exit /b 1
)

REM Run the inspection tool with all arguments
"%PROJECT_ROOT%\python32\python.exe" "%SCRIPT_DIR%inspect_dsn.py" %*
