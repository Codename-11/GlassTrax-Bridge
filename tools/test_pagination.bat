@echo off
REM Test pagination for /orders/fabs endpoint
REM Usage: tools\test_pagination.bat [date]

set DATE=%1
if "%DATE%"=="" set DATE=%date:~10,4%-%date:~4,2%-%date:~7,2%

echo Testing pagination for date: %DATE%
python32\python.exe tools\test_pagination.py --date %DATE% %2 %3 %4
