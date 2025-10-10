@echo off
REM ========================================
REM Stop Plagiarism Detection System
REM ========================================

echo.
echo ===================================
echo  Stopping Plagiarism Detection System
echo ===================================
echo.

echo [1/2] Stopping Python processes...
taskkill /F /IM python.exe /T >nul 2>&1
taskkill /F /IM celery.exe /T >nul 2>&1
echo [OK] Processes stopped

echo.
echo [2/2] Stopping Redis...
docker stop redis >nul 2>&1
echo [OK] Redis stopped

echo.
echo ===================================
echo  All services stopped!
echo ===================================
echo.
pause
