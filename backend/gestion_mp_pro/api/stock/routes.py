"""Routes du domaine « Stock et lots » (API-PRO § 1.12 : routes 103–113 ; § 1.24 : 236).

Routes minces : chemin, droits, schémas, `summary` ; un appel de service. La route 114
(`GET /documents/etiquettes`) est rendue par le lot D9 (`api/documents`) à partir de
`services.lots_lecture.etiquettes`.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import date
from typing import Annotated

from fastapi import Depends, Query, Response

from gestion_mp_pro.api.communs import encoder_curseur, nouveau_routeur
from gestion_mp_pro.api.dependances import (
    DateReferenceDep,
    PaginationDep,
    SessionDep,
    borner_date,
)
from gestion_mp_pro.api.erreurs import Refus, reponses
from gestion_mp_pro.api.stock.schemas import (
    ControleSoldes,
    EtatStock,
    FicheStockMatiere,
    LotDisponible,
    LotFiche,
    LotModification,
    LotResume,
    LotSolde,
    MouvementLigne,
    PageMouvements,
    Tracabilite,
)
from gestion_mp_pro.exports import stock as classeurs
from gestion_mp_pro.exports.flux import classeur_en_flux
from gestion_mp_pro.modeles.enums import DocumentMouvement, TypeMouvement
from gestion_mp_pro.securite import A, C, D, QuiDep, droit
from gestion_mp_pro.services import (
    horloge,
    lots,
    lots_fiche,
    lots_lecture,
    mouvements,
    stock_lecture,
    tracabilite,
)

routeur = nouveau_routeur("stock")

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
Q = Annotated[str, Query(max_length=200, description="mots, sans accents")]


def _xlsx(contenu: bytes, prefixe: str) -> Response:
    """Un classeur à télécharger."""
    nom = classeurs.nom_de_fichier(prefixe, horloge.aujourd_hui())
    return Response(
        contenu, media_type=XLSX, headers={"Content-Disposition": f'attachment; filename="{nom}"'}
    )


@routeur.get(
    "/stock",
    response_model=EtatStock,
    dependencies=[droit(*C)],
    summary="L'état du stock à une date : une ligne par matière (tous les champs du moteur).",
    responses=reponses(401, 403, 422),
)
def etat(jour: DateReferenceDep, qui: QuiDep, s: SessionDep, q: Q = "") -> EtatStock:
    """Route 103 : sans prix, montants ni conseil d'achat pour l'alimentation."""
    e = stock_lecture.etat(s, jour, q, conseil=qui.voit_prix)
    return EtatStock.model_validate(asdict(e))


@routeur.get(
    "/stock/{matiere_id}",
    response_model=FicheStockMatiere,
    dependencies=[droit(*C)],
    summary="La fiche de stock d'une matière : sa ligne, d'où vient son besoin, ses lots.",
    responses=reponses(401, 403, 404, 422),
)
def fiche_matiere(
    matiere_id: int, jour: DateReferenceDep, qui: QuiDep, s: SessionDep
) -> FicheStockMatiere:
    """Route 104."""
    f = stock_lecture.fiche_matiere(s, matiere_id, jour, conseil=qui.voit_prix)
    return FicheStockMatiere.model_validate(asdict(f))


def filtres_mouvements(
    *,
    q: Q = "",
    matiere: Annotated[int | None, Query(ge=1)] = None,
    lot: Annotated[int | None, Query(ge=1)] = None,
    magasin: Annotated[int | None, Query(ge=1)] = None,
    type: TypeMouvement | None = None,
    document: DocumentMouvement | None = None,
    du: date | None = None,
    au: date | None = None,
) -> mouvements.FiltresMouvements:
    """Les filtres du journal du stock, partagés avec son export (106)."""
    return mouvements.FiltresMouvements(q, matiere, lot, magasin, type, document, du, au)


FiltresDep = Annotated[mouvements.FiltresMouvements, Depends(filtres_mouvements)]


def _curseur(pagination: PaginationDep) -> tuple[date, int] | None:
    """(date d'effet, n°) de la dernière ligne rendue."""
    if not pagination.apres:
        return None
    try:
        jour, ident = pagination.apres
        return date.fromisoformat(str(jour)), int(str(ident))
    except (ValueError, TypeError) as exc:
        raise Refus.saisie(
            "Curseur de pagination illisible : recharger la liste.", code="curseur_invalide"
        ) from exc


@routeur.get(
    "/mouvements",
    response_model=PageMouvements,
    dependencies=[droit(*C)],
    summary="Le journal du stock, filtré, le plus récent d'abord, par pages.",
    responses=reponses(401, 403, 422),
)
def lister_mouvements(
    f: FiltresDep,
    pagination: PaginationDep,
    qui: QuiDep,
    s: SessionDep,
    avec_valeur: bool = False,
) -> PageMouvements:
    """Route 105 : `avec_valeur` ajoute le coût unitaire et la valeur (MAD) de chaque ligne."""
    page = mouvements.lister(s, f, _curseur(pagination), pagination.limite, avec_valeur)
    return PageMouvements(
        elements=[_mouvement(asdict(x), qui.voit_prix) for x in page.lignes],
        total=page.total,
        suivant=encoder_curseur([page.dernier[0], page.dernier[1]]) if page.dernier else None,
        types=mouvements.types_presents(s, f),
    )


@routeur.get(
    "/export/mouvements",
    dependencies=[droit(*C)],
    summary="Le journal du stock en classeur (mêmes filtres ; sans prix pour l'alimentation).",
    responses={**reponses(401, 403, 422), 200: {"content": {XLSX: {}}}},
    response_class=Response,
)
def exporter_mouvements(
    f: FiltresDep, qui: QuiDep, s: SessionDep, avec_valeur: bool = True
) -> Response:
    """Route 106 : rendu **en flux** (V4 § 6), les lignes écrites une à une sans tout charger."""
    lignes = mouvements.tous_en_flux(s, f, avec_valeur and qui.voit_prix)
    return classeur_en_flux(
        "Mouvements", classeurs.COLONNES_MOUVEMENTS, lignes, qui.voit_prix, "mouvements"
    )


def filtres_lots(
    *,
    q: Q = "",
    matiere: Annotated[int | None, Query(ge=1)] = None,
    magasin: Annotated[int | None, Query(ge=1)] = None,
    statut: Annotated[
        str | None, Query(pattern="^(disponible|partiel|quarantaine|epuise)$")
    ] = None,
    non_nuls: bool = True,
    jour: Annotated[date | None, Query(alias="date")] = None,
) -> lots.FiltresLots:
    """Les filtres de la liste des lots, partagés avec son export (236)."""
    return lots.FiltresLots(
        matiere_id=matiere, magasin_id=magasin, statut=statut, non_nuls=non_nuls, q=q,
        jour=borner_date(jour) if jour is not None else None,
    )  # fmt: skip


FiltresLotsDep = Annotated[lots.FiltresLots, Depends(filtres_lots)]


@routeur.get(
    "/lots",
    response_model=list[LotSolde],
    dependencies=[droit(*C)],
    summary="Les lots et leurs soldes par magasin, avec leur statut et leur histoire.",
    responses=reponses(401, 403, 422),
)
def lister_lots(f: FiltresLotsDep, s: SessionDep) -> list[LotSolde]:
    """Route 107 (`date` passée : ce que chaque lot pouvait donner ce jour-là)."""
    return [LotSolde.model_validate(asdict(x)) for x in lots.lister(s, f)]


@routeur.get(
    "/export/lots",
    dependencies=[droit(*C)],
    summary="La liste des lots en classeur (mêmes filtres que la liste).",
    responses={**reponses(401, 403, 422), 200: {"content": {XLSX: {}}}},
    response_class=Response,
)
def exporter_lots(f: FiltresLotsDep, qui: QuiDep, s: SessionDep) -> Response:
    """Route 236."""
    return _xlsx(classeurs.lots(lots.lister(s, f), qui.voit_prix), "lots")


@routeur.get(
    "/lots/scan",
    response_model=list[LotResume],
    dependencies=[droit(*C)],
    summary="Le lot d'une étiquette scannée (adresse …/lot/123) ou d'un numéro tapé.",
    responses=reponses(401, 403, 404, 422),
)
def scanner(
    code: Annotated[str, Query(min_length=1, max_length=300)], s: SessionDep
) -> list[LotResume]:
    """Route 110 : un même numéro peut exister pour deux matières (liste) ; 404 si aucun."""
    trouves = lots_lecture.scan(s, code)
    if not trouves:
        raise Refus.introuvable("Lot introuvable.")
    return [LotResume.model_validate(asdict(x)) for x in trouves]


@routeur.get(
    "/lots/disponibles",
    response_model=list[LotDisponible],
    dependencies=[droit(*C)],
    summary="Les lots d'une matière qu'on peut sortir à une date, hors quarantaine, FIFO.",
    responses=reponses(401, 403, 422),
)
def disponibles(
    matiere: Annotated[int, Query(ge=1)],
    jour: DateReferenceDep,
    s: SessionDep,
    magasin: Annotated[int | None, Query(ge=1)] = None,
) -> list[LotDisponible]:
    """Route 111."""
    return [
        LotDisponible.model_validate(asdict(x))
        for x in lots_lecture.disponibles(s, matiere, magasin, jour)
    ]


@routeur.get(
    "/lots/{lot_id}",
    response_model=LotFiche,
    dependencies=[droit(*C)],
    summary="Tout d'un lot : soldes, statut, histoire, réception, journal, commentaire.",
    responses=reponses(401, 403, 404),
)
def fiche_lot(lot_id: int, qui: QuiDep, s: SessionDep) -> LotFiche:
    """Route 108."""
    return _fiche(lots_fiche.fiche(s, lot_id), qui.voit_prix)


def _mouvement(ligne: dict[str, object], voit_prix: bool) -> MouvementLigne:
    """Une écriture du journal ; sans devise hors direction et achats (an. 27, RESTES3 : le
    filtre des prix retire prix et cours, la devise restait)."""
    return MouvementLigne.model_validate(ligne if voit_prix else ligne | {"devise": None})


def _fiche(f: lots_fiche.LotFiche, voit_prix: bool) -> LotFiche:
    """La fiche à plat : la ligne du lot et ce qui s'y ajoute (journal sans devise pour qui ne
    voit pas les prix)."""
    donnees = asdict(f)
    donnees["mouvements"] = [_mouvement(x, voit_prix) for x in donnees["mouvements"]]
    return LotFiche.model_validate(donnees.pop("ligne") | donnees)


@routeur.put(
    "/lots/{lot_id}",
    response_model=LotFiche,
    dependencies=[droit(D, A)],
    summary="Modifier le commentaire d'un lot (avec la version lue).",
    responses=reponses(401, 403, 404, 409, 422),
)
def modifier_lot(lot_id: int, corps: LotModification, qui: QuiDep, s: SessionDep) -> LotFiche:
    """Route 109."""
    fiche = lots_fiche.modifier_commentaire(s, qui, lot_id, corps.commentaire, corps.version)
    return _fiche(fiche, qui.voit_prix)


@routeur.get(
    "/tracabilite",
    response_model=Tracabilite,
    dependencies=[droit(*C)],
    summary="Le chemin de la matière : d'un lot, d'un ordre de fabrication, d'une matière.",
    responses=reponses(401, 403, 404, 422),
)
def tracer(
    s: SessionDep,
    lot: Annotated[int | None, Query(ge=1)] = None,
    ordre: Annotated[int | None, Query(ge=1)] = None,
    matiere: Annotated[int | None, Query(ge=1)] = None,
) -> Tracabilite:
    """Route 112."""
    t = tracabilite.tracabilite(s, lot_id=lot, ordre_id=ordre, matiere_id=matiere)
    return Tracabilite.model_validate(asdict(t))


@routeur.get(
    "/controles/soldes",
    response_model=ControleSoldes,
    dependencies=[droit(D, A)],
    summary="Les soldes tenus égalent-ils le journal du stock ? Aucun n'est négatif ?",
    responses=reponses(401, 403),
)
def controle_soldes(s: SessionDep) -> ControleSoldes:
    """Route 113."""
    return ControleSoldes.model_validate(asdict(mouvements.controler_soldes(s)))
