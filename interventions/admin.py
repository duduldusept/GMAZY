from django.contrib import admin
from .models import Intervention, InterventionPiece, DemandeAmelioration

# Permet d'ajouter les pièces sous forme de lignes directement dans l'intervention
class InterventionPieceInline(admin.TabularInline):
    model = InterventionPiece
    extra = 1  # Affiche une ligne vide par défaut pour ajouter une pièce

@admin.register(Intervention)
class InterventionAdmin(admin.ModelAdmin):
    list_display = ['id', 'titre', 'machine', 'type_intervention', 'etat_machine', 'technicien', 'statut', 'date_prevue', 'date_creation', 'date_resolution']
    list_filter = ['statut', 'type_intervention', 'etat_machine', 'machine']
    search_fields = ['titre', 'description', 'compte_rendu']

    # On ajoute les lignes de pièces et on organise les formulaires
    inlines = [InterventionPieceInline]

    fieldsets = (
        ('Informations Générales', {
            'fields': ('titre', 'machine', 'etat_machine', 'description', 'type_intervention', 'statut', 'technicien')
        }),
        ('Planification (Maintenance Préventive)', {
            'fields': ('date_prevue',),
        }),
        ('Suivi & Historique (Visible par tous)', {
            'fields': ('compte_rendu', 'date_resolution'),
        }),
    )


@admin.register(DemandeAmelioration)
class DemandeAmeliorationAdmin(admin.ModelAdmin):
    list_display = ['id', 'titre', 'machine', 'demandeur', 'statut', 'date_creation']
    list_filter = ['statut', 'machine']
    search_fields = ['titre', 'description']
