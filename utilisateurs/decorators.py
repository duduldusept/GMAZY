from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

# Page vers laquelle renvoyer un utilisateur quand la page qu'il visait lui
# est refusée (ou juste après connexion). Certains rôles restreints n'ont
# même pas accès à 'declarer_panne' (le secours "par défaut"), on leur
# indique alors une autre page à laquelle ils ont accès. Rôle absent de ce
# dictionnaire (admin, technicien, ...) => aucune restriction, secours sur
# le tableau de bord.
PAGE_ACCUEIL_PAR_ROLE = {
    'chef_equipe': 'declarer_panne',
    'production': 'amelioration',
}


def page_accueil_pour(user):
    """Renvoie le nom d'URL de la page d'accueil/de secours adaptée au rôle
    de `user` (voir PAGE_ACCUEIL_PAR_ROLE)."""
    role = getattr(user, 'role', None)
    return PAGE_ACCUEIL_PAR_ROLE.get(role, 'liste_interventions')


def bloquer_pour_role(*roles_bloques):
    """Décorateur de vue : interdit l'accès à cette page aux utilisateurs
    dont le rôle (Utilisateur.role) fait partie de `roles_bloques`.

    Ils sont redirigés vers une page à laquelle ils ont accès (voir
    page_accueil_pour) avec un message d'explication, plutôt que de tomber
    sur une erreur 403 brute. Un administrateur ou un superutilisateur n'est
    jamais bloqué, même si son rôle figure dans la liste.

    À utiliser en plus de @login_required (en dessous), pas à sa place :
        @login_required
        @bloquer_pour_role('chef_equipe', 'production')
        def ma_vue(request):
            ...
    """
    def decorateur(vue):
        @wraps(vue)
        def wrapper(request, *args, **kwargs):
            role = getattr(request.user, 'role', None)
            est_protege = (
                request.user.is_authenticated
                and not request.user.is_superuser
                and role in roles_bloques
            )
            if est_protege:
                messages.error(request, "Accès refusé : cette page n'est pas disponible pour ton rôle.")
                return redirect(page_accueil_pour(request.user))
            return vue(request, *args, **kwargs)
        return wrapper
    return decorateur
