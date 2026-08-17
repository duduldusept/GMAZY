# =====================================================================
# INSTALLATION DE LA GMAO SUR LE SERVEUR WINDOWS
# =====================================================================
# À exécuter UNE SEULE FOIS lors de la première installation (ou après
# avoir copié une nouvelle version complète du projet sur le serveur).
#
# Aucune configuration à faire dans ce fichier : le script détecte tout
# seul le dossier dans lequel il se trouve. Copie le projet où tu veux
# sur le serveur, double-clique sur "installer.bat" (à côté de ce
# fichier) et c'est parti.
# =====================================================================

# ---- Élévation automatique (droits administrateur nécessaires pour installer Python) ----
$estAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $estAdmin) {
    Write-Host "Droits administrateur requis : relance avec élévation (une nouvelle fenêtre va s'ouvrir)..." -ForegroundColor Yellow
    Start-Process powershell -Verb RunAs -ArgumentList "-NoExit", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$PSCommandPath`""
    exit
}

$ErrorActionPreference = "Stop"
$ProjectPath = $PSScriptRoot
$PythonInstallerUrl = "https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe"

try {
    Set-Location $ProjectPath
    Write-Host "===== Installation de la GMAO =====" -ForegroundColor Cyan
    Write-Host "Dossier du projet : $ProjectPath" -ForegroundColor Green

    # ---- 1. Vérifier / installer Python ----
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCmd) {
        Write-Host "Python n'est pas installé. Téléchargement et installation en cours..." -ForegroundColor Yellow
        $installerPath = "$env:TEMP\python-installer.exe"
        Invoke-WebRequest -Uri $PythonInstallerUrl -OutFile $installerPath
        # Installation silencieuse, pour tous les utilisateurs, avec ajout au PATH
        Start-Process -FilePath $installerPath -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1 Include_launcher=1" -Wait
        Remove-Item $installerPath
        Write-Host "Python installé." -ForegroundColor Green
        # On recharge le PATH dans la session courante pour pouvoir continuer sans relancer le script
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
    } else {
        Write-Host "Python déjà installé : $(python --version)" -ForegroundColor Green
    }

    # ---- 2. Créer l'environnement virtuel s'il n'existe pas ----
    if (-not (Test-Path ".\venv")) {
        Write-Host "Création de l'environnement virtuel (venv)..." -ForegroundColor Yellow
        python -m venv venv
    } else {
        Write-Host "Environnement virtuel déjà présent." -ForegroundColor Green
    }

    # ---- 3. Installer les dépendances ----
    Write-Host "Installation des dépendances (requirements.txt)..." -ForegroundColor Yellow
    & ".\venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
    & ".\venv\Scripts\pip.exe" install -r requirements.txt --quiet

    # S'assurer que waitress (serveur de production) et whitenoise (fichiers
    # statiques) sont bien présents, et les ajouter à requirements.txt s'ils
    # n'y sont pas déjà, pour que les prochaines installations les incluent.
    foreach ($paquet in @("waitress", "whitenoise")) {
        $dejaPresent = Select-String -Path "requirements.txt" -Pattern "^$paquet" -Quiet -ErrorAction SilentlyContinue
        if (-not $dejaPresent) {
            Add-Content -Path "requirements.txt" -Value $paquet
            Write-Host "Ajouté à requirements.txt : $paquet" -ForegroundColor Yellow
        }
        & ".\venv\Scripts\pip.exe" install $paquet --quiet
    }

    # ---- 4. Créer le fichier .env s'il n'existe pas ----
    if (-not (Test-Path ".\.env")) {
        if (Test-Path ".\.env.example") {
            Copy-Item ".\.env.example" ".\.env"
            Write-Host "Fichier .env créé à partir de .env.example." -ForegroundColor Yellow
        } else {
            New-Item -Path ".\.env" -ItemType File | Out-Null
            Write-Host "Fichier .env vide créé." -ForegroundColor Yellow
        }

        # Génère une vraie clé secrète aléatoire (ne jamais garder de valeur par défaut en production)
        $secretKey = & ".\venv\Scripts\python.exe" -c "import secrets; print(secrets.token_urlsafe(50))"
        Add-Content -Path ".\.env" -Value "DJANGO_SECRET_KEY=$secretKey"
        Add-Content -Path ".\.env" -Value "DJANGO_DEBUG=False"
        Add-Content -Path ".\.env" -Value "DJANGO_ALLOWED_HOSTS=CHANGE-MOI"

        Write-Host ""
        Write-Host "IMPORTANT : ouvre le fichier .env et remplace DJANGO_ALLOWED_HOSTS par" -ForegroundColor Red
        Write-Host "l'adresse IP ou le nom du serveur (ex: 192.168.1.50,gmao.entreprise.local)." -ForegroundColor Red
        Write-Host ""
    } else {
        Write-Host "Fichier .env déjà présent, non modifié." -ForegroundColor Green
    }

    # ---- 5. Appliquer les migrations de base de données ----
    Write-Host "Application des migrations..." -ForegroundColor Yellow
    & ".\venv\Scripts\python.exe" manage.py migrate

    # ---- 6. Activer le mode WAL de SQLite ----
    # Réduit encore le (déjà faible) risque d'erreur "database is locked" si
    # deux personnes écrivent au même instant. Ce réglage est enregistré dans
    # le fichier db.sqlite3 lui-même : il suffit de l'activer une fois, il
    # reste actif ensuite (relancer cette commande ne fait rien si déjà activé).
    Write-Host "Activation du mode WAL sur la base de données..." -ForegroundColor Yellow
    & ".\venv\Scripts\python.exe" -c "import sqlite3; con = sqlite3.connect('db.sqlite3'); print('Mode journal :', con.execute('PRAGMA journal_mode=WAL;').fetchone()[0]); con.close()"

    # ---- 7. Rassembler les fichiers statiques (CSS/JS de l'admin Django) ----
    Write-Host "Rassemblement des fichiers statiques..." -ForegroundColor Yellow
    & ".\venv\Scripts\python.exe" manage.py collectstatic --noinput

    Write-Host ""
    Write-Host "===== Installation terminée avec succès =====" -ForegroundColor Cyan
    Write-Host "Prochaines étapes :"
    Write-Host "  1. Vérifie/complète le fichier .env (DJANGO_ALLOWED_HOSTS notamment)."
    Write-Host "  2. Crée un compte administrateur si besoin :"
    Write-Host "     .\venv\Scripts\python.exe manage.py createsuperuser"
    Write-Host "  3. Teste le serveur manuellement : demarrer_production.bat"
    Write-Host "  4. Une fois validé, double-clique sur installer_service.bat pour"
    Write-Host "     l'installer comme service Windows (démarrage automatique)."
}
catch {
    Write-Host ""
    Write-Host "===== ERREUR =====" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    Write-Host "L'installation s'est arrêtée. Corrige le problème ci-dessus puis relance" -ForegroundColor Red
    Write-Host "ce script (il est sans risque de le relancer plusieurs fois)." -ForegroundColor Red
}

Write-Host ""
Read-Host "Appuie sur Entrée pour fermer cette fenêtre"
