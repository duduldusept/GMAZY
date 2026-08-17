from datetime import date

from django.db import models

class Zone(models.Model):
    nom = models.CharField(max_length=100, verbose_name="Nom de la zone")
    description = models.TextField(blank=True, null=True, verbose_name="Description de la zone")

    class Meta:
        verbose_name = "Zone"
        verbose_name_plural = "Zones"

    def __str__(self):
        return self.nom


class Machine(models.Model):
    STATUT_CHOICES = [
        ('fonctionne', 'En marche / Opérationnel'),
        ('panne', 'En panne / Arrêt'),
        ('maintenance', 'En cours de maintenance'),
    ]

    nom = models.CharField(max_length=100, verbose_name="Nom de la machine")
    code_interne = models.CharField(max_length=50, unique=True, verbose_name="Code interne")
    zone = models.ForeignKey(Zone, on_delete=models.SET_NULL, null=True, blank=True, related_name='machines', verbose_name="Zone / Secteur")
    emplacement = models.CharField(max_length=100, verbose_name="Emplacement précis")
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='fonctionne')

    def __str__(self):
        return f"{self.code_interne} - {self.nom}"


class PieceDetachee(models.Model):
    nom = models.CharField(max_length=150, verbose_name="Nom de la pièce")
    reference = models.CharField(max_length=100, unique=True, verbose_name="Référence constructeur / interne")
    description = models.TextField(blank=True, null=True, verbose_name="Description / Caractéristiques")
    quantite_stock = models.PositiveIntegerField(default=0, verbose_name="Quantité en stock")
    stock_minimum = models.PositiveIntegerField(default=1, verbose_name="Alerte stock minimum")
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Prix unitaire (€)")

    machine_compatible = models.ForeignKey(
        Machine,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pieces_detachees',
        verbose_name="Machine compatible (optionnel)"
    )

    class Meta:
        verbose_name = "Pièce"
        verbose_name_plural = "Pièces"

    def __str__(self):
        return f"[{self.reference}] {self.nom}"

    def en_alerte_stock(self):
        return self.quantite_stock <= self.stock_minimum
    en_alerte_stock.boolean = True
    en_alerte_stock.short_description = "Alerte Stock ?"


class Section(models.Model):
    """Section budgétaire (Consommable, Entretien, Travaux Neuf...). Permet
    de regrouper toutes les dépenses qui utilisent un budget afin d'avoir
    un historique par section (voir DepenseBudget ci-dessous), en plus du
    suivi par machine déjà existant sur la page Budget Machine.

    Le champ `code` (fixe, ex: 'consommable') sert dans les URLs
    (/machines/budget/<code>/) et n'est pas modifiable par l'utilisateur
    final ; `nom` est le libellé affiché, modifiable depuis l'admin."""
    code = models.SlugField(max_length=30, unique=True, verbose_name="Code (technique)")
    nom = models.CharField(max_length=100, unique=True, verbose_name="Nom de la section")
    description = models.TextField(blank=True, null=True, verbose_name="Description")

    class Meta:
        verbose_name = "Section budgétaire"
        verbose_name_plural = "Sections budgétaires"
        ordering = ['nom']

    def __str__(self):
        return self.nom


class DepenseBudget(models.Model):
    """Une dépense rattachée à une Section budgétaire, permettant de
    constituer un historique par section (Consommable, Entretien, Travaux
    Neuf...). La machine est optionnelle : certaines dépenses (ex. Travaux
    Neuf) ne concernent pas forcément un équipement précis."""
    section = models.ForeignKey(Section, on_delete=models.PROTECT, related_name='depenses', verbose_name="Section")
    machine = models.ForeignKey(
        Machine,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='depenses_budget',
        verbose_name="Machine concernée (optionnel)",
    )
    titre = models.CharField(max_length=150, verbose_name="Intitulé de la dépense")
    description = models.TextField(blank=True, null=True, verbose_name="Description")
    montant = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Montant (€)")
    date_depense = models.DateField(default=date.today, verbose_name="Date de la dépense")
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Enregistrée le")

    class Meta:
        verbose_name = "Dépense budgétaire"
        verbose_name_plural = "Dépenses budgétaires"
        ordering = ['-date_depense']

    def __str__(self):
        return f"{self.titre} - {self.montant} € ({self.section.nom})"
