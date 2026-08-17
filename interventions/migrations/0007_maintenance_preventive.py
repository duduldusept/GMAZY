# Ajoute la prise en charge de la planification de maintenance préventive
# (onglet Maintenance > Maintenance Préventive) :
#   - date_prevue : date/heure planifiée d'une intervention préventive,
#     affichée dans le calendrier.
#   - etat_machine : ajout du choix 'planifiee', utilisé pour les
#     interventions préventives programmées afin qu'elles ne soient jamais
#     comptabilisées dans le temps d'arrêt (page Analyse des Temps d'Arrêt,
#     qui ne somme que 'arretee' et 'degradee').
#
# Les interventions existantes reçoivent date_prevue = NULL (aucun impact
# sur leur comportement actuel).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('interventions', '0006_intervention_etat_machine'),
    ]

    operations = [
        migrations.AddField(
            model_name='intervention',
            name='date_prevue',
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text="Date de planification pour une intervention de maintenance préventive.",
                verbose_name='Date prévue',
            ),
        ),
        migrations.AlterField(
            model_name='intervention',
            name='etat_machine',
            field=models.CharField(
                choices=[
                    ('arretee', 'Machine arrêtée'),
                    ('degradee', 'Machine fonctionne en mode dégradé'),
                    ('planifiee', 'Maintenance planifiée (aucun arrêt)'),
                ],
                default='arretee',
                max_length=20,
                verbose_name='État de la machine',
            ),
        ),
    ]
