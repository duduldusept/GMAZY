from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from machines.models import Machine, PieceDetachee
from .models import Intervention, InterventionPiece

Utilisateur = get_user_model()


class ResolutionInterventionTests(TestCase):
    """Vérifie le nouveau flux de résolution (fenêtre modale du tableau de
    bord) : compte-rendu, déduction du stock de pièces, et horodatage
    (date_resolution) utilisé par l'Analyse des Temps d'Arrêt."""

    def setUp(self):
        self.utilisateur = Utilisateur.objects.create_superuser(
            username='admin_test', email='admin@test.local', password='motdepasse123',
        )
        self.client.force_login(self.utilisateur)

        self.machine = Machine.objects.create(
            nom="Presse 1", code_interne="P1", emplacement="Atelier",
        )
        self.piece = PieceDetachee.objects.create(
            nom="Roulement", reference="ROUL-01", quantite_stock=5,
        )

        # Intervention créée il y a 3h, pour obtenir un temps d'arrêt mesurable.
        self.intervention = Intervention.objects.create(
            titre="Bruit anormal",
            description="Bruit suspect au démarrage",
            machine=self.machine,
            statut='en_cours',
            etat_machine='arretee',
            date_creation=timezone.now() - timedelta(hours=3),
        )

    def test_resolution_avec_piece_deduit_le_stock_et_horodate(self):
        reponse = self.client.post(
            reverse('resoudre_intervention', args=[self.intervention.id]),
            {
                'pieces_utilisees': 'oui',
                'piece_id': [str(self.piece.id)],
                f'quantite_{self.piece.id}': '2',
                'compte_rendu': "Remplacement du roulement défectueux.",
            },
        )
        self.assertRedirects(reponse, reverse('liste_interventions'))

        self.intervention.refresh_from_db()
        self.piece.refresh_from_db()

        # Statut + compte-rendu enregistrés
        self.assertEqual(self.intervention.statut, 'resolu')
        self.assertEqual(self.intervention.compte_rendu, "Remplacement du roulement défectueux.")

        # Stock déduit de la quantité utilisée
        self.assertEqual(self.piece.quantite_stock, 3)
        self.assertEqual(
            InterventionPiece.objects.get(intervention=self.intervention, piece=self.piece).quantite_utilisee,
            2,
        )

        # Horodatage : date_resolution posée, et duree_arret_heures() reflète
        # bien l'écart entre date_creation et date_resolution (~3h).
        self.assertIsNotNone(self.intervention.date_resolution)
        self.assertAlmostEqual(self.intervention.duree_arret_heures(), 3.0, delta=0.05)

    def test_resolution_sans_piece_fonctionne(self):
        reponse = self.client.post(
            reverse('resoudre_intervention', args=[self.intervention.id]),
            {'pieces_utilisees': 'non', 'compte_rendu': "Redémarrage simple, RAS."},
        )
        self.assertRedirects(reponse, reverse('liste_interventions'))

        self.intervention.refresh_from_db()
        self.assertEqual(self.intervention.statut, 'resolu')
        self.assertEqual(InterventionPiece.objects.filter(intervention=self.intervention).count(), 0)

    def test_stock_insuffisant_bloque_la_resolution(self):
        reponse = self.client.post(
            reverse('resoudre_intervention', args=[self.intervention.id]),
            {
                'pieces_utilisees': 'oui',
                'piece_id': [str(self.piece.id)],
                f'quantite_{self.piece.id}': '999',
                'compte_rendu': "Tentative avec quantité excessive.",
            },
        )
        self.assertRedirects(reponse, reverse('liste_interventions'))

        self.intervention.refresh_from_db()
        self.piece.refresh_from_db()

        # Rien n'est appliqué : ni la résolution, ni la déduction de stock
        self.assertEqual(self.intervention.statut, 'en_cours')
        self.assertIsNone(self.intervention.date_resolution)
        self.assertEqual(self.piece.quantite_stock, 5)

    def test_horodatage_alimente_analyse_temps_arret(self):
        """Vérifie que l'Analyse des Temps d'Arrêt (statistiques_machines)
        reflète bien la durée entre date_creation et date_resolution une
        fois l'intervention résolue via la nouvelle fenêtre modale."""
        self.client.post(
            reverse('resoudre_intervention', args=[self.intervention.id]),
            {'pieces_utilisees': 'non', 'compte_rendu': "RAS."},
        )

        reponse = self.client.get(reverse('statistiques') + '?periode=mois')
        self.assertEqual(reponse.status_code, 200)

        noms = reponse.context['noms_machines']
        temps_arret = reponse.context['temps_arret']
        index_machine = noms.index(self.machine.nom)
        self.assertAlmostEqual(temps_arret[index_machine], 3.0, delta=0.05)
