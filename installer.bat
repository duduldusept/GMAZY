@echo off
REM =====================================================================
REM Point de depart de l'installation : double-clique sur ce fichier.
REM Lance installer_serveur.ps1 sans que tu aies besoin de connaitre
REM PowerShell (contourne la restriction d'execution de script, qui
REM bloque sinon le double-clic direct sur un .ps1 par defaut sur
REM Windows).
REM =====================================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0installer_serveur.ps1"
