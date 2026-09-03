from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Machine, PieceDetachee, Contrat

Utilisateur = get_user_model()


class AjusterStockAtomiqueTests(TestCase):
    """Vérifie que l'ajustement de stock (Stock de Pièces) passe par une
    mise à jour atomique (F()) plutôt qu'un aller-retour Python (lecture,
    +=/-=, save()), qui pouvait perdre un ajustement concurrent ou laisser
    passer un retrait supérieur au stock réel (voir
    machines/views.py::ajuster_stock)."""

    def setUp(self):
        self.utilisateur = Utilisateur.objects.create_superuser(
            username='admin_stock', email='admin_stock@test.local', password='motdepasse123',
        )
        self.client.force_login(self.utilisateur)
        self.piece = PieceDetachee.objects.create(nom="Roulement", reference="ROUL-STOCK", quantite_stock=5)

    def test_ajouter_incremente_le_stock(self):
        self.client.post(reverse('ajuster_stock_piece', args=[self.piece.id]), {'action': 'ajouter', 'quantite': '3'})
        self.piece.refresh_from_db()
        self.assertEqual(self.piece.quantite_stock, 8)

    def test_retirer_plus_que_le_stock_est_refuse_et_ne_change_rien(self):
        self.client.post(reverse('ajuster_stock_piece', args=[self.piece.id]), {'action': 'retirer', 'quantite': '999'})
        self.piece.refresh_from_db()
        self.assertEqual(self.piece.quantite_stock, 5)

    def test_retirer_exactement_le_stock_disponible_fonctionne(self):
        self.client.post(reverse('ajuster_stock_piece', args=[self.piece.id]), {'action': 'retirer', 'quantite': '5'})
        self.piece.refresh_from_db()
        self.assertEqual(self.piece.quantite_stock, 0)


class TroncatureChampsTests(TestCase):
    """Vérifie que les champs texte des formulaires de création (Machine,
    Pièce, Contrat) sont tronqués à la longueur du modèle avant
    l'enregistrement. Sans ça, un titre/nom trop long passe silencieusement
    en local (SQLite n'impose pas la limite VARCHAR) mais plante en
    production avec une erreur 500 (Postgres, sur Railway, la rejette)."""

    def setUp(self):
        self.utilisateur = Utilisateur.objects.create_superuser(
            username='admin_troncature', email='admin_troncature@test.local', password='motdepasse123',
        )
        self.client.force_login(self.utilisateur)

    def test_nom_machine_trop_long_est_tronque(self):
        self.client.post(reverse('ajouter_machine'), {
            'nom': "N" * 500, 'code_interne': 'CODE-TEST', 'emplacement': 'Atelier',
        })
        machine = Machine.objects.get(code_interne='CODE-TEST')
        self.assertEqual(len(machine.nom), 100)

    def test_nom_piece_trop_long_est_tronque(self):
        self.client.post(reverse('ajouter_piece'), {
            'nom': "P" * 500, 'reference': 'REF-TEST', 'quantite_stock': '1', 'stock_minimum': '1',
        })
        piece = PieceDetachee.objects.get(reference='REF-TEST')
        self.assertEqual(len(piece.nom), 150)

    def test_prestataire_contrat_trop_long_est_tronque(self):
        self.client.post(reverse('contrats'), {
            'prestataire': "C" * 500, 'type_contrat': 'autre', 'prix': '100', 'date_debut': '2026-01-01',
        })
        contrat = Contrat.objects.latest('id')
        self.assertEqual(len(contrat.prestataire), 150)
