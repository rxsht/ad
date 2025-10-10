@echo off
REM ========================================
REM Start Plagiarism Detection System
REM ========================================

echo.
echo ===================================
echo  Starting Plagiarism Detection System
echo ===================================
echo.

REM Check Docker Desktop
echo [1/4] Checking Docker...
docker ps >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Docker is not running. Start Docker Desktop!
    pause
    exit /b 1
)
echo [OK] Docker is running

REM Start Redis if not running
echo.
echo [2/4] Starting Redis...
docker ps | findstr redis >nul
if %errorlevel% neq 0 (
    docker start redis >nul 2>&1
    if %errorlevel% neq 0 (
        echo [+] Creating new Redis container...
        docker run -d -p 6379:6379 --name redis --restart unless-stopped redis:alpine
    )
)
echo [OK] Redis is running

REM Navigate to project directory
cd /d %~dp0\Folder

REM Activate virtual environment
call ..\.venv\Scripts\activate.bat

echo.
echo [3/4] Starting Django server...
echo [i] URL: http://localhost:8000
start "Django Server" cmd /k "python manage.py runserver"
timeout /t 3 >nul

echo.
echo [4/4] Starting Celery Worker...
start "Celery Worker" cmd /k "celery -A app worker --loglevel=info --pool=solo"
timeout /t 3 >nul

echo.
echo ===================================
echo  All services started! 
echo ===================================
echo.
echo  Django:  http://localhost:8000
echo  Admin:   http://localhost:8000/admin
echo.
echo  Celery Worker: running in background
echo  Redis: running in Docker
echo.
echo  To stop all services, close terminal windows
echo ===================================
echo.
pause
