# Migration de correction : restaure la permission personnalisée
# 'can_close_intervention' qui avait été supprimée par erreur dans la
# migration 0004 (celle-ci a écrasé le dict d'options du Meta sans
# conserver la clé 'permissions' ajoutée en 0002).

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('interventions', '0004_alter_intervention_options_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='intervention',
            options={
                'verbose_name': 'Intervention',
                'verbose_name_plural': 'Interventions',
                'permissions': [('can_close_intervention', 'Peut clôturer une intervention')],
            },
        ),
    ]
