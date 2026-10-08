"""Pilotage : coût matière annuel et Cockpit (CALCULS B § 3).

Portage de `moteur.cout_matiere_annuel`, `cockpit`, `_concentration_devises` (méthode
corrigée). Le Cockpit de Gestion MP était un dict ; ici des dataclasses aux mêmes clés
(`cockpit_valeurs.py`).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from gestion_mp_pro.calcul.achats import montant_ligne_mad, pas_partie, reste_a_livrer
from gestion_mp_pro.calcul.constantes import (
    JOURS_PAR_AN,
    MOIS,
    MONO_SOURCE,
    STATUTS,
    STATUTS_EN_ALERTE,
)
from gestion_mp_pro.calcul.modele import Donnees
from gestion_mp_pro.calcul.nomenclature import nomenclature
from gestion_mp_pro.calcul.opportunites import opportunites
from gestion_mp_pro.calcul.outils import debut_de_mois
from gestion_mp_pro.calcul.pilotage_valeurs import (
    AchatsCockpit,
    AlerteCockpit,
    Cockpit,
    DormantCockpit,
    EconomiesCockpit,
    ExpositionDevise,
    FinanceCockpit,
    StockCockpit,
    Valeurs,
    valeurs_du_stock,
)
from gestion_mp_pro.calcul.plan import plan_mensuel
from gestion_mp_pro.calcul.prix import CoutDate
from gestion_mp_pro.calcul.stock import LigneStock
from gestion_mp_pro.calcul.valorisation import CoutsDuJournal, couts_du_journal

NOMBRE_D_ALERTES = 24
"""La liste des alertes s'arrête aux 24 plus pressées (le nombre réel est dit à part)."""
TOP_ECONOMIES = 5


def cout_matiere_annuel(donnees: Donnees, date_ref: date) -> float:
    """`Cockpit!J54` : Σ coût/m² de la qualité × m² annuels planifiés."""
    plan = plan_mensuel(donnees, date_ref)
    cout_par_qualite: dict[str, float] = defaultdict(float)
    for ligne in nomenclature(donnees):
        cout_par_qualite[ligne.qualite] += ligne.cout_m2_mad
    return sum(cout_par_qualite.get(q, 0.0) * sum(m2) for q, m2 in plan.items())


def _rotation(
    donnees: Donnees, date_ref: date, journal: CoutsDuJournal, v: Valeurs, cout_annuel: float
) -> tuple[str, float, float]:
    """(base, stock, coût annuel) du DIO : la consommation réelle des douze derniers mois clos
    au CMUP face au stock au CMUP ; sans historique, le plan et le stock au catalogue."""
    fin_conso = debut_de_mois(date_ref) - timedelta(days=1)
    debut_conso = debut_de_mois(date_ref, -MOIS)
    consomme = sum(val for jour, val in journal.consommation if debut_conso <= jour <= fin_conso)
    premiere = min((m.date for m in donnees.mouvements), default=None)
    if consomme > 0 and premiere is not None and premiere <= fin_conso:
        jours_conso = (fin_conso - max(debut_conso, premiere)).days + 1
        return "consommation", v.stock, consomme / jours_conso * JOURS_PAR_AN
    return "plan", v.stock_catalogue, cout_annuel


def _engagements(donnees: Donnees, date_ref: date) -> tuple[int, float, float, float]:
    """(bons actifs, reste à livrer en MAD, dont estimé, DPO) ; un brouillon ou un bon annulé
    n'engage rien ; le DPO se pondère par le reçu des douze derniers mois (E-09)."""
    parametres = donnees.parametres
    commandes = [c for c in donnees.commandes if not pas_partie(c) and c.statut != "Annulée"]
    bc_actifs, reste_bc, reste_estime = 0, 0.0, 0.0
    for commande in commandes:
        restes = [(x, reste_a_livrer(commande, x, parametres)) for x in commande.lignes]
        if any(reste > 0 for _, reste in restes):
            bc_actifs += 1
        for x, reste in restes:
            montant = montant_ligne_mad(x, reste, parametres)
            reste_bc += montant
            if not x.prix_confirme:
                reste_estime += montant
    montants: dict[str, float] = defaultdict(float)
    depuis = date_ref - timedelta(days=JOURS_PAR_AN)
    for prix in donnees.historique_prix:
        if prix.date_bc is not None and depuis < prix.date_bc <= date_ref:
            montants[prix.fournisseur] += (
                prix.quantite * prix.prix_achat * parametres.taux(prix.devise)
            )
    return bc_actifs, reste_bc, reste_estime, _dpo(donnees, montants)


def _dpo(donnees: Donnees, montants: dict[str, float]) -> float:
    total = sum(montants.values())
    if total:
        return (
            sum(
                (f.delai_paiement_jours if (f := donnees.fournisseur(nom)) else 0) * montant
                for nom, montant in montants.items()
            )
            / total
        )
    delais = [f.delai_paiement_jours for f in donnees.fournisseurs if f.delai_paiement_jours > 0]
    return sum(delais) / len(delais) if delais else 0.0


def _alerte(x: LigneStock) -> AlerteCockpit:
    return AlerteCockpit(
        reference=x.reference,
        nature=x.nature,
        designation=x.designation,
        fournisseur=x.fournisseur,
        stock=x.stock_projete,
        conso_mensuelle=x.conso_mensuelle,
        couverture_jours=x.couverture_jours,
        delai_jours=x.delai_jours,
        quantite_a_commander=x.quantite_a_commander,
        statut=x.statut,
        statut_couverture=x.statut_couverture,
        action=x.action,
        titrage=" ".join(v for v in (x.titrage, x.titrage_unite) if v),
        kg_par_ml=x.kg_par_ml,
        stock_machine=x.stock_machine,
    )


def concentration_devises(lignes_stock: list[LigneStock]) -> list[ExpositionDevise]:
    """`Cockpit` zone 6 : l'exposition au change du budget d'achat à émettre."""
    par_devise: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0])
    total = 0.0
    for ligne in lignes_stock:
        if ligne.quantite_a_commander <= 0:
            continue
        bloc = par_devise[ligne.devise]
        bloc[0] += 1
        bloc[1] += ligne.montant_a_commander_mad
        total += ligne.montant_a_commander_mad
    return [
        ExpositionDevise(
            devise=devise,
            references=int(bloc[0]),
            montant_mad=bloc[1],
            part=bloc[1] / total if total else 0.0,
        )
        for devise, bloc in sorted(par_devise.items(), key=lambda kv: -kv[1][1])
    ]


def _stock(lignes: list[LigneStock], v: Valeurs) -> StockCockpit:
    def _compte(cle: str) -> int:
        return sum(1 for x in lignes if x.statut == STATUTS[cle])

    return StockCockpit(
        valeur_mad=v.stock,
        valeur_machine_mad=v.machine,
        nb_references=len(lignes),
        nb_detenues=v.nb_detenues,
        nb_sur_metiers=sum(1 for x in lignes if x.stock_machine > 0),
        couverture_ponderee_jours=v.couverture_ponderee,
        ruptures=_compte("RUPTURE"),
        critiques=_compte("CRITIQUE"),
        urgents=_compte("URGENT"),
        attentions=_compte("ATTENTION"),
        ok=_compte("OK"),
        sans_consommation=_compte("SANS_CONSO"),
    )


def _finance(
    dso: float, cout_annuel: float, rotation: tuple[str, float, float], dpo: float
) -> FinanceCockpit:
    base, valeur_rotation, cout_rotation = rotation
    dio = valeur_rotation / (cout_rotation / JOURS_PAR_AN) if cout_rotation else 0.0
    return FinanceCockpit(
        cout_matiere_annuel_mad=cout_annuel,
        cout_matiere_mensuel_mad=cout_annuel / MOIS,
        rotation_stock=cout_rotation / valeur_rotation if valeur_rotation else 0.0,
        dio_jours=dio,
        cout_rotation_annuel_mad=cout_rotation,
        base_rotation=base,
        dso_jours=dso,
        dpo_jours=dpo,
        ccc_jours=dio + dso - dpo,
    )


def cockpit(
    donnees: Donnees,
    date_ref: date,
    lignes_stock: list[LigneStock],
    couts: dict[str, list[CoutDate]] | None = None,
    meme_couleur: bool = False,
) -> Cockpit:
    """La vue 🚨 Cockpit sur les matières réelles ; `couts` : le coût rendu de chaque achat
    pour les opportunités ; toutes les routes de Gestion MP passent `meme_couleur=True`."""
    parametres = donnees.parametres
    journal = couts_du_journal(donnees)
    v = valeurs_du_stock(donnees, lignes_stock, journal)
    cout_annuel = cout_matiere_annuel(donnees, date_ref)
    base, valeur_rotation, cout_rotation = _rotation(donnees, date_ref, journal, v, cout_annuel)
    bc_actifs, reste_bc, reste_estime, dpo = _engagements(donnees, date_ref)
    economies = opportunites(donnees, lignes_stock, meme_couleur=meme_couleur, couts=couts)
    alertes = sorted(
        [x for x in lignes_stock if x.statut in STATUTS_EN_ALERTE],
        key=lambda x: x.couverture_jours if x.couverture_jours is not None else 0,
    )
    return Cockpit(
        date_reference=date_ref.isoformat(),
        stock=_stock(lignes_stock, v),
        achats=AchatsCockpit(
            bc_actifs=bc_actifs,
            montant_bc_en_cours_mad=reste_bc,
            montant_bc_estime_mad=reste_estime,
            fournisseurs_actifs=sum(1 for f in donnees.fournisseurs if f.actif),
            budget_a_commander_mad=sum(
                x.montant_a_commander_mad for x in lignes_stock if x.quantite_a_commander > 0
            ),
        ),
        finance=_finance(parametres.dso, cout_annuel, (base, valeur_rotation, cout_rotation), dpo),
        abc={c: sum(1 for x in lignes_stock if x.classe_abc == c) for c in "ABC"},
        dormant=DormantCockpit(
            nb_references=v.nb_dormantes,
            valeur_mad=v.dormante,
            part_valeur=v.dormante / v.stock if v.stock else 0.0,
            seuil_jours=parametres.seuil_dormant,
        ),
        sourcing={
            "mono_source": sum(1 for x in lignes_stock if x.sourcing == MONO_SOURCE),
            "multi_source": sum(1 for x in lignes_stock if x.sourcing.startswith("✅")),
        },
        economies=EconomiesCockpit(
            total_mad=sum(o.economie_mad for o in economies),
            nb_opportunites=len(economies),
            top=economies[:TOP_ECONOMIES],
        ),
        nb_alertes=len(alertes),
        alertes=[_alerte(x) for x in alertes[:NOMBRE_D_ALERTES]],
        devises=concentration_devises(lignes_stock),
    )
