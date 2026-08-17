@echo off
REM =====================================================================
REM Met à jour la GMAO déjà installée sur le serveur, puis redémarre le
REM service Windows. Aucune configuration à faire : tout est détecté
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

REM Si le projet est versionné avec Git, on récupère la dernière version.
REM Sinon (fichiers copiés à la main), on continue directement avec les
REM étapes ci-dessous : copie d'abord les nouveaux fichiers avant de lancer
REM ce script.
if exist ".git" (
    echo Récupération de la dernière version via Git...
    git pull
) else (
    echo [Pas de dépôt Git détecté - assure-toi d'avoir déjà copié les nouveaux fichiers sur le serveur avant de continuer.]
)

call venv\Scripts\activate.bat

echo Installation des dépendances (au cas où requirements.txt aurait changé)...
pip install -r requirements.txt --quiet

echo Application des migrations de base de données...
python manage.py migrate

echo Rassemblement des fichiers statiques...
python manage.py collectstatic --noinput

if exist "%NSSM_EXE%" (
    echo Redémarrage du service %NOM_SERVICE%...
    "%NSSM_EXE%" restart %NOM_SERVICE%
) else (
    echo [NSSM introuvable - le service n'a peut-etre pas encore ete installe.]
    echo [Lance installer_service.bat une fois, puis reessaie une mise a jour.]
)

echo.
echo ===== Mise a jour terminee =====
echo.
pause
