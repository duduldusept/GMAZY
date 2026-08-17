from django.urls import path
from . import views

urlpatterns = [
    path('', views.liste_interventions, name='liste_interventions'),  # Page d'accueil du site
    path('declarer-panne/', views.declarer_panne, name='declarer_panne'),
    path('interventions/<int:id_intervention>/statut/', views.changer_statut, name='changer_statut'),
    path('statistiques/', views.statistiques_machines, name='statistiques'),

    # Onglet Amélioration
    path('amelioration/', views.amelioration, name='amelioration'),
    path('amelioration/<int:id_demande>/statut/', views.changer_statut_amelioration, name='changer_statut_amelioration'),

    # Onglet Maintenance
    path('maintenance/preventive/', views.maintenance_preventive, name='maintenance_preventive'),
    path('maintenance/preventive/evenements/', views.evenements_preventifs, name='evenements_preventifs'),
    path('maintenance/curative/', views.maintenance_curative, name='maintenance_curative'),
    path('maintenance/analyse/', views.maintenance_analyse, name='maintenance_analyse'),

    # Onglet Service Généraux
    path('service-generaux/batiment/', views.service_generaux_batiment, name='service_generaux_batiment'),
    path('service-generaux/batiment/preventif/', views.service_generaux_preventif, name='service_generaux_preventif'),
    path('service-generaux/batiment/preventif/evenements/', views.evenements_preventifs_batiment, name='evenements_preventifs_batiment'),
]
