# Ajoute le suivi budgétaire par Section (onglet Budget > Consommable /
# Entretien / Travaux Neuf) :
#   - Section : catégorie budgétaire (code technique + nom affiché).
#   - DepenseBudget : une dépense rattachée à une Section, avec une machine
#     optionnelle, permettant un historique par section indépendant du
#     suivi par machine déjà existant (page Budget Machine).
#
# Les 3 sections initiales (Consommable, Entretien, Travaux Neuf) sont
# créées automatiquement via une migration de données (RunPython) pour que
# les 3 sous-onglets fonctionnent dès le premier lancement, sans passer par
# l'admin.

import datetime
from django.db import migrations, models
import django.db.models.deletion


def creer_sections_par_defaut(apps, schema_editor):
    Section = apps.get_model('machines', 'Section')
    sections = [
        ('consommable', 'Consommable'),
        ('entretien', 'Entretien'),
        ('travaux_neuf', 'Travaux Neuf'),
    ]
    for code, nom in sections:
        Section.objects.get_or_create(code=code, defaults={'nom': nom})


def supprimer_sections_par_defaut(apps, schema_editor):
    Section = apps.get_model('machines', 'Section')
    Section.objects.filter(code__in=['consommable', 'entretien', 'travaux_neuf']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('machines', '0003_piecedetachee'),
    ]

    operations = [
        migrations.CreateModel(
            name='Section',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.SlugField(max_length=30, unique=True, verbose_name='Code (technique)')),
                ('nom', models.CharField(max_length=100, unique=True, verbose_name='Nom de la section')),
                ('description', models.TextField(blank=True, null=True, verbose_name='Description')),
            ],
            options={
                'verbose_name': 'Section budgétaire',
                'verbose_name_plural': 'Sections budgétaires',
                'ordering': ['nom'],
            },
        ),
        migrations.CreateModel(
            name='DepenseBudget',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titre', models.CharField(max_length=150, verbose_name='Intitulé de la dépense')),
                ('description', models.TextField(blank=True, null=True, verbose_name='Description')),
                ('montant', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Montant (€)')),
                ('date_depense', models.DateField(default=datetime.date.today, verbose_name='Date de la dépense')),
                ('date_creation', models.DateTimeField(auto_now_add=True, verbose_name='Enregistrée le')),
                ('machine', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='depenses_budget', to='machines.machine', verbose_name='Machine concernée (optionnel)')),
                ('section', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='depenses', to='machines.section', verbose_name='Section')),
            ],
            options={
                'verbose_name': 'Dépense budgétaire',
                'verbose_name_plural': 'Dépenses budgétaires',
                'ordering': ['-date_depense'],
            },
        ),
        migrations.RunPython(creer_sections_par_defaut, supprimer_sections_par_defaut),
    ]
