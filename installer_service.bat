@echo off
REM =====================================================================
REM Installe la GMAO comme service Windows (demarrage automatique).
REM A lancer UNE SEULE FOIS, apres avoir verifie que demarrer_production.bat
REM fonctionne correctement (voir GUIDE_DEPLOIEMENT.md).
REM =====================================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0installer_service.ps1"
