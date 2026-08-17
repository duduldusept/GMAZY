# =====================================================================
# INSTALLATION DU SERVICE WINDOWS (démarrage + redémarrage automatiques)
# =====================================================================
# À exécuter UNE SEULE FOIS, après avoir lancé installer.bat et vérifié
# que demarrer_production.bat fonctionne correctement.
#
# Ce script télécharge NSSM tout seul (aucune installation manuelle) et
# enregistre la GMAO comme service Windows : elle démarrera alors
# automatiquement avec le serveur, et se relancera toute seule si le
# processus plante. Aucune configuration à faire dans ce fichier.
# =====================================================================

# ---- Élévation automatique (droits administrateur nécessaires pour créer un service) ----
$estAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $estAdmin) {
    Write-Host "Droits administrateur requis : relance avec élévation (une nouvelle fenêtre va s'ouvrir)..." -ForegroundColor Yellow
    Start-Process powershell -Verb RunAs -ArgumentList "-NoExit", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$PSCommandPath`""
    exit
}

$ErrorActionPreference = "Stop"
$ProjectPath = $PSScriptRoot
$NomService = "GmaoDjango"
$NssmDir = Join-Path $ProjectPath "nssm"
$NssmExe = Join-Path $NssmDir "nssm.exe"
$NssmUrl = "https://nssm.cc/release/nssm-2.24.zip"

try {
    Set-Location $ProjectPath
    Write-Host "===== Installation du service Windows =====" -ForegroundColor Cyan

    if (-not (Test-Path ".\demarrer_production.bat")) {
        throw "demarrer_production.bat introuvable dans $ProjectPath. Ce script doit être dans le même dossier que le reste du projet."
    }

    # ---- 1. Télécharger NSSM si absent (installé une seule fois, dans le projet lui-même) ----
    if (-not (Test-Path $NssmExe)) {
        Write-Host "Téléchargement de NSSM..." -ForegroundColor Yellow
        $zipPath = "$env:TEMP\nssm.zip"
        Invoke-WebRequest -Uri $NssmUrl -OutFile $zipPath
        $extractDir = "$env:TEMP\nssm_extract"
        if (Test-Path $extractDir) { Remove-Item $extractDir -Recurse -Force }
        Expand-Archive -Path $zipPath -DestinationPath $extractDir -Force
        New-Item -Path $NssmDir -ItemType Directory -Force | Out-Null
        $arch = if ([Environment]::Is64BitOperatingSystem) { "win64" } else { "win32" }
        $nssmSource = Get-ChildItem -Path $extractDir -Recurse -Filter "nssm.exe" | Where-Object { $_.FullName -like "*$arch*" } | Select-Object -First 1
        if (-not $nssmSource) {
            throw "Impossible de trouver nssm.exe dans l'archive téléchargée."
        }
        Copy-Item $nssmSource.FullName $NssmExe
        Remove-Item $zipPath -Force
        Remove-Item $extractDir -Recurse -Force
        Write-Host "NSSM installé dans $NssmDir" -ForegroundColor Green
    } else {
        Write-Host "NSSM déjà présent." -ForegroundColor Green
    }

    # ---- 2. Enregistrer (ou redémarrer) le service ----
    $serviceExiste = Get-Service -Name $NomService -ErrorAction SilentlyContinue

    if ($serviceExiste) {
        Write-Host "Le service '$NomService' existe déjà. Redémarrage..." -ForegroundColor Yellow
        & $NssmExe restart $NomService
    } else {
        Write-Host "Enregistrement du service '$NomService'..." -ForegroundColor Yellow
        & $NssmExe install $NomService (Join-Path $ProjectPath "demarrer_production.bat")
        & $NssmExe set $NomService AppDirectory $ProjectPath
        & $NssmExe set $NomService Start SERVICE_AUTO_START
        & $NssmExe set $NomService DisplayName "GMAO - Serveur Django"
        & $NssmExe set $NomService Description "Sert l'application GMAO en continu (waitress). Redemarrage automatique si le serveur redemarre ou si le processus plante."
        & $NssmExe start $NomService
        Write-Host "Service installé et démarré." -ForegroundColor Green
    }

    Start-Sleep -Seconds 2
    $statut = (Get-Service -Name $NomService).Status
    Write-Host ""
    Write-Host "===== Statut du service : $statut =====" -ForegroundColor Cyan
    if ($statut -eq "Running") {
        Write-Host "La GMAO tourne en continu et redémarrera automatiquement avec le serveur." -ForegroundColor Green
        Write-Host "Prochaine étape : utilise mettre_a_jour.bat pour les futures mises à jour." -ForegroundColor Green
    } else {
        Write-Host "Le service n'est pas démarré. Ouvre services.msc, cherche '$NomService' pour voir le détail." -ForegroundColor Red
    }
}
catch {
    Write-Host ""
    Write-Host "===== ERREUR =====" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    Write-Host "L'installation du service a échoué. Corrige le problème ci-dessus puis relance ce script." -ForegroundColor Red
}

Write-Host ""
Read-Host "Appuie sur Entrée pour fermer cette fenêtre"
