@echo off
REM =====================================================================
REM Point de départ de l'installation : double-clique sur ce fichier.
REM Lance installer_serveur.ps1 sans que tu aies besoin de connaître
REM PowerShell (contourne la restriction d'exécution de script, qui
REM bloque sinon le double-clic direct sur un .ps1 par défaut sur
REM Windows).
REM =====================================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0installer_serveur.ps1"
