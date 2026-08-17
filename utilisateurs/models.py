from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser
from django.db import models

class Utilisateur(AbstractUser):
    # On définit les rôles possibles
    CHOIX_ROLES = [
        ('admin', 'Administrateur / Responsable'),
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

