from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser
from django.db import models

class Utilisateur(AbstractUser):
    # On définit les rôles possibles
    CHOIX_ROLES = [
        ('admin', 'Administrateur'),
        # Accès à toutes les pages de l'appli (comme Admin), mais sans accès
        # à l'administration Django (/admin/) : voir le lien "Gestion" dans
        # interventions/templates/interventions/base.html, conditionné à
        # role == 'admin' ou is_superuser (Responsable n'y correspond pas).
        ('responsable', 'Responsable'),
        ('chef_equipe', "Chef d'équipe"),
        ('technicien', 'Technicien de Maintenance'),
        ('production', 'Production / Opérateur'),
    ]

    role = models.CharField(
        max_length=20,
        choices=CHOIX_ROLES,
        default='production',
        verbose_name="Rôle au sein de l'entreprise"
    )

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class Fonctionnalite(models.Model):
    """Une page ou action de l'appli dont l'accès par rôle est configurable
    depuis la page d'administration des droits (utilisateurs.views.gestion_droits),
    plutôt que codé en dur dans les vues (voir utilisateurs/permissions.py)."""
    code = models.SlugField(max_length=50, unique=True, verbose_name="Code (technique)")
    nom = models.CharField(max_length=100, verbose_name="Nom affiché")
    categorie = models.CharField(max_length=50, verbose_name="Catégorie (regroupement dans le tableau)")
    ordre = models.PositiveIntegerField(default=0, verbose_name="Ordre d'affichage")

    class Meta:
        verbose_name = "Fonctionnalité"
        verbose_name_plural = "Fonctionnalités"
        ordering = ['ordre', 'nom']

    def __str__(self):
        return self.nom


class DroitRole(models.Model):
    """Indique si le rôle `role` a accès à la fonctionnalité `fonctionnalite`.
    Une ligne manquante pour une paire (fonctionnalite, role) équivaut à
    "non autorisé" (voir utilisateurs.permissions.a_le_droit)."""
    fonctionnalite = models.ForeignKey(Fonctionnalite, on_delete=models.CASCADE, related_name='droits')
    role = models.CharField(max_length=20, choices=Utilisateur.CHOIX_ROLES, verbose_name="Rôle")
    autorise = models.BooleanField(default=False, verbose_name="Autorisé ?")

    class Meta:
        verbose_name = "Droit par rôle"
        verbose_name_plural = "Droits par rôle"
        constraints = [
            models.UniqueConstraint(fields=['fonctionnalite', 'role'], name='unique_fonctionnalite_role'),
        ]

    def __str__(self):
        return f"{self.fonctionnalite.nom} - {self.get_role_display()} : {'Oui' if self.autorise else 'Non'}"

