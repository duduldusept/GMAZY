from datetime import date
from decimal import Decimal, InvalidOperation

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, F, Sum, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce
from django.http import FileResponse, Http404
from django.utils.dateparse import parse_date

from .models import Machine, Zone, PieceDetachee, Section, DepenseBudget, Contrat
# InterventionPiece vit dans l'app interventions (table de liaison entre une
# Intervention et une PieceDetachee). On l'importe ici uniquement dans les
# vues (jamais dans models.py) pour éviter tout risque d'import circulaire
# entre les deux apps.
from interventions.models import InterventionPiece
from utilisateurs.decorators import bloquer_pour_role

MOIS_CHOICES = [
    (1, 'Janvier'), (2, 'Février'), (3, 'Mars'), (4, 'Avril'),
    (5, 'Mai'), (6, 'Juin'), (7, 'Juillet'), (8, 'Août'),
    (9, 'Septembre'), (10, 'Octobre'), (11, 'Novembre'), (12, 'Décembre'),
]


@login_required
@bloquer_pour_role('chef_equipe', 'production')  # Stock de Pièces : hors périmètre
def stock_pieces(request):
    """Affiche le stock de pièces détachées (onglet "Stock de Pièces"),
    avec une recherche simple (nom, référence, machine compatible) et
    une mise en évidence des pièces en alerte de stock bas."""
    pieces = PieceDetachee.objects.select_related('machine_compatible').order_by('nom')

    recherche = request.GET.get('q', '').strip()
    if recherche:
        pieces = pieces.filter(
            Q(nom__icontains=recherche) |
            Q(reference__icontains=recherche) |
            Q(machine_compatible__nom__icontains=recherche) |
            Q(machine_compatible__code_interne__icontains=recherche)
        )

    return render(request, 'machines/stock_pieces.html', {
        'pieces': pieces,
        'recherche': recherche,
        'machines': Machine.objects.all().order_by('nom'),
    })


@login_required
@bloquer_pour_role('chef_equipe', 'production')  # Idem : dépend de Stock de Pièces
def ajuster_stock(request, id_piece):
    """Ajoute ou retire une quantité du stock d'une pièce depuis la page
    Stock de Pièces, sans passer par l'admin Django."""
    piece = get_object_or_404(PieceDetachee, id=id_piece)

    if request.method == 'POST':
        action = request.POST.get('action')
        try:
            quantite = int(request.POST.get('quantite', '0'))
        except (TypeError, ValueError):
            quantite = 0

        if quantite <= 0:
            messages.error(request, "Merci d'indiquer une quantité valide (supérieure à 0).")
        elif action == 'ajouter':
            piece.quantite_stock += quantite
            piece.save()
            messages.success(
                request,
                f"Stock de « {piece.nom} » : +{quantite} ({piece.quantite_stock} en stock)."
            )
        elif action == 'retirer':
            if quantite > piece.quantite_stock:
                messages.error(
                    request,
                    f"Stock insuffisant pour « {piece.nom} » : {piece.quantite_stock} disponible(s), "
                    f"{quantite} demandé(s)."
                )
            else:
                piece.quantite_stock -= quantite
                piece.save()
                messages.success(
                    request,
                    f"Stock de « {piece.nom} » : -{quantite} ({piece.quantite_stock} en stock)."
                )
        else:
            messages.error(request, "Action inconnue.")

    return redirect('stock_pieces')


@login_required
@bloquer_pour_role('chef_equipe', 'production')  # Idem : dépend de Stock de Pièces
def ajouter_piece(request):
    """Ajoute une toute nouvelle pièce au catalogue depuis la page Stock de
    Pièces (jusqu'ici possible uniquement depuis l'admin Django). La page
    Stock de Pièces elle-même n'étant déjà accessible qu'à Admin et
    Technicien (voir décorateur ci-dessus), cette action l'est aussi de
    fait, mais on garde le même décorateur ici par cohérence et pour rester
    protégé même si l'accès à la page venait à être élargi plus tard."""
    if request.method == 'POST':
        nom = (request.POST.get('nom') or '').strip()
        reference = (request.POST.get('reference') or '').strip()
        description = request.POST.get('description', '')
        machine_id = request.POST.get('machine_compatible')

        try:
            quantite_stock = int(request.POST.get('quantite_stock', '0'))
        except (TypeError, ValueError):
            quantite_stock = 0

        try:
            stock_minimum = int(request.POST.get('stock_minimum', '1'))
        except (TypeError, ValueError):
            stock_minimum = 1

        prix_brut = (request.POST.get('prix_unitaire') or '').strip()
        prix_unitaire = None
        if prix_brut:
            try:
                prix_unitaire = Decimal(prix_brut.replace(',', '.'))
            except InvalidOperation:
                prix_unitaire = None

        machine_compatible = None
        if machine_id:
            machine_compatible = get_object_or_404(Machine, id=machine_id)

        if not nom or not reference:
            messages.error(request, "Merci d'indiquer au moins un nom et une référence.")
        elif PieceDetachee.objects.filter(reference=reference).exists():
            messages.error(request, f"Une pièce avec la référence « {reference} » existe déjà.")
        else:
            PieceDetachee.objects.create(
                nom=nom,
                reference=reference,
                description=description,
                quantite_stock=max(quantite_stock, 0),
                stock_minimum=max(stock_minimum, 0),
                prix_unitaire=prix_unitaire,
                machine_compatible=machine_compatible,
            )
            messages.success(request, f"Pièce « {nom} » ajoutée au catalogue.")

    return redirect('stock_pieces')


@login_required
@bloquer_pour_role('chef_equipe', 'production')  # Idem : dépend de Stock de Pièces
def supprimer_piece(request, id_piece):
    """Supprime une pièce du catalogue depuis la page Stock de Pièces."""
    piece = get_object_or_404(PieceDetachee, id=id_piece)

    if request.method == 'POST':
        # SÉCURITÉ : une pièce déjà utilisée dans une intervention n'est
        # jamais supprimée directement : PieceDetachee -> InterventionPiece
        # est en CASCADE (voir interventions/models.py), donc la supprimer
        # effacerait par cascade les lignes InterventionPiece correspondantes
        # et, avec elles, l'historique utilisé par la page Budget Machine.
        if InterventionPiece.objects.filter(piece=piece).exists():
            messages.error(
                request,
                f"Impossible de supprimer « {piece.nom} » : elle a déjà été utilisée dans au moins une "
                f"intervention (son historique de coûts serait perdu). Tu peux en revanche mettre son stock à 0."
            )
        else:
            nom = piece.nom
            piece.delete()
            messages.success(request, f"Pièce « {nom} » supprimée du catalogue.")

    return redirect('stock_pieces')


@login_required
@bloquer_pour_role('chef_equipe', 'production', 'technicien')  # Budget Machine : hors périmètre
def budget_machine(request):
    """Onglet Budget > Budget Machine : calcule, pour chaque machine, le
    coût des pièces détachées utilisées (quantité utilisée x prix unitaire,
    via la table de liaison InterventionPiece) sur le mois et l'année
    sélectionnés (par défaut : le mois/l'année en cours).

    La date de référence retenue pour rattacher une pièce utilisée à un
    mois/une année est la date de signalement de l'intervention
    (date_creation), toujours renseignée contrairement à date_resolution.
    """
    aujourdhui = date.today()

    try:
        mois_selectionne = int(request.GET.get('mois', aujourdhui.month))
    except (TypeError, ValueError):
        mois_selectionne = aujourdhui.month
    if mois_selectionne < 1 or mois_selectionne > 12:
        mois_selectionne = aujourdhui.month

    try:
        annee_selectionnee = int(request.GET.get('annee', aujourdhui.year))
    except (TypeError, ValueError):
        annee_selectionnee = aujourdhui.year

    # Coût d'une ligne de pièce utilisée = quantité x prix unitaire de la pièce.
    cout_ligne = ExpressionWrapper(
        F('quantite_utilisee') * F('piece__prix_unitaire'),
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )

    lignes_budget = []
    total_mois_general = 0
    total_annee_general = 0

    for machine in Machine.objects.all().order_by('nom'):
        # Seules les pièces dont le prix unitaire est renseigné peuvent
        # entrer dans le calcul (une pièce sans prix ne peut pas être chiffrée).
        pieces_utilisees = InterventionPiece.objects.filter(
            intervention__machine=machine,
            piece__prix_unitaire__isnull=False,
        )

        cout_mois = pieces_utilisees.filter(
            intervention__date_creation__year=annee_selectionnee,
            intervention__date_creation__month=mois_selectionne,
        ).aggregate(
            total=Coalesce(Sum(cout_ligne), 0, output_field=DecimalField(max_digits=12, decimal_places=2))
        )['total']

        cout_annee = pieces_utilisees.filter(
            intervention__date_creation__year=annee_selectionnee,
        ).aggregate(
            total=Coalesce(Sum(cout_ligne), 0, output_field=DecimalField(max_digits=12, decimal_places=2))
        )['total']

        total_mois_general += cout_mois
        total_annee_general += cout_annee

        lignes_budget.append({
            'machine': machine,
            'cout_mois': cout_mois,
            'cout_annee': cout_annee,
        })

    context = {
        'lignes_budget': lignes_budget,
        'total_mois_general': total_mois_general,
        'total_annee_general': total_annee_general,
        'mois_choices': MOIS_CHOICES,
        'mois_selectionne': mois_selectionne,
        'annee_selectionnee': annee_selectionnee,
        # 5 dernières années (dont l'année en cours) proposées dans le filtre.
        'annees_disponibles': range(aujourdhui.year - 4, aujourdhui.year + 1),
    }
    return render(request, 'machines/budget_machine.html', context)


@login_required
@bloquer_pour_role('chef_equipe', 'production', 'technicien')  # Consommable / Entretien / Travaux Neuf : hors périmètre
def budget_section(request, code):
    """Onglet Budget > Consommable / Entretien / Travaux Neuf : historique
    des dépenses rattachées à une Section budgétaire donnée (voir Section
    et DepenseBudget dans machines/models.py), avec formulaire d'ajout et
    filtre mois/année (même logique que Budget Machine)."""
    section = get_object_or_404(Section, code=code)

    if request.method == 'POST':
        machine_id = request.POST.get('machine')
        titre = (request.POST.get('titre') or '').strip()
        description = request.POST.get('description', '')
        montant_brut = request.POST.get('montant', '')
        date_brute = request.POST.get('date_depense')

        try:
            montant = Decimal(montant_brut.replace(',', '.'))
        except (InvalidOperation, AttributeError):
            montant = None

        machine_liee = None
        if machine_id:
            machine_liee = get_object_or_404(Machine, id=machine_id)

        if not titre or montant is None or montant <= 0:
            messages.error(request, "Merci d'indiquer un intitulé et un montant valide (supérieur à 0).")
        else:
            DepenseBudget.objects.create(
                section=section,
                machine=machine_liee,
                titre=titre,
                description=description,
                montant=montant,
                date_depense=date_brute or date.today(),
            )
            messages.success(request, f"Dépense « {titre} » enregistrée dans la section {section.nom}.")

        return redirect('budget_section', code=code)

    aujourdhui = date.today()

    try:
        mois_selectionne = int(request.GET.get('mois', aujourdhui.month))
    except (TypeError, ValueError):
        mois_selectionne = aujourdhui.month
    if mois_selectionne < 1 or mois_selectionne > 12:
        mois_selectionne = aujourdhui.month

    try:
        annee_selectionnee = int(request.GET.get('annee', aujourdhui.year))
    except (TypeError, ValueError):
        annee_selectionnee = aujourdhui.year

    depenses = DepenseBudget.objects.filter(section=section).select_related('machine').order_by('-date_depense')

    total_mois = depenses.filter(
        date_depense__year=annee_selectionnee,
        date_depense__month=mois_selectionne,
    ).aggregate(
        total=Coalesce(Sum('montant'), 0, output_field=DecimalField(max_digits=12, decimal_places=2))
    )['total']

    total_annee = depenses.filter(
        date_depense__year=annee_selectionnee,
    ).aggregate(
        total=Coalesce(Sum('montant'), 0, output_field=DecimalField(max_digits=12, decimal_places=2))
    )['total']

    context = {
        'section': section,
        'depenses': depenses,
        'machines': Machine.objects.all().order_by('nom'),
        'mois_choices': MOIS_CHOICES,
        'mois_selectionne': mois_selectionne,
        'annee_selectionnee': annee_selectionnee,
        'annees_disponibles': range(aujourdhui.year - 4, aujourdhui.year + 1),
        'total_mois': total_mois,
        'total_annee': total_annee,
        'aujourdhui': aujourdhui,
    }
    return render(request, 'machines/budget_section.html', context)


# =====================================================================
# ONGLET MAINTENANCE > MACHINE (Parc machine)
# =====================================================================

@login_required
@bloquer_pour_role('chef_equipe', 'production')  # Parc Machine : réservé à Admin et Technicien
def parc_machines(request):
    """Onglet Maintenance > Machine : liste du parc machine, avec ajout et
    suppression directement depuis la page (réservé à Admin et Technicien)."""
    machines = Machine.objects.select_related('zone').order_by('nom')

    return render(request, 'machines/parc_machines.html', {
        'machines': machines,
        'zones': Zone.objects.all().order_by('nom'),
        'statut_choices': Machine.STATUT_CHOICES,
    })


@login_required
@bloquer_pour_role('chef_equipe', 'production')  # Idem : dépend de Parc Machine
def ajouter_machine(request):
    """Ajoute une nouvelle machine au parc depuis l'onglet Machine (jusqu'ici
    possible uniquement depuis l'admin Django)."""
    if request.method == 'POST':
        nom = (request.POST.get('nom') or '').strip()
        code_interne = (request.POST.get('code_interne') or '').strip()
        emplacement = (request.POST.get('emplacement') or '').strip()
        statut = request.POST.get('statut', 'fonctionne')
        zone_id = request.POST.get('zone')

        if statut not in dict(Machine.STATUT_CHOICES):
            statut = 'fonctionne'

        zone = None
        if zone_id:
            zone = get_object_or_404(Zone, id=zone_id)

        if not nom or not code_interne:
            messages.error(request, "Merci d'indiquer au moins un nom et un code interne.")
        elif Machine.objects.filter(code_interne=code_interne).exists():
            messages.error(request, f"Une machine avec le code interne « {code_interne} » existe déjà.")
        else:
            Machine.objects.create(
                nom=nom,
                code_interne=code_interne,
                zone=zone,
                emplacement=emplacement,
                statut=statut,
            )
            messages.success(request, f"Machine « {nom} » ajoutée au parc.")

    return redirect('parc_machines')


@login_required
@bloquer_pour_role('chef_equipe', 'production')  # Idem : dépend de Parc Machine
def supprimer_machine(request, id_machine):
    """Supprime une machine du parc depuis l'onglet Machine."""
    machine = get_object_or_404(Machine, id=id_machine)

    if request.method == 'POST':
        # SÉCURITÉ : une machine qui a déjà des interventions liées n'est
        # jamais supprimée directement : Intervention.machine est en CASCADE
        # (voir interventions/models.py), donc la supprimer effacerait par
        # cascade tout l'historique de pannes/maintenances de cette machine,
        # ainsi que les coûts de pièces associés utilisés par Budget Machine.
        if machine.interventions.exists():
            messages.error(
                request,
                f"Impossible de supprimer « {machine.nom} » : elle a déjà des interventions enregistrées "
                f"(son historique serait perdu). Tu peux en revanche la passer en statut « En panne » ou "
                f"« En cours de maintenance » si elle n'est plus utilisée."
            )
        else:
            nom = machine.nom
            machine.delete()
            messages.success(request, f"Machine « {nom} » supprimée du parc.")

    return redirect('parc_machines')


# =====================================================================
# ONGLET BUDGET > CONTRATS
# =====================================================================

@login_required
@bloquer_pour_role('chef_equipe', 'production', 'technicien')  # Contrats : même périmètre que le reste de l'onglet Budget
def contrats(request):
    """Onglet Budget > Contrats : liste des contrats prestataires
    (maintenance, assurance, location...), avec ajout (document PDF/image
    optionnel) et suppression directement depuis la page."""
    if request.method == 'POST':
        prestataire = (request.POST.get('prestataire') or '').strip()
        type_contrat = request.POST.get('type_contrat', 'autre')
        if type_contrat not in dict(Contrat.TYPE_CHOICES):
            type_contrat = 'autre'

        prix_brut = (request.POST.get('prix') or '').strip()
        try:
            prix = Decimal(prix_brut.replace(',', '.'))
        except (InvalidOperation, AttributeError):
            prix = None

        date_debut = parse_date(request.POST.get('date_debut', ''))
        date_fin_brute = request.POST.get('date_fin', '')
        date_fin = parse_date(date_fin_brute) if date_fin_brute else None

        description = request.POST.get('description', '')
        document = request.FILES.get('document')

        if not prestataire or prix is None or prix <= 0 or not date_debut:
            messages.error(request, "Merci d'indiquer au moins un prestataire, un prix valide (supérieur à 0) et une date de début.")
        elif date_fin and date_fin < date_debut:
            messages.error(request, "La date de fin ne peut pas être antérieure à la date de début.")
        else:
            Contrat.objects.create(
                prestataire=prestataire,
                type_contrat=type_contrat,
                prix=prix,
                date_debut=date_debut,
                date_fin=date_fin,
                description=description,
                document=document,
            )
            messages.success(request, f"Contrat avec « {prestataire} » ajouté.")

        return redirect('contrats')

    liste_contrats = Contrat.objects.all()

    context = {
        'contrats': liste_contrats,
        'type_choices': Contrat.TYPE_CHOICES,
        'aujourdhui': date.today(),
    }
    return render(request, 'machines/contrats.html', context)


@login_required
@bloquer_pour_role('chef_equipe', 'production', 'technicien')  # Idem : dépend de Contrats
def supprimer_contrat(request, id_contrat):
    """Supprime un contrat (et son document associé, voir le signal
    pre_delete dans machines/models.py) depuis l'onglet Contrats."""
    contrat = get_object_or_404(Contrat, id=id_contrat)

    if request.method == 'POST':
        prestataire = contrat.prestataire
        contrat.delete()
        messages.success(request, f"Contrat avec « {prestataire} » supprimé.")

    return redirect('contrats')


@login_required
@bloquer_pour_role('chef_equipe', 'production', 'technicien')  # Idem : dépend de Contrats
def telecharger_contrat_document(request, id_contrat):
    """Sert le document (PDF/image) d'un contrat. Passe par une vue plutôt
    que par une URL /media/ publique, pour rester derrière @login_required
    et bloquer_pour_role comme le reste de l'onglet Budget (voir MEDIA_URL
    dans settings.py)."""
    contrat = get_object_or_404(Contrat, id=id_contrat)
    if not contrat.document:
        raise Http404("Ce contrat n'a pas de document associé.")

    return FileResponse(
        contrat.document.open('rb'),
        as_attachment=False,
        filename=contrat.document.name.rsplit('/', 1)[-1],
    )
