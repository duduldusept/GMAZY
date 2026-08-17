from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('utilisateurs', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='utilisateur',
            name='role',
            field=models.CharField(
                choices=[
                    ('admin', 'Administrateur / Responsable'),
                    ('chef_equipe', "Chef d'équipe"),
                    ('technicien', 'Technicien de Maintenance'),
                    ('production', 'Production / Opérateur'),
                ],
                default='production',
                max_length=20,
                verbose_name="Rôle au sein de l'entreprise",
            ),
        ),
    ]
