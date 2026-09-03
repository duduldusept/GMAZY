from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from django.urls import reverse
from django.db import transaction
from django.db.models import Case, When, IntegerField, Count
from machines.models import Machine, Zone, PieceDetachee
from .models import Intervention, DemandeAmelioration, InterventionPiece
from utilisateurs.permissions import a_le_droit, necessite_droit

# CORRECTIF SÉCURITÉ : on ne fournit plus les listes Python brutes au
# template pour un rendu avec |safe (faille XSS si un nom de machine
# contient des caractères spéciaux, ex: </script>). On utilise désormais
# {% json_script %} côté template, qui échappe correctement les données.

@login_required  # Oblige l'utilisateur à être connecté pour voir cette page
@necessite_droit('declarer_panne')
def declarer_panne(request):
    if request.method == 'POST':
        # On récupère les données du formulaire HTML
        machine_id = request.POST.get('machine')
        titre = request.POST.get('titre')
        description = request.POST.get('description')

        # Menu déroulant "État de la machine" : seule la valeur 'arretee'
        # sera comptabilisée dans le temps d'arrêt (voir statistiques_machines
        # ci-dessous). On valide la valeur reçue pour ne jamais enregistrer
        # autre chose que les choix proposés dans le formulaire.
        etat_machine = request.POST.get('etat_machine', 'arretee')
        if etat_machine not in dict(Intervention.ETAT_MACHINE_CHOICES):
            etat_machine = 'arretee'

        # Bascule "Panne" / "Intervention" en haut du formulaire : en mode
        # Intervention, la nature vient du menu déroulant (Réglage,
        # Nettoyage, Modification, Divers, Travaux Neuf) ; en mode Panne
        # (par défaut), la nature reste 'panne'.
        mode = request.POST.get('mode', 'panne')
        if mode == 'intervention':
            nature = request.POST.get('nature', '')
            if nature not in dict(Intervention.NATURE_CHOICES) or nature == 'panne':
                nature = 'divers'
        else:
            nature = 'panne'

        # BUGFIX : get_object_or_404 évite une erreur 500 si l'ID de
        # machine envoyé par le formulaire est invalide ou manquant.
        machine_concerne = get_object_or_404(Machine, id=machine_id)

        # On crée l'intervention en base de données
        Intervention.objects.create(
            titre=titre,
            description=description,
            machine=machine_concerne,
            type_intervention='correctif',
            statut='a_faire',
            etat_machine=etat_machine,
            nature=nature,
        )

        if mode == 'intervention':
            messages.success(request, "L'intervention a bien été signalée à l'équipe de maintenance.")
        else:
            messages.success(request, "La panne a bien été signalée à l'équipe de maintenance.")
        return redirect('liste_interventions')

    # Si c'est une requête simple (GET), on affiche juste la page avec la liste des machines
    machines_disponibles = Machine.objects.all()
    return render(request, 'interventions/declarer_panne.html', {'machines': machines_disponibles})


@login_required
@necessite_droit('tableau_de_bord')
def liste_interventions(request):
    # On regroupe automatiquement les cartes par statut (à faire, puis en
    # cours, puis résolu/clôturé), et on trie par date décroissante à
    # l'intérieur de chaque groupe.
    ordre_statut = Case(
        When(statut='a_faire', then=0),
        When(statut='en_cours', then=1),
        When(statut='resolu', then=2),
        output_field=IntegerField(),
    )
    interventions = Intervention.objects.all().order_by(ordre_statut, '-date_creation')
    # Pièces disponibles proposées dans la fenêtre de résolution (voir resoudre_intervention)
    pieces_stock = PieceDetachee.objects.all().order_by('nom')
    return render(request, 'interventions/liste_interventions.html', {
        'interventions': interventions,
        'pieces_stock': pieces_stock,
    })


@login_required
@necessite_droit('changer_statut_intervention')
def changer_statut(request, id_intervention):
    """Fait passer une intervention de "À faire" à "En cours" (prise en
    charge, accessible à tout le monde). Le passage à "Résolu" se fait
    désormais via resoudre_intervention, qui recueille le compte-rendu et
    les pièces éventuellement utilisées avant de clôturer."""
    if request.method == 'POST':
        # BUGFIX : get_object_or_404 évite une erreur 500 si l'ID n'existe pas
        intervention = get_object_or_404(Intervention, id=id_intervention)

        if intervention.statut == 'a_faire':
            intervention.statut = 'en_cours'
            intervention.save()
            messages.success(request, f"L'intervention #{intervention.id} a été prise en charge.")

    # Dans tous les cas, on redirige sagement vers le tableau de bord sans casser la page
    return redirect('liste_interventions')


@login_required
@necessite_droit('changer_statut_intervention')
def resoudre_intervention(request, id_intervention):
    """Clôture une intervention "En cours" depuis la fenêtre de résolution
    du tableau de bord : indique si des pièces ont été utilisées (et les
    déduit du stock via InterventionPiece, qui gère déjà la validation et
    la déduction - voir models.py), et enregistre le compte-rendu."""
    intervention = get_object_or_404(Intervention, id=id_intervention)

    if request.method == 'POST':
        if intervention.statut != 'en_cours':
            messages.error(request, "Cette intervention ne peut pas être résolue dans son état actuel.")
            return redirect('liste_interventions')

        # Sécurisé par Groupe / Permission, comme l'ancienne clôture via changer_statut
        if not (request.user.has_perm('interventions.can_close_intervention') or request.user.is_superuser):
            messages.error(request, "Action refusée : Vous devez faire partie du groupe autorisé pour clôturer.")
            return redirect('liste_interventions')

        pieces_utilisees = request.POST.get('pieces_utilisees') == 'oui'
        compte_rendu = (request.POST.get('compte_rendu') or '').strip()

        try:
            with transaction.atomic():
                if pieces_utilisees:
                    for piece_id in request.POST.getlist('piece_id'):
                        quantite = int(request.POST.get(f'quantite_{piece_id}') or 0)
                        if quantite > 0:
                            piece = get_object_or_404(PieceDetachee, id=piece_id)
                            InterventionPiece.objects.create(
                                intervention=intervention,
                                piece=piece,
                                quantite_utilisee=quantite,
                            )

                intervention.statut = 'resolu'
                intervention.date_resolution = timezone.now()
                intervention.compte_rendu = compte_rendu
                intervention.save()
        except ValueError as e:
            # Levée par InterventionPiece.save() si le stock est insuffisant :
            # la transaction est annulée, l'intervention reste "En cours".
            messages.error(request, str(e))
            return redirect('liste_interventions')

        messages.success(request, f"L'intervention #{intervention.id} a été clôturée avec succès !")

    return redirect('liste_interventions')


@login_required
@necessite_droit('analyse_temps_arret')
def statistiques_machines(request):
    # 1. Récupérer le filtre temporel choisi par l'utilisateur (par défaut: mois)
    periode = request.GET.get('periode', 'mois')

    # Filtre optionnel par nature d'intervention (Panne, Réglage, Nettoyage,
    # Modification, Divers, Travaux Neuf) : vide = toutes natures confondues.
    nature = request.GET.get('nature', '')
    if nature not in dict(Intervention.NATURE_CHOICES):
        nature = ''

    machines = Machine.objects.all()
    noms_machines = []
    temps_arret = []
    temps_degrade = []

    maintenant = timezone.now()

    for machine in machines:
        noms_machines.append(machine.nom)

        # On récupère TOUTES les interventions de la machine (résolues ou
        # encore en cours) sur la période demandée, puis on sépare les deux
        # séries pour le graphique :
        # - 'arretee'  -> barres rouges (temps d'arrêt réel)
        # - 'degradee' -> barres orange clair (temps en mode dégradé, la
        #                 machine continue de fonctionner)
        #
        # Le compteur démarre dès l'envoi de la demande d'intervention
        # (date_creation) : on filtre donc la période sur cette date plutôt
        # que sur date_resolution, afin qu'une panne toujours en cours (pas
        # encore résolue) apparaisse déjà dans le total de la période en
        # cours. duree_arret_heures() (voir models.py) calcule la durée
        # jusqu'à maintenant tant que l'intervention n'est pas résolue, et
        # se fige à la valeur finale une fois le clic sur "Résolu" effectué.
        #
        # NB : les interventions préventives programmées via le calendrier
        # ont etat_machine='planifiee', elles ne sont donc jamais comptées
        # ici (ni 'arretee' ni 'degradee').
        interventions = Intervention.objects.filter(machine=machine)

        if nature:
            interventions = interventions.filter(nature=nature)

        if periode == 'jour':
            interventions = interventions.filter(date_creation__date=maintenant.date())
        elif periode == 'mois':
            interventions = interventions.filter(date_creation__year=maintenant.year, date_creation__month=maintenant.month)
        elif periode == 'annee':
            interventions = interventions.filter(date_creation__year=maintenant.year)

        interventions_arretees = interventions.filter(etat_machine='arretee')
        interventions_degradees = interventions.filter(etat_machine='degradee')

        # Somme des heures pour chaque série (fait appel à la fonction du model).
        # BUGFIX : on arrondit désormais le total à 1 décimale plutôt que de
        # tronquer chaque intervention à l'heure entière avant de sommer. Avec
        # l'ancienne méthode, une panne récente (< 1h) comptait pour 0, et
        # plusieurs pannes courtes sommées entre elles perdaient jusqu'à ~1h
        # chacune (ex: trois pannes de 0.9h affichaient 0h au lieu de ~2.7h).
        total_heures_arret = round(sum(interv.duree_arret_heures() for interv in interventions_arretees), 1)
        total_heures_degrade = round(sum(interv.duree_arret_heures() for interv in interventions_degradees), 1)

        temps_arret.append(total_heures_arret)
        temps_degrade.append(total_heures_degrade)

    context = {
        'noms_machines': noms_machines,
        'temps_arret': temps_arret,
        'temps_degrade': temps_degrade,
        'periode_actuelle': periode,
        'nature_choices': Intervention.NATURE_CHOICES,
        'nature_selectionnee': nature,
    }
    return render(request, 'interventions/statistiques.html', context)


# =====================================================================
# ONGLET MAINTENANCE
# =====================================================================

@login_required
@necessite_droit('maintenance_preventive_consulter')
def maintenance_preventive(request):
    """Onglet Maintenance > Maintenance Préventive : calendrier permettant
    de programmer des interventions de maintenance préventive sur une
    machine, à une date/heure donnée. Certains rôles peuvent consulter cette
    page (calendrier + historique) sans pouvoir programmer de nouvelle
    intervention (droit 'maintenance_preventive_programmer', voir la page
    d'administration des droits) : la case est vérifiée ici (POST) plutôt
    que de masquer seulement le bouton côté template, pour bloquer aussi un
    envoi direct du formulaire."""
    if request.method == 'POST':
        if not a_le_droit(request.user, 'maintenance_preventive_programmer'):
            messages.error(request, "Action refusée : la programmation d'une maintenance préventive n'est pas disponible pour ton rôle.")
            return redirect('maintenance_preventive')

        machine_id = request.POST.get('machine')
        titre = request.POST.get('titre')
        description = request.POST.get('description', '')
        date_prevue_brute = request.POST.get('date_prevue')

        # Le champ HTML <input type="datetime-local"> envoie une chaîne du
        # type "2026-08-05T08:00" (heure "flottante", sans fuseau horaire).
        # On la convertit en datetime, puis on la rend "aware" avec le
        # fuseau horaire courant de l'application (voir TIME_ZONE dans
        # settings.py) pour respecter USE_TZ=True sans décaler l'heure
        # saisie par l'utilisateur.
        date_prevue = parse_datetime(date_prevue_brute) if date_prevue_brute else None
        if date_prevue and timezone.is_naive(date_prevue):
            date_prevue = timezone.make_aware(date_prevue)

        if not date_prevue:
            messages.error(request, "Merci d'indiquer une date et une heure de planification valides.")
            return redirect('maintenance_preventive')

        machine_concernee = get_object_or_404(Machine, id=machine_id)

        Intervention.objects.create(
            titre=titre,
            description=description,
            machine=machine_concernee,
            type_intervention='preventif',
            statut='a_faire',
            etat_machine='planifiee',
            date_prevue=date_prevue,
        )

        messages.success(request, "L'intervention de maintenance préventive a bien été programmée.")
        return redirect('maintenance_preventive')

    machines_disponibles = Machine.objects.all().order_by('nom')

    interventions_realisees = Intervention.objects.filter(
        type_intervention='preventif',
        statut='resolu',
    ).select_related('machine').order_by('-date_resolution')

    context = {
        'machines': machines_disponibles,
        'interventions_realisees': interventions_realisees,
    }
    return render(request, 'interventions/maintenance_preventive.html', context)


@login_required
@necessite_droit('maintenance_preventive_consulter')
def evenements_preventifs(request):
    """Renvoie en JSON les interventions préventives programmées, au
    format attendu par FullCalendar (utilisé par maintenance_preventive.html)."""
    interventions = Intervention.objects.filter(
        type_intervention='preventif',
        date_prevue__isnull=False,
    ).select_related('machine')

    couleurs_statut = {
        'a_faire': '#f59e0b',   # orange : planifiée, pas encore réalisée
        'en_cours': '#3b82f6',  # bleu : en cours
        'resolu': '#22c55e',    # vert : réalisée
    }

    evenements = []
    for interv in interventions:
        evenements.append({
            'id': interv.id,
            'title': f"{interv.machine.code_interne} - {interv.titre}",
            # strftime (et non isoformat) volontairement : on renvoie l'heure
            # "flottante" telle que saisie par le technicien, sans décalage
            # de fuseau horaire côté navigateur.
            'start': interv.date_prevue.strftime('%Y-%m-%dT%H:%M:%S'),
            'color': couleurs_statut.get(interv.statut, '#64748b'),
            'url': reverse('liste_interventions') + f'#intervention-{interv.id}',
        })

    return JsonResponse(evenements, safe=False)


@login_required
@necessite_droit('maintenance_curative')
def maintenance_curative(request):
    """Onglet Maintenance > Historique Maintenance : liste toutes les
    interventions curatives (pannes) et préventives, filtrable par machine,
    zone et type, triable par date, machine ou zone."""
    interventions = Intervention.objects.select_related('machine', 'machine__zone')

    machine_id = request.GET.get('machine')
    machine_selectionnee = None
    if machine_id:
        try:
            machine_selectionnee = int(machine_id)
            interventions = interventions.filter(machine_id=machine_selectionnee)
        except (TypeError, ValueError):
            machine_selectionnee = None

    zone_id = request.GET.get('zone')
    zone_selectionnee = None
    if zone_id:
        try:
            zone_selectionnee = int(zone_id)
            interventions = interventions.filter(machine__zone_id=zone_selectionnee)
        except (TypeError, ValueError):
            zone_selectionnee = None

    type_selectionne = request.GET.get('type')
    if type_selectionne not in ('correctif', 'preventif'):
        type_selectionne = ''
    else:
        interventions = interventions.filter(type_intervention=type_selectionne)

    tris_valides = {
        '-date_creation': '-date_creation',
        'date_creation': 'date_creation',
        'machine': 'machine__nom',
        'zone': 'machine__zone__nom',
    }
    tri = request.GET.get('tri', '-date_creation')
    if tri not in tris_valides:
        tri = '-date_creation'
    interventions = interventions.order_by(tris_valides[tri])

    context = {
        'interventions': interventions,
        'machines': Machine.objects.all().order_by('nom'),
        'zones': Zone.objects.all().order_by('nom'),
        'machine_selectionnee': machine_selectionnee,
        'zone_selectionnee': zone_selectionnee,
        'type_selectionne': type_selectionne,
        'tri': tri,
    }
    return render(request, 'interventions/maintenance_curative.html', context)


@login_required
@necessite_droit('analyse_preventif_curatif')
def maintenance_analyse(request):
    """Onglet Maintenance > Analyse : camembert affichant le pourcentage
    d'interventions préventives vs curatives."""
    nb_preventif = Intervention.objects.filter(type_intervention='preventif').count()
    nb_correctif = Intervention.objects.filter(type_intervention='correctif').count()
    total = nb_preventif + nb_correctif

    if total > 0:
        pct_preventif = round(nb_preventif * 100 / total, 1)
        pct_correctif = round(nb_correctif * 100 / total, 1)
    else:
        pct_preventif = 0
        pct_correctif = 0

    # Répartition par nature d'intervention (Panne, Réglage, Nettoyage,
    # Modification, Divers, Travaux Neuf), calculée sur les interventions
    # curatives : c'est le seul flux de création (le formulaire "Signalement
    # de Panne ou d'une Intervention") où ce champ est renseigné par
    # l'utilisateur plutôt que laissé à sa valeur par défaut 'panne'.
    libelles_nature = dict(Intervention.NATURE_CHOICES)
    repartition_nature = (
        Intervention.objects.filter(type_intervention='correctif')
        .values('nature')
        .annotate(total=Count('id'))
        .order_by('-total')
    )
    labels_nature = [libelles_nature.get(r['nature'], r['nature']) for r in repartition_nature]
    donnees_nature = [r['total'] for r in repartition_nature]

    context = {
        'total': total,
        'nb_preventif': nb_preventif,
        'nb_correctif': nb_correctif,
        'pct_preventif': pct_preventif,
        'pct_correctif': pct_correctif,
        'labels_nature': labels_nature,
        'donnees_nature': donnees_nature,
    }
    return render(request, 'interventions/maintenance_analyse.html', context)


# =====================================================================
# ONGLET SERVICE GÉNÉRAUX
# =====================================================================

@login_required
@necessite_droit('service_generaux_batiment')
def service_generaux_batiment(request):
    """Onglet Service Généraux > Bâtiment : liste toutes les interventions
    (préventives et curatives) des équipements rattachés à la Zone
    "Batiment" (voir Zone dans machines/models.py), filtrable par machine
    et type, triable par date ou machine."""
    interventions = Intervention.objects.filter(
        machine__zone__nom__icontains='Batiment'
    ).select_related('machine', 'machine__zone')

    machine_id = request.GET.get('machine')
    machine_selectionnee = None
    if machine_id:
        try:
            machine_selectionnee = int(machine_id)
            interventions = interventions.filter(machine_id=machine_selectionnee)
        except (TypeError, ValueError):
            machine_selectionnee = None

    type_selectionne = request.GET.get('type')
    if type_selectionne not in ('correctif', 'preventif'):
        type_selectionne = ''
    else:
        interventions = interventions.filter(type_intervention=type_selectionne)

    tris_valides = {
        '-date_creation': '-date_creation',
        'date_creation': 'date_creation',
        'machine': 'machine__nom',
    }
    tri = request.GET.get('tri', '-date_creation')
    if tri not in tris_valides:
        tri = '-date_creation'
    interventions = interventions.order_by(tris_valides[tri])

    context = {
        'interventions': interventions,
        'machines': Machine.objects.filter(zone__nom__icontains='Batiment').order_by('nom'),
        'machine_selectionnee': machine_selectionnee,
        'type_selectionne': type_selectionne,
        'tri': tri,
    }
    return render(request, 'interventions/service_generaux_batiment.html', context)


@login_required
@necessite_droit('service_generaux_batiment')
def service_generaux_preventif(request):
    """Onglet Service Généraux > Bâtiment > Préventif : calendrier des
    maintenances préventives programmées pour les équipements de la zone
    "Batiment", ainsi que la liste de celles déjà réalisées (statut
    'resolu')."""
    interventions_realisees = Intervention.objects.filter(
        type_intervention='preventif',
        statut='resolu',
        machine__zone__nom__icontains='Batiment',
    ).select_related('machine').order_by('-date_resolution')

    context = {
        'interventions_realisees': interventions_realisees,
    }
    return render(request, 'interventions/service_generaux_preventif.html', context)


@login_required
@necessite_droit('service_generaux_batiment')
def evenements_preventifs_batiment(request):
    """Renvoie en JSON les interventions préventives programmées pour les
    équipements de la zone "Batiment", au format attendu par FullCalendar
    (utilisé par service_generaux_preventif.html)."""
    interventions = Intervention.objects.filter(
        type_intervention='preventif',
        date_prevue__isnull=False,
        machine__zone__nom__icontains='Batiment',
    ).select_related('machine')

    couleurs_statut = {
        'a_faire': '#f59e0b',   # orange : planifiée, pas encore réalisée
        'en_cours': '#3b82f6',  # bleu : en cours
        'resolu': '#22c55e',    # vert : réalisée
    }

    evenements = []
    for interv in interventions:
        evenements.append({
            'id': interv.id,
            'title': f"{interv.machine.code_interne} - {interv.titre}",
            'start': interv.date_prevue.strftime('%Y-%m-%dT%H:%M:%S'),
            'color': couleurs_statut.get(interv.statut, '#64748b'),
            'url': reverse('liste_interventions') + f'#intervention-{interv.id}',
        })

    return JsonResponse(evenements, safe=False)


# =====================================================================
# ONGLET AMÉLIORATION
# =====================================================================

@login_required
@necessite_droit('amelioration')
def amelioration(request):
    """Onglet Amélioration (sous Déclarer une panne) : formulaire pour
    soumettre une demande d'amélioration sur une machine ou sur le
    Bâtiment / Services Généraux (machine laissée vide), et historique de
    toutes les demandes déjà soumises."""
    if request.method == 'POST':
        titre = (request.POST.get('titre') or '').strip()
        description = (request.POST.get('description') or '').strip()
        machine_id = request.POST.get('machine')

        machine_concernee = None
        if machine_id:
            machine_concernee = get_object_or_404(Machine, id=machine_id)

        if not titre or not description:
            messages.error(request, "Merci de renseigner un titre et une description.")
        else:
            DemandeAmelioration.objects.create(
                titre=titre,
                description=description,
                machine=machine_concernee,
                demandeur=request.user if request.user.is_authenticated else None,
            )
            messages.success(request, "Ta demande d'amélioration a bien été enregistrée.")

        return redirect('amelioration')

    demandes = DemandeAmelioration.objects.select_related('machine', 'demandeur').order_by('-date_creation')

    context = {
        'demandes': demandes,
        'machines': Machine.objects.all().order_by('nom'),
        'statut_choices': DemandeAmelioration.STATUT_CHOICES,
    }
    return render(request, 'interventions/amelioration.html', context)


@login_required
@necessite_droit('changer_statut_amelioration')
def changer_statut_amelioration(request, id_demande):
    """Met à jour le statut d'une demande d'amélioration depuis
    l'historique de l'onglet Amélioration."""
    if request.method == 'POST':
        demande = get_object_or_404(DemandeAmelioration, id=id_demande)
        nouveau_statut = request.POST.get('statut')

        if nouveau_statut in dict(DemandeAmelioration.STATUT_CHOICES):
            demande.statut = nouveau_statut
            # Horodatage de clôture : posé quand la demande arrive à un statut
            # définitif, effacé si elle est rouverte (retour à Nouvelle / En étude).
            if nouveau_statut in ('acceptee', 'refusee', 'realisee'):
                demande.date_cloture = timezone.now()
            else:
                demande.date_cloture = None
            demande.save()
            messages.success(request, f"Statut de la demande « {demande.titre} » mis à jour.")
        else:
            messages.error(request, "Statut invalide.")

    return redirect('amelioration')
