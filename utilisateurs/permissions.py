from functools import wraps

from django.contrib import messages
from django.core.cache import cache
from django.shortcuts import redirect

CACHE_KEY_MATRICE = 'utilisateurs_matrice_droits'

# Candidats (code de Fonctionnalite -> nom d'URL) essayés dans l'ordre pour
# rediriger un utilisateur qui n'a pas accès à la page qu'il visait (voir
# necessite_droit ci-dessous), ou juste après connexion. On ne renvoie
# jamais vers une page à laquelle l'utilisateur n'a lui-même pas accès :
# depuis que les droits sont éditables par l'admin (voir gestion_droits),
# rediriger en dur vers une page fixe par rôle pourrait produire une boucle
# de redirection si l'admin retire l'accès à cette page précise pour ce
# rôle. 'acces_refuse' (dernier recours) n'est protégé par aucun droit :
# il ne peut donc jamais boucler.
CANDIDATS_PAGE_ACCUEIL = [
    ('tableau_de_bord', 'liste_interventions'),
    ('declarer_panne', 'declarer_panne'),
    ('amelioration', 'amelioration'),
    ('maintenance_curative', 'maintenance_curative'),
]


def _charger_matrice_droits():
    """Charge {role: {codes de Fonctionnalite autorisés}}, mise en cache
    (invalidée automatiquement à chaque modification de DroitRole, voir plus
    bas) pour éviter de re-requêter la base à chaque contrôle d'accès."""
    matrice = cache.get(CACHE_KEY_MATRICE)
    if matrice is None:
        from .models import DroitRole

        matrice = {}
        for role, code in DroitRole.objects.filter(autorise=True).values_list('role', 'fonctionnalite__code'):
            matrice.setdefault(role, set()).add(code)
        cache.set(CACHE_KEY_MATRICE, matrice, None)
    return matrice


def _invalider_cache_droits(sender, **kwargs):
    # Connecté aux signaux post_save/post_delete de DroitRole depuis
    # UtilisateursConfig.ready() (voir apps.py).
    cache.delete(CACHE_KEY_MATRICE)


def a_le_droit(user, code):
    """True si `user` a le droit `code` (voir Fonctionnalite.code). Un
    superutilisateur a toujours tous les droits, même en l'absence de ligne
    DroitRole correspondante (garde-fou : jamais bloqué par une mauvaise
    configuration de la matrice)."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    role = getattr(user, 'role', None)
    return code in _charger_matrice_droits().get(role, set())


def codes_autorises_pour(user):
    """Ensemble des codes de Fonctionnalite accessibles à `user`, utilisé
    par le context processor ci-dessous pour piloter l'affichage du menu
    (voir base.html) sans dupliquer la logique de a_le_droit."""
    if not user or not user.is_authenticated:
        return set()
    if user.is_superuser:
        from .models import Fonctionnalite
        return set(Fonctionnalite.objects.values_list('code', flat=True))
    role = getattr(user, 'role', None)
    return set(_charger_matrice_droits().get(role, set()))


def droits_utilisateur(request):
    """Context processor (voir TEMPLATES dans settings.py) : expose
    `droits_utilisateur`, l'ensemble des codes accessibles à l'utilisateur
    connecté, à tous les templates."""
    return {'droits_utilisateur': codes_autorises_pour(getattr(request, 'user', None))}


def page_accueil_pour(user):
    """Renvoie le nom d'URL de la première page, parmi CANDIDATS_PAGE_ACCUEIL,
    à laquelle `user` a effectivement accès. 'acces_refuse' (sans aucune
    restriction de droit) sert de dernier recours absolu."""
    for code, nom_url in CANDIDATS_PAGE_ACCUEIL:
        if a_le_droit(user, code):
            return nom_url
    return 'acces_refuse'


def necessite_droit(code):
    """Décorateur de vue : n'autorise l'accès qu'aux utilisateurs ayant le
    droit `code` (voir Fonctionnalite/DroitRole et la page d'administration
    utilisateurs.views.gestion_droits). Les autres sont redirigés vers une
    page à laquelle ils ont accès (voir page_accueil_pour) avec un message
    d'explication, plutôt que de tomber sur une erreur 403 brute.

    À utiliser en plus de @login_required (en dessous), pas à sa place :
        @login_required
        @necessite_droit('stock_pieces')
        def ma_vue(request):
            ...
    """
    def decorateur(vue):
        @wraps(vue)
        def wrapper(request, *args, **kwargs):
            if not a_le_droit(request.user, code):
                messages.error(request, "Accès refusé : cette page n'est pas disponible pour ton rôle.")
                return redirect(page_accueil_pour(request.user))
            return vue(request, *args, **kwargs)
        return wrapper
    return decorateur
