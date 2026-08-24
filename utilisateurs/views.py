from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect

from .models import DroitRole, Fonctionnalite, Utilisateur
from .permissions import page_accueil_pour


def connexion_view(request):
    error = None
    if request.method == 'POST':
        nom_util = request.POST.get('username')
        mot_passe = request.POST.get('password')

        # Django vérifie si l'utilisateur existe et si le mot de passe est bon
        user = authenticate(request, username=nom_util, password=mot_passe)

        if user is not None:
            login(request, user)
            # Certains rôles n'ont pas accès au Tableau de bord (voir
            # utilisateurs/permissions.py) : on les envoie directement vers
            # une page à laquelle ils ont accès, pour éviter un
            # aller-retour inutile.
            return redirect(page_accueil_pour(user))
        else:
            error = "Identifiant ou mot de passe incorrect."

    return render(request, 'utilisateurs/login.html', {'error': error})


def deconnexion_view(request):
    logout(request)
    return redirect('connexion')


@login_required
def gestion_droits(request):
    """Page d'administration des droits (onglet visible uniquement pour
    Admin/superutilisateur, voir base.html) : tableau à cases à cocher
    Fonctionnalité x rôle, qui pilote necessite_droit (voir permissions.py)
    et l'affichage du menu (context processor droits_utilisateur).

    Accès volontairement vérifié ici en dur (role == 'admin' ou
    is_superuser) plutôt que via necessite_droit : cette page contrôle les
    droits de toutes les autres fonctionnalités, elle ne doit jamais pouvoir
    être elle-même ouverte via la matrice qu'elle édite (un rôle pourrait
    sinon s'auto-accorder tous les droits)."""
    if not (request.user.is_superuser or request.user.role == 'admin'):
        messages.error(request, "Accès refusé : la gestion des droits est réservée aux administrateurs.")
        return redirect(page_accueil_pour(request.user))

    roles = Utilisateur.CHOIX_ROLES

    if request.method == 'POST':
        for fonctionnalite in Fonctionnalite.objects.all():
            for role_code, _ in roles:
                autorise = f"droit_{fonctionnalite.id}_{role_code}" in request.POST
                DroitRole.objects.update_or_create(
                    fonctionnalite=fonctionnalite,
                    role=role_code,
                    defaults={'autorise': autorise},
                )
        messages.success(request, "Droits mis à jour.")
        return redirect('gestion_droits')

    categories = {}
    for fonctionnalite in Fonctionnalite.objects.prefetch_related('droits'):
        autorisations = {droit.role: droit.autorise for droit in fonctionnalite.droits.all()}
        lignes_role = [(role_code, role_nom, autorisations.get(role_code, False)) for role_code, role_nom in roles]
        categories.setdefault(fonctionnalite.categorie, []).append((fonctionnalite, lignes_role))

    context = {
        'roles': roles,
        'categories': categories,
    }
    return render(request, 'utilisateurs/gestion_droits.html', context)


@login_required
def acces_refuse(request):
    """Page de secours absolue, jamais protégée par necessite_droit : sert
    de dernier recours à page_accueil_pour (voir permissions.py) pour
    garantir qu'aucune configuration de la matrice des droits ne puisse
    provoquer de boucle de redirection."""
    return render(request, 'utilisateurs/acces_refuse.html')
