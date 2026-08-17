from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from .decorators import page_accueil_pour

def connexion_view(request):
    error = None
    if request.method == 'POST':
        nom_util = request.POST.get('username')
        mot_passe = request.POST.get('password')

        # Django vérifie si l'utilisateur existe et si le mot de passe est bon
        user = authenticate(request, username=nom_util, password=mot_passe)

        if user is not None:
            login(request, user)
            # Certains rôles (Chef d'équipe, Production/Opérateur) n'ont pas
            # accès au Tableau de bord (voir utilisateurs/decorators.py) : on
            # les envoie directement vers une page à laquelle ils ont accès,
            # pour éviter un aller-retour inutile.
            return redirect(page_accueil_pour(user))
        else:
            error = "Identifiant ou mot de passe incorrect."

    return render(request, 'utilisateurs/login.html', {'error': error})

def deconnexion_view(request):
    logout(request)
    return redirect('connexion')
