# Guide de déploiement de la GMAO sur un serveur Windows

Tous les scripts se trouvent à la racine du projet, à côté de `manage.py`. Ils détectent automatiquement leur propre emplacement : **aucun chemin à modifier nulle part**, où que tu copies le dossier sur le serveur.

## Étape 1 — Copier le projet sur le serveur

Copie le dossier complet du projet (avec `db.sqlite3`, `.env`, tout le code, et ces scripts) à l'endroit de ton choix sur le serveur, par exemple `C:\gmao\gmao_entreprise`.

## Étape 2 — Installer (double-clic)

Double-clique sur **`installer.bat`**.

Une fenêtre de confirmation Windows va apparaître pour demander les droits administrateur (nécessaires pour installer Python si besoin) — accepte-la. Le script installe alors tout seul : Python (si absent), l'environnement virtuel, toutes les dépendances (y compris `waitress` et `whitenoise`, nécessaires pour la production), le fichier `.env` avec une clé secrète générée automatiquement, les migrations de base de données, le mode WAL sur la base (meilleure robustesse en cas d'accès simultanés), et les fichiers statiques de l'interface d'administration.

La fenêtre reste ouverte à la fin (ou affiche clairement l'erreur si quelque chose a échoué) — pas besoin de deviner si ça a fonctionné.

## Étape 3 — Configurer `.env`

Ouvre le fichier `.env` (créé à l'étape précédente) et complète la ligne :

```
DJANGO_ALLOWED_HOSTS=192.168.1.50,gmao.entreprise.local
```

Remplace `CHANGE-MOI` par l'adresse IP réelle du serveur (et/ou son nom si le réseau en a un). Sans ça, Django refusera de répondre aux requêtes. C'est la seule modification manuelle nécessaire dans tout le processus.

## Étape 4 — Créer un compte administrateur (si besoin)

Ouvre une invite de commande dans le dossier du projet et lance :

```
venv\Scripts\python.exe manage.py createsuperuser
```

## Étape 5 — Tester manuellement

Double-clique sur `demarrer_production.bat`. Une fenêtre doit indiquer que le serveur écoute sur le port 8000. Depuis un navigateur sur une autre machine du même réseau, teste `http://<adresse-ip-du-serveur>:8000`.

Si ça fonctionne, ferme la fenêtre (Ctrl+C) et passe à l'étape suivante pour que ça tourne en permanence, même après un redémarrage du serveur.

## Étape 6 — Installer comme service Windows (double-clic)

Double-clique sur **`installer_service.bat`**.

Là encore, accepte la demande de droits administrateur. Ce script télécharge NSSM tout seul (rien à installer manuellement, aucun site externe à visiter), l'installe directement dans un sous-dossier du projet, puis enregistre la GMAO comme service Windows nommé **GmaoDjango**, démarré automatiquement.

À partir de maintenant, la GMAO démarre automatiquement à chaque redémarrage du serveur, et se relance toute seule si jamais le processus plante — sans aucune intervention.

Pour vérifier ou piloter le service manuellement : ouvre `services.msc`, cherche **GmaoDjango**. Le statut doit être "En cours d'exécution" et le type de démarrage "Automatique".

## Étape 7 — Mises à jour futures

Quand une nouvelle version du code est prête : copie les fichiers modifiés dans le dossier du serveur (comme fait jusqu'ici), puis double-clique sur **`mettre_a_jour.bat`**. Il réinstalle les dépendances si besoin, applique les migrations, régénère les fichiers statiques, et redémarre le service automatiquement — pas besoin de droits administrateur pour cette étape.

Si un dépôt Git est utilisé (un dossier `.git` a été repéré dans le projet), ce même script fait aussi `git pull` avant tout le reste, automatiquement.

## Résumé — ce qu'il y a réellement à faire sur le serveur

Copier le dossier, double-cliquer sur `installer.bat`, remplir une ligne dans `.env`, double-cliquer sur `installer_service.bat`. Ensuite, plus rien à faire jusqu'à la prochaine mise à jour (`mettre_a_jour.bat`).

## Sécurité et bon sens

Ne jamais repasser `DJANGO_DEBUG=True` en production (le `.env` généré met `False` par défaut, ne pas y toucher). Garder `DJANGO_SECRET_KEY` secrète (ne pas la partager, ne pas la mettre dans un dépôt Git public). Si le serveur est accessible depuis l'extérieur du réseau local (pas seulement en interne), prévoir un reverse proxy (Caddy ou IIS) devant waitress pour ajouter du HTTPS — m'en parler le moment venu, ça se met en place facilement.

## Sauvegardes

`db.sqlite3` est un fichier unique : le sauvegarder régulièrement suffit à sauvegarder toutes les données (le mode WAL peut créer temporairement des fichiers `db.sqlite3-wal` et `db.sqlite3-shm` à côté — les inclure aussi dans la sauvegarde si présents). Sur le serveur, créer une tâche planifiée Windows (Planificateur de tâches → Créer une tâche de base → déclencheur quotidien) qui copie ces fichiers vers un dossier de sauvegarde daté, par exemple avec une commande PowerShell :

```powershell
Copy-Item "C:\gmao\gmao_entreprise\db.sqlite3*" "C:\gmao\sauvegardes\" -Include "db.sqlite3*"
Rename-Item "C:\gmao\sauvegardes\db.sqlite3" "db_$(Get-Date -Format yyyyMMdd_HHmmss).sqlite3"
```
