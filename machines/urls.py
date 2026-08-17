from django.urls import path
from . import views

urlpatterns = [
    path('stock-pieces/', views.stock_pieces, name='stock_pieces'),
    path('stock-pieces/<int:id_piece>/ajuster/', views.ajuster_stock, name='ajuster_stock_piece'),
    path('stock-pieces/ajouter/', views.ajouter_piece, name='ajouter_piece'),
    path('stock-pieces/<int:id_piece>/supprimer/', views.supprimer_piece, name='supprimer_piece'),
    path('budget-machine/', views.budget_machine, name='budget_machine'),
    path('budget/<slug:code>/', views.budget_section, name='budget_section'),
    path('parc/', views.parc_machines, name='parc_machines'),
    path('parc/ajouter/', views.ajouter_machine, name='ajouter_machine'),
    path('parc/<int:id_machine>/supprimer/', views.supprimer_machine, name='supprimer_machine'),
]
