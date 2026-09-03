from django.contrib import admin
from django.utils import timezone
from .models import Intervention, InterventionPiece, DemandeAmelioration

# Permet d'ajouter les pièces sous forme de lignes directement dans l'intervention
class InterventionPieceInline(admin.TabularInline):
    model = InterventionPiece
    extra = 1  # Affiche une ligne vide par défaut pour ajouter une pièce


# Actions de liste : permettent de rouvrir en masse une intervention déjà
# clôturée (ou de la faire avancer) sans avoir à ouvrir sa fiche détaillée.
# date_resolution est effacée quand on repasse à un statut non terminé, et
# reposée à l'instant présent quand on la marque résolue depuis l'action.
@admin.action(description="Repasser en « À faire / En attente »")
def repasser_a_faire(modeladmin, request, queryset):
    queryset.update(statut='a_faire', date_resolution=None)


@admin.action(description="Repasser en « En cours de réparation »")
def repasser_en_cours(modeladmin, request, queryset):
    queryset.update(statut='en_cours', date_resolution=None)


@admin.action(description="Marquer comme « Résolu / Clôturé »")
def marquer_resolu(modeladmin, request, queryset):
    queryset.update(statut='resolu', date_resolution=timezone.now())


@admin.register(Intervention)
class InterventionAdmin(admin.ModelAdmin):
    list_display = ['id', 'titre', 'machine', 'type_intervention', 'etat_machine', 'technicien', 'statut', 'date_prevue', 'date_creation', 'date_resolution']
    list_filter = ['statut', 'type_intervention', 'etat_machine', 'machine']
    search_fields = ['titre', 'description', 'compte_rendu']
    actions = [repasser_a_faire, repasser_en_cours, marquer_resolu]

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
    list_display = ['id', 'titre', 'machine', 'demandeur', 'statut', 'date_creation', 'date_cloture']
    list_filter = ['statut', 'machine']
    search_fields = ['titre', 'description']
