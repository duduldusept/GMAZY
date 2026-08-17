from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Utilisateur

@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    # On indique à Django comment afficher notre champ "role" dans les formulaires
    fieldsets = UserAdmin.fieldsets + (
        ('Informations Entreprise', {'fields': ('role',)}),
    )
    # Les colonnes qui vont s'afficher dans la liste des utilisateurs
    list_display = ['username', 'email', 'role', 'is_staff', 'is_superuser']
    list_filter = ['role', 'is_staff']