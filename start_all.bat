@echo off
REM ========================================
REM Запуск всего проекта антиплагиата
REM ========================================

echo.
echo ===================================
echo  Запуск системы антиплагиата
echo ===================================
echo.

REM Проверяем Docker Desktop
echo [1/4] Проверка Docker...
docker ps >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Docker не запущен. Запустите Docker Desktop!
    pause
    exit /b 1
)
echo [OK] Docker работает

REM Запускаем Redis если не запущен
echo.
echo [2/4] Запуск Redis...
docker ps | findstr redis >nul
if %errorlevel% neq 0 (
    docker start redis >nul 2>&1
    if %errorlevel% neq 0 (
        echo [+] Создаём новый Redis контейнер...
        docker run -d -p 6379:6379 --name redis --restart unless-stopped redis:alpine
    )
)
echo [OK] Redis работает

REM Переходим в директорию проекта
cd /d %~dp0\Folder

REM Активируем venv
call ..\.venv\Scripts\activate.bat

echo.
echo [3/4] Запуск Django сервера...
echo [i] URL: http://localhost:8000
start "Django Server" cmd /k "python manage.py runserver"
timeout /t 3 >nul

echo.
echo [4/4] Запуск Celery Worker...
start "Celery Worker" cmd /k "celery -A app worker --loglevel=info --pool=solo"
timeout /t 3 >nul

echo.
echo ===================================
echo  Всё запущено! 
echo ===================================
echo.
echo  Django:  http://localhost:8000
echo  Admin:   http://localhost:8000/admin
echo.
echo  Celery Worker: работает в фоне
echo  Redis: работает в Docker
echo.
echo  Для остановки закройте окна терминалов
echo ===================================
echo.
pause

