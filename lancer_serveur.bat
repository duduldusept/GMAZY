@echo off
cd /d "%~dp0"

if not exist venv\Scripts\activate.bat (
    echo Environnement virtuel introuvable. Creation...
    python -m venv venv
)

call venv\Scripts\activate.bat

pip install -r requirements.txt --quiet

python manage.py migrate

python manage.py runserver

pause
