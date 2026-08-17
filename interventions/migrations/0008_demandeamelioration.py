# Ajoute l'onglet Amélioration (sous "Déclarer une panne") : permet de
# soumettre une demande d'amélioration sur une machine précise ou sur le
# Bâtiment / Services Généraux (machine laissée vide dans ce cas), avec un
# historique des demandes et de leur statut (nouvelle / en étude /
# acceptée / refusée / réalisée).

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('machines', '0003_piecedetachee'),
        ('interventions', '0007_maintenance_preventive'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DemandeAmelioration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titre', models.CharField(max_length=150, verbose_name='Titre de la demande')),
                ('description', models.TextField(verbose_name="Description de l'amélioration souhaitée")),
                ('statut', models.CharField(choices=[('nouvelle', 'Nouvelle demande'), ('en_etude', 'En étude'), ('acceptee', 'Acceptée'), ('refusee', 'Refusée'), ('realisee', 'Réalisée')], default='nouvelle', max_length=20)),
                ('date_creation', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Date de la demande')),
                ('demandeur', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='demandes_amelioration', to=settings.AUTH_USER_MODEL, verbose_name='Demandeur')),
                ('machine', models.ForeignKey(blank=True, help_text="Laisser vide si la demande concerne le Bâtiment / les Services Généraux plutôt qu'une machine précise.", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='demandes_amelioration', to='machines.machine', verbose_name='Machine concernée')),
            ],
            options={
                'verbose_name': "Demande d'amélioration",
                'verbose_name_plural': "Demandes d'amélioration",
                'ordering': ['-date_creation'],
            },
        ),
    ]
