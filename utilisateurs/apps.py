from django.apps import AppConfig


class UtilisateursConfig(AppConfig):
    name = 'utilisateurs'

    def ready(self):
        # Invalide le cache de la matrice des droits (voir permissions.py) à
        # chaque modification, pour qu'un changement fait depuis la page
        # d'administration des droits soit pris en compte immédiatement.
        from django.db.models.signals import post_delete, post_save

        from .models import DroitRole
        from .permissions import _invalider_cache_droits

        post_save.connect(_invalider_cache_droits, sender=DroitRole, dispatch_uid='invalider_cache_droits_save')
        post_delete.connect(_invalider_cache_droits, sender=DroitRole, dispatch_uid='invalider_cache_droits_delete')
