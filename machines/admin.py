from django.contrib import admin
from .models import Machine, Zone, PieceDetachee, Section, DepenseBudget

@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ['id', 'nom', 'description']
    search_fields = ['nom']

@admin.register(Machine)
class MachineAdmin(admin.ModelAdmin):
    list_display = ['code_interne', 'nom', 'zone', 'emplacement', 'statut']
    list_filter = ['statut', 'zone', 'emplacement']
    search_fields = ['nom', 'code_interne']

@admin.register(PieceDetachee)
class PieceDetacheeAdmin(admin.ModelAdmin):
    list_display = ['reference', 'nom', 'quantite_stock', 'stock_minimum', 'en_alerte_stock', 'prix_unitaire', 'machine_compatible']
    list_filter = ['machine_compatible']
    search_fields = ['nom', 'reference', 'description']
    list_editable = ['quantite_stock']

@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ['nom', 'code']
    search_fields = ['nom', 'code']

@admin.register(DepenseBudget)
class DepenseBudgetAdmin(admin.ModelAdmin):
    list_display = ['titre', 'section', 'machine', 'montant', 'date_depense']
    list_filter = ['section', 'machine']
    search_fields = ['titre', 'description']
    date_hierarchy = 'date_depense'
