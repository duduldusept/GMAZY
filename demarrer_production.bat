@echo off
REM =====================================================================
REM Lance la GMAO en mode production avec waitress.
REM C'est CE script que le service Windows (NSSM) doit lancer, pas
REM lancer_serveur.bat (qui utilise le serveur de developpement Django,
REM non prevu pour tourner en continu).
REM Aucune configuration a faire : le dossier du projet est detecte
REM automatiquement (celui ou se trouve ce fichier).
REM =====================================================================
setlocal
set PROJECT_PATH=%~dp0
set PORT=8000

cd /d "%PROJECT_PATH%"

if not exist "venv\Scripts\activate.bat" (
    echo [ERREUR] Environnement virtuel introuvable ^(venv\Scripts\activate.bat^).
    echo Lance d'abord installer.bat pour installer la GMAO.
    echo.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

echo Demarrage de la GMAO (waitress) sur le port %PORT%...
waitress-serve --host=0.0.0.0 --port=%PORT% config.wsgi:application

echo.
echo [Le serveur s'est arrete, ou n'a pas pu demarrer - regarde le message ci-dessus.]
pause
