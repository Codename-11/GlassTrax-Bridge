@echo off
REM ============================================
REM GlassTrax API Agent - Build Installer
REM ============================================
REM
REM This script builds a standalone Windows installer for the GlassTrax API Agent.
REM
REM Prerequisites:
REM   - Inno Setup 6 (https://jrsoftware.org/isdl.php)
REM   - PowerShell 5.1+
REM
REM Usage:
REM   BUILD_AGENT.bat           Build the installer
REM   BUILD_AGENT.bat -Clean    Clean build from scratch
REM
REM ============================================

echo.
echo ========================================
echo   GlassTrax API Agent - Build Installer
echo ========================================
echo.

REM Run the PowerShell build script
powershell -ExecutionPolicy Bypass -File "%~dp0build_agent.ps1" %*

echo.
pause
