from django.urls import path
from . import views

urlpatterns = [
    path('connexion/', views.connexion_view, name='connexion'),
    path('deconnexion/', views.deconnexion_view, name='deconnexion'),
    path('droits/', views.gestion_droits, name='gestion_droits'),
    path('acces-refuse/', views.acces_refuse, name='acces_refuse'),
]