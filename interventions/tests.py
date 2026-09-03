from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from machines.models import Machine, PieceDetachee
from .models import Intervention, InterventionPiece, DemandeAmelioration

Utilisateur = get_user_model()


class NatureInterventionTests(TestCase):
    """Vérifie la bascule Panne / Intervention du formulaire "Signalement de
    Panne ou d'une Intervention" (champ `nature`), et son exploitation dans
    Analyse (répartition par nature) et Analyse des Temps d'Arrêt (filtre)."""

    def setUp(self):
        self.utilisateur = Utilisateur.objects.create_superuser(
            username='admin_test4', email='admin4@test.local', password='motdepasse123',
        )
        self.client.force_login(self.utilisateur)
        self.machine = Machine.objects.create(
            nom="Presse 3", code_interne="P3", emplacement="Atelier",
        )

    def _declarer(self, **extra):
        donnees = {
            'machine': self.machine.id,
            'etat_machine': 'arretee',
            'titre': "Test",
            'description': "Test",
            'mode': 'panne',
        }
        donnees.update(extra)
        return self.client.post(reverse('declarer_panne'), donnees)

    def test_mode_panne_par_defaut(self):
        self._declarer()
        intervention = Intervention.objects.latest('id')
        self.assertEqual(intervention.nature, 'panne')

    def test_mode_intervention_utilise_la_nature_choisie(self):
        self._declarer(mode='intervention', nature='nettoyage')
        intervention = Intervention.objects.latest('id')
        self.assertEqual(intervention.nature, 'nettoyage')

    def test_mode_intervention_sans_nature_valide_retombe_sur_divers(self):
        self._declarer(mode='intervention', nature='')
        intervention = Intervention.objects.latest('id')
        self.assertEqual(intervention.nature, 'divers')

    def test_filtre_nature_sur_analyse_temps_arret(self):
        Intervention.objects.create(
            titre="Panne", machine=self.machine, statut='resolu',
            etat_machine='arretee', nature='panne',
            date_creation=timezone.now(), date_resolution=timezone.now() + timedelta(hours=2),
        )
        Intervention.objects.create(
            titre="Nettoyage", machine=self.machine, statut='resolu',
            etat_machine='arretee', nature='nettoyage',
            date_creation=timezone.now(), date_resolution=timezone.now() + timedelta(hours=1),
        )

        reponse = self.client.get(reverse('statistiques') + '?periode=mois&nature=nettoyage')
        index_machine = reponse.context['noms_machines'].index(self.machine.nom)
        self.assertAlmostEqual(reponse.context['temps_arret'][index_machine], 1.0, delta=0.05)

    def test_repartition_par_nature_sur_page_analyse(self):
        Intervention.objects.create(
            titre="Panne 1", machine=self.machine, type_intervention='correctif', nature='panne',
        )
        Intervention.objects.create(
            titre="Panne 2", machine=self.machine, type_intervention='correctif', nature='panne',
        )
        Intervention.objects.create(
            titre="Réglage 1", machine=self.machine, type_intervention='correctif', nature='reglage',
        )
        # Une intervention préventive ne doit pas polluer cette répartition
        # (elle reste à sa nature par défaut 'panne', non pertinente ici).
        Intervention.objects.create(
            titre="Entretien programmé", machine=self.machine, type_intervention='preventif',
        )

        reponse = self.client.get(reverse('maintenance_analyse'))
        repartition = dict(zip(reponse.context['labels_nature'], reponse.context['donnees_nature']))
        self.assertEqual(repartition.get('Panne'), 2)
        self.assertEqual(repartition.get('Réglage'), 1)
        self.assertEqual(sum(reponse.context['donnees_nature']), 3)

    def test_couleurs_du_camembert_restent_alignees_meme_quand_le_tri_change(self):
        # "Réglage" est ici la nature la plus fréquente : elle passe donc en
        # tête du tri par nombre décroissant, devant "Panne". La couleur de
        # chaque nature doit rester la sienne, pas celle de sa position.
        for _ in range(3):
            Intervention.objects.create(
                titre="Réglage", machine=self.machine, type_intervention='correctif', nature='reglage',
            )
        Intervention.objects.create(
            titre="Panne", machine=self.machine, type_intervention='correctif', nature='panne',
        )

        reponse = self.client.get(reverse('maintenance_analyse'))
        labels = reponse.context['labels_nature']
        couleurs = reponse.context['couleurs_nature']
        couleurs_par_label = dict(zip(labels, couleurs))

        self.assertEqual(labels[0], 'Réglage')  # confirme que le tri place bien Réglage en tête
        self.assertEqual(couleurs_par_label['Réglage'], 'rgba(59, 130, 246, 0.85)')
        self.assertEqual(couleurs_par_label['Panne'], 'rgba(239, 68, 68, 0.85)')


class RenduPagesModifieesTests(TestCase):
    """Vérification basique (statut 200, pas d'erreur de template) des pages
    dont le HTML a été modifié dans cette série de changements."""

    def setUp(self):
        self.utilisateur = Utilisateur.objects.create_superuser(
            username='admin_test5', email='admin5@test.local', password='motdepasse123',
        )
        self.client.force_login(self.utilisateur)

    def test_pages_se_chargent_sans_erreur(self):
        for nom_url in ['declarer_panne', 'statistiques', 'maintenance_analyse', 'amelioration', 'liste_interventions', 'maintenance_curative']:
            reponse = self.client.get(reverse(nom_url))
            self.assertEqual(reponse.status_code, 200, f"{nom_url} a renvoyé {reponse.status_code}")


class ClotureDemandeAmeliorationTests(TestCase):
    """Vérifie que la date de clôture d'une Demande d'Amélioration est posée
    quand elle atteint un statut définitif, et effacée si elle est rouverte."""

    def setUp(self):
        self.utilisateur = Utilisateur.objects.create_superuser(
            username='admin_test3', email='admin3@test.local', password='motdepasse123',
        )
        self.client.force_login(self.utilisateur)
        self.demande = DemandeAmelioration.objects.create(
            titre="Ajouter un éclairage", description="Zone trop sombre", statut='nouvelle',
        )

    def test_cloture_posee_sur_statut_final(self):
        self.client.post(
            reverse('changer_statut_amelioration', args=[self.demande.id]),
            {'statut': 'acceptee'},
        )
        self.demande.refresh_from_db()
        self.assertEqual(self.demande.statut, 'acceptee')
        self.assertIsNotNone(self.demande.date_cloture)

    def test_reouverture_efface_la_cloture(self):
        self.demande.statut = 'acceptee'
        self.demande.date_cloture = timezone.now()
        self.demande.save()

        self.client.post(
            reverse('changer_statut_amelioration', args=[self.demande.id]),
            {'statut': 'en_etude'},
        )
        self.demande.refresh_from_db()
        self.assertEqual(self.demande.statut, 'en_etude')
        self.assertIsNone(self.demande.date_cloture)


class RegroupementListeInterventionsTests(TestCase):
    """Vérifie que le tableau de bord regroupe automatiquement les cartes
    par statut (à faire, puis en cours, puis résolu), plutôt que de les
    mélanger par simple date de création."""

    def setUp(self):
        self.utilisateur = Utilisateur.objects.create_superuser(
            username='admin_test2', email='admin2@test.local', password='motdepasse123',
        )
        self.client.force_login(self.utilisateur)
        self.machine = Machine.objects.create(
            nom="Presse 2", code_interne="P2", emplacement="Atelier",
        )

    def test_ordre_par_statut_puis_date(self):
        # Créées volontairement dans le désordre pour vérifier que le tri
        # ne dépend pas de l'ordre de création.
        resolu = Intervention.objects.create(
            titre="Résolu", machine=self.machine, statut='resolu',
        )
        a_faire_ancienne = Intervention.objects.create(
            titre="A faire (ancienne)", machine=self.machine, statut='a_faire',
        )
        en_cours = Intervention.objects.create(
            titre="En cours", machine=self.machine, statut='en_cours',
        )
        a_faire_recente = Intervention.objects.create(
            titre="A faire (récente)", machine=self.machine, statut='a_faire',
        )

        reponse = self.client.get(reverse('liste_interventions'))
        ordre_obtenu = [i.titre for i in reponse.context['interventions']]

        # Groupe "à faire" (la plus récente d'abord) puis "en cours" puis "résolu"
        self.assertEqual(
            ordre_obtenu,
            ["A faire (récente)", "A faire (ancienne)", "En cours", "Résolu"],
        )


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
