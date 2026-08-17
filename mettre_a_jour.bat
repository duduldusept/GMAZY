@echo off
REM =====================================================================
REM Met a jour la GMAO deja installee sur le serveur, puis redemarre le
REM service Windows. Aucune configuration a faire : tout est detecte
REM automatiquement (dossier du projet, emplacement de NSSM).
REM =====================================================================
setlocal
set PROJECT_PATH=%~dp0
set NOM_SERVICE=GmaoDjango
set NSSM_EXE=%PROJECT_PATH%nssm\nssm.exe

cd /d "%PROJECT_PATH%"

echo.
echo ===== Mise a jour de la GMAO =====
echo.

REM Si le projet est versionne avec Git, on recupere la derniere version.
REM Sinon (fichiers copies a la main), on continue directement avec les
REM etapes ci-dessous : copie d'abord les nouveaux fichiers avant de lancer
REM ce script.
if exist ".git" (
    echo Recuperation de la derniere version via Git...
    git pull
) else (
    echo [Pas de depot Git detecte - assure-toi d'avoir deja copie les nouveaux fichiers sur le serveur avant de continuer.]
)

call venv\Scripts\activate.bat

echo Installation des dependances (au cas ou requirements.txt aurait change)...
pip install -r requirements.txt --quiet

echo Application des migrations de base de donnees...
python manage.py migrate

echo Rassemblement des fichiers statiques...
python manage.py collectstatic --noinput

if exist "%NSSM_EXE%" (
    echo Redemarrage du service %NOM_SERVICE%...
    "%NSSM_EXE%" restart %NOM_SERVICE%
) else (
    echo [NSSM introuvable - le service n'a peut-etre pas encore ete installe.]
    echo [Lance installer_service.bat une fois, puis reessaie une mise a jour.]
)

echo.
echo ===== Mise a jour terminee =====
echo.
pause
