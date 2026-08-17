@echo off
REM =====================================================================
REM Lance la GMAO en mode production avec waitress.
REM C'est CE script que le service Windows (NSSM) doit lancer, pas
REM lancer_serveur.bat (qui utilise le serveur de développement Django,
REM non prévu pour tourner en continu).
REM Aucune configuration à faire : le dossier du projet est détecté
REM automatiquement (celui où se trouve ce fichier).
REM =====================================================================
setlocal
set PROJECT_PATH=%~dp0
set PORT=8000

cd /d "%PROJECT_PATH%"
call venv\Scripts\activate.bat

echo Démarrage de la GMAO (waitress) sur le port %PORT%...
waitress-serve --host=0.0.0.0 --port=%PORT% config.wsgi:application
