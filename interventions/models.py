from django.db import models
from django.conf import settings
from django.db.models import F
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.utils import timezone
from machines.models import Machine, PieceDetachee  # On importe Machine et PieceDetachee

class Intervention(models.Model):
    STATUT_CHOICES = [
        ('a_faire', 'À faire / En attente'),
        ('en_cours', 'En cours de réparation'),
        ('resolu', 'Résolu / Clôturé'),
    ]

    TYPE_CHOICES = [
        ('correctif', 'Correctif (Panne)'),
        ('preventif', 'Préventif (Entretien)'),
    ]

    # Choix affiché en menu déroulant sur le formulaire "Déclarer une panne".
    # Seul l'état 'arretee' est comptabilisé dans le temps d'arrêt de la page
    # Analyse des Temps d'Arrêt (voir statistiques_machines dans views.py) :
    # une machine en mode dégradé continue de fonctionner, elle ne génère
    # donc pas de temps d'arrêt à proprement parler. 'planifiee' est réservé
    # aux interventions de maintenance préventive programmées depuis le
    # calendrier : la machine ne s'arrête pas, elle n'est donc jamais
    # comptabilisée dans le temps d'arrêt (ni 'arretee' ni 'degradee').
    ETAT_MACHINE_CHOICES = [
        ('arretee', 'Machine arrêtée'),
        ('degradee', 'Machine fonctionne en mode dégradé'),
        ('planifiee', 'Maintenance planifiée (aucun arrêt)'),
    ]

    titre = models.CharField(max_length=100, verbose_name="Problème constaté")
    description = models.TextField(verbose_name="Description détaillée")
    type_intervention = models.CharField(max_length=20, choices=TYPE_CHOICES, default='correctif')
    etat_machine = models.CharField(
        max_length=20,
        choices=ETAT_MACHINE_CHOICES,
        default='arretee',
        verbose_name="État de la machine",
    )
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='a_faire')

    machine = models.ForeignKey(Machine, on_delete=models.CASCADE, related_name='interventions', verbose_name="Machine")
    technicien = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Technicien en charge")

    # --- NOUVEAUX CHAMPS AJOUTÉS ---
    compte_rendu = models.TextField(blank=True, null=True, verbose_name="Compte-rendu de l'intervention")
    date_creation = models.DateTimeField(default=timezone.now, verbose_name="Date de signalement")
    date_resolution = models.DateTimeField(blank=True, null=True, verbose_name="Date de clôture")

    # Date planifiée pour une intervention de maintenance préventive,
    # utilisée par le calendrier de l'onglet Maintenance Préventive.
    # Vide pour les interventions curatives (déclarations de panne).
    date_prevue = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Date prévue",
        help_text="Date de planification pour une intervention de maintenance préventive.",
    )

    # Relation vers les pièces via la table de liaison intermédiaire définie plus bas
    pieces_utilisees = models.ManyToManyField(
        PieceDetachee,
        through='InterventionPiece',
        blank=True,
        verbose_name="Pièces utilisées"
    )

    class Meta:
        verbose_name = "Intervention"
        verbose_name_plural = "Interventions"
        # BUGFIX : cette permission avait été supprimée par erreur lors d'une
        # migration précédente (AlterModelOptions qui écrasait tout le dict
        # d'options). Elle est utilisée dans interventions/views.py
        # (changer_statut) pour autoriser la clôture d'une intervention.
        permissions = [
            ('can_close_intervention', 'Peut clôturer une intervention'),
        ]

    def __str__(self):
        return f"Int #{self.id} - {self.titre} ({self.get_statut_display()})"

    def duree_arret_heures(self):
        """
        Retourne la durée d'arrêt en heures (float) entre l'envoi de la
        demande d'intervention (date_creation, clic sur "Envoyer la demande
        d'intervention") et sa résolution (date_resolution, clic sur
        "Marquer comme Résolu").

        Le compteur démarre donc dès la création de l'intervention. Tant
        qu'elle n'est pas encore résolue, date_resolution est vide : on
        calcule alors la durée jusqu'à l'instant présent, ce qui fait que
        le total augmente à chaque affichage de la page Analyse des Temps
        d'Arrêt pour une panne toujours en cours. Il ne s'arrête réellement
        que lorsque l'intervention est clôturée.
        """
        fin = self.date_resolution or timezone.now()
        delta = fin - self.date_creation
        return delta.total_seconds() / 3600


class DemandeAmelioration(models.Model):
    """Une demande d'amélioration (onglet Amélioration, sous Déclarer une
    panne) : contrairement à une Intervention, il ne s'agit pas d'une
    panne à réparer mais d'une suggestion à étudier, sur une machine
    précise ou sur le Bâtiment / Services Généraux en général (machine
    laissée vide dans ce cas)."""
    STATUT_CHOICES = [
        ('nouvelle', 'Nouvelle demande'),
        ('en_etude', 'En étude'),
        ('acceptee', 'Acceptée'),
        ('refusee', 'Refusée'),
        ('realisee', 'Réalisée'),
    ]

    titre = models.CharField(max_length=150, verbose_name="Titre de la demande")
    description = models.TextField(verbose_name="Description de l'amélioration souhaitée")
    machine = models.ForeignKey(
        Machine,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='demandes_amelioration',
        verbose_name="Machine concernée",
        help_text="Laisser vide si la demande concerne le Bâtiment / les Services Généraux plutôt qu'une machine précise.",
    )
    demandeur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='demandes_amelioration',
        verbose_name="Demandeur",
    )
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='nouvelle')
    date_creation = models.DateTimeField(default=timezone.now, verbose_name="Date de la demande")

    class Meta:
        verbose_name = "Demande d'amélioration"
        verbose_name_plural = "Demandes d'amélioration"
        ordering = ['-date_creation']

    def __str__(self):
        cible = self.machine.code_interne if self.machine else "Bâtiment / Services Généraux"
        return f"{self.titre} - {cible} ({self.get_statut_display()})"


# --- NOUVEAU MODÈLE INTERMÉDIAIRE POUR ASSOCIER PIÈCE ET QUANTITÉ ---
class InterventionPiece(models.Model):
    intervention = models.ForeignKey(Intervention, on_delete=models.CASCADE)
    piece = models.ForeignKey(PieceDetachee, on_delete=models.CASCADE, verbose_name="Pièce")
    quantite_utilisee = models.PositiveIntegerField(default=1, verbose_name="Quantité utilisée")

    class Meta:
        verbose_name = "Pièce utilisée"
        verbose_name_plural = "Pièces utilisées"

    def __str__(self):
        return f"{self.quantite_utilisee}x {self.piece.nom}"

    # Logique automatique : On déduit la quantité du stock lorsque le technicien valide.
    #
    # BUGFIX : la version précédente ne touchait au stock qu'à la création
    # (`if not self.pk`), donc modifier la quantité d'une ligne déjà
    # enregistrée (ex: 2 -> 5 pièces via l'inline de l'admin) ne déduisait
    # jamais la différence du stock. On calcule maintenant un delta par
    # rapport à l'état précédent en base (et on gère aussi le cas, plus
    # rare, où on change la pièce elle-même sur une ligne existante).
    def save(self, *args, **kwargs):
        ancienne_piece_id = None
        ancienne_quantite = 0
        if self.pk:
            ancienne_piece_id, ancienne_quantite = InterventionPiece.objects.filter(
                pk=self.pk
            ).values_list('piece_id', 'quantite_utilisee').first()

        if ancienne_piece_id == self.piece_id:
            delta = self.quantite_utilisee - ancienne_quantite
            if delta > 0 and delta > self.piece.quantite_stock:
                raise ValueError(
                    f"Stock insuffisant pour « {self.piece.nom} » : "
                    f"{self.piece.quantite_stock} disponible(s), "
                    f"{delta} demandé(s) en plus."
                )
            if delta != 0:
                PieceDetachee.objects.filter(pk=self.piece_id).update(
                    quantite_stock=F('quantite_stock') - delta
                )
        else:
            if ancienne_piece_id is not None:
                # On restitue à l'ancienne pièce la quantité qui lui avait été retirée.
                PieceDetachee.objects.filter(pk=ancienne_piece_id).update(
                    quantite_stock=F('quantite_stock') + ancienne_quantite
                )
            if self.quantite_utilisee > self.piece.quantite_stock:
                raise ValueError(
                    f"Stock insuffisant pour « {self.piece.nom} » : "
                    f"{self.piece.quantite_stock} disponible(s), "
                    f"{self.quantite_utilisee} demandé(s)."
                )
            PieceDetachee.objects.filter(pk=self.piece_id).update(
                quantite_stock=F('quantite_stock') - self.quantite_utilisee
            )

        super().save(*args, **kwargs)


# BUGFIX : la restitution du stock vivait dans InterventionPiece.delete(),
# qui n'est jamais appelée quand la ligne est supprimée par cascade (ex:
# suppression de l'Intervention parente, ou de la Machine dont elle dépend,
# depuis l'admin Django) : Django supprime alors les lignes liées via une
# suppression en masse au niveau de la requête, sans passer par la méthode
# delete() de chaque instance. Un signal pre_delete, lui, est envoyé pour
# chaque ligne réellement supprimée même dans ce cas, ce qui couvre aussi
# bien la suppression directe que les suppressions en cascade.
@receiver(pre_delete, sender=InterventionPiece)
def restituer_stock_piece_utilisee(sender, instance, **kwargs):
    PieceDetachee.objects.filter(pk=instance.piece_id).update(
        quantite_stock=F('quantite_stock') + instance.quantite_utilisee
    )
