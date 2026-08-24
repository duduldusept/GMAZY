from datetime import date

from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver

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


class Contrat(models.Model):
    """Un contrat prestataire (onglet Budget > Contrats) : maintenance,
    assurance, location, etc. Le document (PDF ou image) est optionnel et
    n'est jamais servi via une URL publique (voir MEDIA_URL/MEDIA_ROOT dans
    settings.py) : il passe par la vue protégée
    machines.views.telecharger_contrat_document."""
    TYPE_CHOICES = [
        ('maintenance', 'Contrat de maintenance'),
        ('assurance', 'Assurance'),
        ('location', 'Location / Leasing'),
        ('prestation', 'Prestation de service'),
        ('autre', 'Autre'),
    ]

    prestataire = models.CharField(max_length=150, verbose_name="Nom du prestataire")
    type_contrat = models.CharField(max_length=20, choices=TYPE_CHOICES, default='autre', verbose_name="Type de contrat")
    prix = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Prix (€)")
    date_debut = models.DateField(verbose_name="Date de début")
    date_fin = models.DateField(
        blank=True,
        null=True,
        verbose_name="Date de fin",
        help_text="Laisser vide si le contrat est à durée indéterminée / reconduction tacite.",
    )
    description = models.TextField(blank=True, null=True, verbose_name="Description / Notes")
    document = models.FileField(
        upload_to='contrats/%Y/%m/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['pdf', 'jpg', 'jpeg', 'png', 'webp'])],
        verbose_name="Document (PDF ou image)",
    )
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Ajouté le")

    class Meta:
        verbose_name = "Contrat"
        verbose_name_plural = "Contrats"
        ordering = ['-date_debut']

    def __str__(self):
        return f"{self.prestataire} - {self.get_type_contrat_display()}"

    def duree_texte(self):
        """Durée lisible du contrat, calculée à partir de date_debut/date_fin
        plutôt que saisie à la main (évite qu'elle se désynchronise des
        dates réelles)."""
        if not self.date_fin:
            return "Durée indéterminée"

        jours = (self.date_fin - self.date_debut).days
        mois = round(jours / 30.44)

        if mois < 1:
            return f"{jours} jour{'s' if jours > 1 else ''}"

        annees, reste_mois = divmod(mois, 12)
        if annees and reste_mois:
            return f"{annees} an{'s' if annees > 1 else ''} {reste_mois} mois"
        elif annees:
            return f"{annees} an{'s' if annees > 1 else ''}"
        return f"{mois} mois"

    def est_expire(self):
        return bool(self.date_fin) and self.date_fin < date.today()
    est_expire.boolean = True
    est_expire.short_description = "Expiré ?"


@receiver(pre_delete, sender=Contrat)
def supprimer_document_contrat(sender, instance, **kwargs):
    # BUGFIX-anticipé : Django ne supprime jamais automatiquement le fichier
    # physique d'un FileField quand l'instance est supprimée (comportement
    # documenté), ce qui laisserait des fichiers orphelins sur le disque à
    # chaque suppression de contrat. On le supprime nous-mêmes ici.
    if instance.document:
        instance.document.delete(save=False)
