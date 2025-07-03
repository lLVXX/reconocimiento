@echo off
echo 🔄 Iniciando Celery Worker...
cd /d %~dp0
call reconocimiento_venv\Scripts\activate
celery -A reconocimiento worker --loglevel=info
pause
