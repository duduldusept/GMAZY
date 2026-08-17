# Pense-bête — Déploiement & mises à jour de la GMAO

Dépôt GitHub : `https://github.com/duduldusept/GMAZY.git`
(guide détaillé complet : `GUIDE_DEPLOIEMENT.md`)

## Première installation sur un nouveau serveur

1. Récupérer le projet sur le serveur : `git clone https://github.com/duduldusept/GMAZY.git`
2. Double-clic sur **`installer.bat`** → accepter la demande de droits admin. Installe Python, l'environnement, les dépendances, crée `.env`, applique les migrations, active le mode WAL, prépare les fichiers statiques.
3. Ouvrir `.env` → remplacer `CHANGE-MOI` par l'IP/le nom du serveur dans `DJANGO_ALLOWED_HOSTS`.
4. (si besoin) créer un compte admin : `venv\Scripts\python.exe manage.py createsuperuser`
5. Tester : double-clic sur **`demarrer_production.bat`**, ouvrir `http://<ip-du-serveur>:8000` depuis un autre poste.
6. Double-clic sur **`installer_service.bat`** → accepter la demande de droits admin. Installe NSSM tout seul et crée le service Windows **GmaoDjango** (démarrage automatique).

C'est terminé : la GMAO tourne en continu et redémarre toute seule avec le serveur.

## Mettre à jour la GMAO (après une modification du code)

**Sur le poste de développement** (une fois les changements prêts) :

- Double-clic sur **`committer_et_pousser.bat`** → taper une courte description → envoie automatiquement sur GitHub.

**Sur le serveur** :

- Double-clic sur **`mettre_a_jour.bat`** → récupère la dernière version (`git pull`), réinstalle les dépendances si besoin, applique les migrations, régénère les fichiers statiques, redémarre le service automatiquement.

Aucun droit administrateur nécessaire pour cette étape.

## Commandes utiles en cas de besoin

| Action | Commande / emplacement |
|---|---|
| Voir si le service tourne | `services.msc` → chercher **GmaoDjango** |
| Redémarrer le service à la main | `nssm\nssm.exe restart GmaoDjango` (depuis le dossier du projet) |
| Arrêter le service | `nssm\nssm.exe stop GmaoDjango` |
| Voir les fichiers modifiés avant d'envoyer sur GitHub | `git status` |
| Voir l'historique des mises à jour | `git log --oneline` |

## À ne jamais oublier

Ne jamais repasser `DJANGO_DEBUG=True` en production. `.env`, `db.sqlite3` et `venv/` ne partent jamais sur GitHub — c'est normal, ils sont protégés par `.gitignore` (secrets et données réelles n'ont rien à faire dans un dépôt de code). Sauvegarder `db.sqlite3` régulièrement (et `db.sqlite3-wal` / `db.sqlite3-shm` s'ils sont présents à côté).
