@echo off
REM GlassTrax Bridge - Full Development Environment
REM Starts API and Portal in a single terminal
REM Documentation: https://codename-11.github.io/GlassTrax-Bridge/

cd /d "%~dp0"

echo.
echo  GlassTrax Bridge - Development Mode
echo  ====================================
echo.

REM Check Python
if not exist "python32\python.exe" (
    echo ERROR: 32-bit Python not found in python32\
    pause
    exit /b 1
)

REM Check Node
where npm >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: npm not found - Install Node.js first
    pause
    exit /b 1
)

REM Install root dependencies if needed (concurrently)
if not exist "node_modules" (
    echo Installing root dependencies...
    npm install
)

REM Install portal dependencies if needed
if not exist "portal\node_modules" (
    echo Installing portal dependencies...
    pushd portal && npm install && popd
)

echo.
echo Starting services...
echo.
echo   Portal:  http://localhost:5173
echo   Swagger: http://localhost:5173/api/docs
echo   API:     http://localhost:5173/api/v1
echo   Health:  http://localhost:5173/health
echo   Docs:    https://codename-11.github.io/GlassTrax-Bridge/
echo.
echo Press Ctrl+C to stop all services
echo.

REM Run all services with concurrently
npm run dev
