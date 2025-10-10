@echo off
REM Автоматический запуск Celery Worker

cd /d C:\allcodes\ad\Folder
call ..\.venv\Scripts\activate.bat
celery -A app worker --loglevel=info --pool=solo

pause

