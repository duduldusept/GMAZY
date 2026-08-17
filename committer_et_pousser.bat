@echo off
REM =====================================================================
REM Enregistre les modifications dans Git et les envoie sur GitHub.
REM À utiliser à chaque fois qu'on veut sauvegarder l'état actuel du
REM projet (nouvelle fonctionnalité, correction...) et pouvoir ensuite
REM le récupérer sur le serveur avec mettre_a_jour.bat.
REM =====================================================================
setlocal
cd /d "%~dp0"

echo.
echo ===== Fichiers modifies detectes =====
git status --short
echo.

set /p MESSAGE="Message de commit (description courte du changement) : "
if "%MESSAGE%"=="" set MESSAGE=Mise a jour

git add -A
git commit -m "%MESSAGE%"
git push

echo.
echo ===== Termine =====
pause
