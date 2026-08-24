from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Utilisateur, Fonctionnalite, DroitRole

@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    # On indique à Django comment afficher notre champ "role" dans les formulaires
    fieldsets = UserAdmin.fieldsets + (
        ('Informations Entreprise', {'fields': ('role',)}),
    )
    # Les colonnes qui vont s'afficher dans la liste des utilisateurs
    list_display = ['username', 'email', 'role', 'is_staff', 'is_superuser']
    list_filter = ['role', 'is_staff']


class DroitRoleInline(admin.TabularInline):
    model = DroitRole
    extra = 0

@admin.register(Fonctionnalite)
class FonctionnaliteAdmin(admin.ModelAdmin):
    # La page dédiée (utilisateurs.views.gestion_droits, menu > Gestion des
    # droits) reste l'outil principal pour éditer les droits au quotidien ;
    # cet écran admin sert surtout à ajouter/retirer des Fonctionnalite elles-mêmes.
    list_display = ['nom', 'code', 'categorie', 'ordre']
    list_filter = ['categorie']
    inlines = [DroitRoleInline]