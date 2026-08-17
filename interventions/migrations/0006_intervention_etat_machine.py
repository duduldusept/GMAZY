# Ajoute le menu déroulant "État de la machine" (arrêtée / mode dégradé)
# sur la déclaration de panne. Seul l'état 'arretee' est comptabilisé dans
# le temps d'arrêt affiché sur la page Analyse des Temps d'Arrêt.
#
# Les interventions déjà existantes reçoivent la valeur par défaut
# 'arretee', ce qui conserve leur comportement actuel (elles étaient déjà
# comptées dans le temps d'arrêt avant l'ajout de ce champ).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('interventions', '0005_restore_can_close_intervention_permission'),
    ]

    operations = [
        migrations.AddField(
            model_name='intervention',
            name='etat_machine',
            field=models.CharField(
                choices=[('arretee', 'Machine arrêtée'), ('degradee', 'Machine fonctionne en mode dégradé')],
                default='arretee',
                max_length=20,
                verbose_name='État de la machine',
            ),
        ),
    ]
