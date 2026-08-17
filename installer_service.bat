@echo off
REM =====================================================================
REM Installe la GMAO comme service Windows (démarrage automatique).
REM À lancer UNE SEULE FOIS, après avoir vérifié que demarrer_production.bat
REM fonctionne correctement (voir GUIDE_DEPLOIEMENT.md).
REM =====================================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0installer_service.ps1"
