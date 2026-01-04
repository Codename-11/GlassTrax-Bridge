@echo off
REM GlassTrax Bridge - Windows Production Server
REM Builds portal and docs, then runs API serving everything

cd /d "%~dp0"

echo.
echo  GlassTrax Bridge - Production Mode
echo  ===================================
echo.

REM Check Python
if not exist "python32\python.exe" (
    echo ERROR: 32-bit Python not found in python32\
    pause
    exit /b 1
)

REM Check Node (needed for building)
where npm >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: npm not found - required for building portal and docs
    pause
    exit /b 1
)

REM Install dependencies if needed
if not exist "portal\node_modules" (
    echo Installing portal dependencies...
    pushd portal && npm install && popd
)

if not exist "docs\node_modules" (
    echo Installing docs dependencies...
    pushd docs && npm install && popd
)

REM Build portal
echo.
echo Building portal...
pushd portal
call npm run build
if %ERRORLEVEL% neq 0 (
    echo ERROR: Portal build failed
    popd
    pause
    exit /b 1
)
popd
echo Portal built successfully.

REM Build docs
echo.
echo Building VitePress docs...
pushd docs
call npm run build
if %ERRORLEVEL% neq 0 (
    echo ERROR: Docs build failed
    popd
    pause
    exit /b 1
)
popd
echo Docs built successfully.

echo.
echo ===================================
echo  Starting Production Server
echo ===================================
echo.
echo   Portal:       http://localhost:8000
echo   User Docs:    http://localhost:8000/docs
echo   API:          http://localhost:8000/api/v1
echo   Swagger:      http://localhost:8000/api/docs
echo.
echo Press Ctrl+C to stop
echo.

REM Run API in production mode (no reload, single worker)
python32\python.exe -m uvicorn api.main:app --host 0.0.0.0 --port 8000
