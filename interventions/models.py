from django.db import models
from django.conf import settings
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

    # Logique automatique : On déduit la quantité du stock lorsque le technicien valide
    def save(self, *args, **kwargs):
        if not self.pk:  # Seulement lors de la création initiale du lien
            # BUGFIX : on vérifie maintenant qu'il y a assez de stock avant
            # de décrémenter, pour éviter un stock négatif silencieux.
            if self.quantite_utilisee > self.piece.quantite_stock:
                raise ValueError(
                    f"Stock insuffisant pour « {self.piece.nom} » : "
                    f"{self.piece.quantite_stock} disponible(s), "
                    f"{self.quantite_utilisee} demandé(s)."
                )
            self.piece.quantite_stock -= self.quantite_utilisee
            self.piece.save()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # BUGFIX : le stock n'était jamais restitué quand une pièce liée à
        # une intervention était supprimée. On le remet maintenant.
        self.piece.quantite_stock += self.quantite_utilisee
        self.piece.save()
        super().delete(*args, **kwargs)
