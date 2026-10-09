"""Routes du domaine « Inventaires » (API-PRO § 1.14 : routes 124–133, 245 ; § 1.24 : 239, 240).

Routes minces : chemin, droits, schémas, `summary` ; un appel de service. La feuille de comptage
(133) est servie ici, sur l'environnement commun des documents (lot D9, `documents.rendu`).
"""

from __future__ import annotations

from dataclasses import asdict
from decimal import Decimal
from typing import Annotated

from fastapi import Query, Response
from fastapi.responses import HTMLResponse

from gestion_mp_pro.api.communs import ValidationVersion, nouveau_routeur
from gestion_mp_pro.api.dependances import SessionDep
from gestion_mp_pro.api.erreurs import reponses
from gestion_mp_pro.api.inventaires.schemas import (
    Comptages,
    DefautsInventaire,
    GesteMotive,
    InventaireFiche,
    InventaireOuverture,
    InventaireResume,
    LotTrouveEntree,
    MatiereACompter,
)
from gestion_mp_pro.documents import rendu
from gestion_mp_pro.exports import inventaires as classeurs
from gestion_mp_pro.exports.classeur import REPONSES_XLSX
from gestion_mp_pro.exports.classeur import reponse as reponse_xlsx
from gestion_mp_pro.modeles.enums import StatutInventaire
from gestion_mp_pro.securite import A, C, D, QuiDep, droit
from gestion_mp_pro.services import horloge
from gestion_mp_pro.services import inventaires as service
from gestion_mp_pro.services.inventaires import feuille as feuilles
from gestion_mp_pro.services.inventaires.lecture import InventaireLu

routeur = nouveau_routeur("inventaires")

ECRITURE = reponses(401, 403, 404, 409, 422)


def _decimal(valeur: float | None) -> Decimal | None:
    return None if valeur is None else Decimal(str(valeur))


def _fiche(lu: InventaireLu) -> InventaireFiche:
    return InventaireFiche.model_validate(asdict(lu))


@routeur.get(
    "/inventaires",
    response_model=list[InventaireResume],
    dependencies=[droit(*C)],
    summary="Les inventaires (ouverts, validés, abandonnés, annulés), les plus récents d'abord.",
    responses=reponses(401, 403, 422),
)
def lister(s: SessionDep, statut: StatutInventaire | None = None) -> list[InventaireResume]:
    """Route 124 (montants masqués pour l'alimentation)."""
    return [InventaireResume.model_validate(asdict(x)) for x in service.liste(s, statut)]


@routeur.get(
    "/inventaires/defauts",
    response_model=DefautsInventaire,
    dependencies=[droit(D, A)],
    summary="Ce que propose l'ouverture : tolérance, rôles et compositions en stock, cadences.",
    responses=reponses(401, 403),
)
def defauts(s: SessionDep) -> DefautsInventaire:
    """Route 125."""
    return DefautsInventaire.model_validate(asdict(service.defauts(s)))


@routeur.get(
    "/inventaires/a-compter",
    response_model=list[MatiereACompter],
    dependencies=[droit(D, A)],
    summary="L'inventaire tournant : les matières à recompter selon leur classe ABC.",
    responses=reponses(401, 403, 422),
)
def a_compter(
    s: SessionDep, magasin: Annotated[int | None, Query(ge=1)] = None
) -> list[MatiereACompter]:
    """Route 126 (par magasin : un comptage ne vaut que pour le magasin compté)."""
    return [MatiereACompter.model_validate(asdict(x)) for x in service.a_compter(s, magasin)]


@routeur.get(
    "/inventaires/{ident}",
    response_model=InventaireFiche,
    dependencies=[droit(*C)],
    summary="Un inventaire : périmètre, lignes, écarts en kilos et en dirhams, blocages.",
    responses=reponses(401, 403, 404),
)
def lire(ident: int, s: SessionDep) -> InventaireFiche:
    """Route 127."""
    return _fiche(service.fiche(s, ident))


@routeur.post(
    "/inventaires",
    response_model=InventaireFiche,
    status_code=201,
    dependencies=[droit(D, A)],
    summary="Ouvre un inventaire : numéro, théorique figé, mouvements du périmètre suspendus.",
    responses=reponses(401, 403, 409, 422),
)
def ouvrir(e: InventaireOuverture, qui: QuiDep, s: SessionDep) -> InventaireFiche:
    """Route 128."""
    c = e.criteres
    i = service.ouvrir(
        s,
        qui,
        service.Ouverture(
            date=e.date,
            magasin_id=e.magasin_id,
            libelle=e.libelle,
            tolerance=_decimal(e.tolerance),
            criteres=service.Criteres(
                tuple(c.matieres), tuple(c.roles), tuple(c.compositions), tuple(c.classes_abc)
            ),
        ),
    )
    return _fiche(service.fiche(s, i.id))


@routeur.put(
    "/inventaires/{ident}/comptages",
    response_model=InventaireFiche,
    dependencies=[droit(D, A)],
    summary="Enregistre des comptages (un champ absent ne change rien ; `null` le vide).",
    responses=ECRITURE,
)
def compter(ident: int, e: Comptages, qui: QuiDep, s: SessionDep) -> InventaireFiche:
    """Route 129."""
    comptages = [
        service.Comptage(
            x.ligne_id,
            {
                champ: (_decimal(valeur) if champ != "justification" else valeur)
                for champ, valeur in x.model_dump(exclude_unset=True).items()
                if champ != "ligne_id"
            },
        )
        for x in e.lignes
    ]
    service.compter(s, qui, ident, e.version, comptages)
    return _fiche(service.fiche(s, ident))


@routeur.post(
    "/inventaires/{ident}/lots-trouves",
    response_model=InventaireFiche,
    dependencies=[droit(D, A)],
    summary="Ajoute un lot trouvé sur place (le lot n'est créé qu'à la validation).",
    responses=ECRITURE,
)
def lot_trouve(ident: int, e: LotTrouveEntree, qui: QuiDep, s: SessionDep) -> InventaireFiche:
    """Route 130."""
    trouve = service.LotTrouve(
        matiere_id=e.matiere_id,
        magasin_id=e.magasin_id,
        lot_numero=e.lot_numero,
        lot_interne=e.lot_interne,
        compte=_decimal(e.compte),
        palettes=_decimal(e.palettes),
        bobines=_decimal(e.bobines),
        justification=e.justification,
    )
    service.lot_trouve(s, qui, ident, e.version, trouve)
    return _fiche(service.fiche(s, ident))


@routeur.post(
    "/inventaires/{ident}/valider",
    response_model=InventaireFiche,
    dependencies=[droit(D, A)],
    summary="Valide un inventaire : un ajustement par écart, daté du jour de l'inventaire.",
    responses=ECRITURE,
)
def valider(ident: int, e: ValidationVersion, qui: QuiDep, s: SessionDep) -> InventaireFiche:
    """Route 131."""
    service.valider(s, qui, ident, e.version)
    return _fiche(service.fiche(s, ident))


@routeur.post(
    "/inventaires/{ident}/abandonner",
    response_model=InventaireFiche,
    dependencies=[droit(D, A)],
    summary="Abandonne un inventaire en cours : rien n'est ajusté, il garde son numéro.",
    responses=ECRITURE,
)
def abandonner(ident: int, e: GesteMotive, qui: QuiDep, s: SessionDep) -> InventaireFiche:
    """Route 132."""
    service.abandonner(s, qui, ident, e.version, e.motif)
    return _fiche(service.fiche(s, ident))


@routeur.post(
    "/inventaires/{ident}/annuler",
    response_model=InventaireFiche,
    dependencies=[droit(D, A)],
    summary="Annule un inventaire validé : ses ajustements sont contre-passés, une fois.",
    responses=ECRITURE,
)
def annuler(ident: int, e: GesteMotive, qui: QuiDep, s: SessionDep) -> InventaireFiche:
    """Route 245."""
    service.annuler(s, qui, ident, e.version, e.motif)
    return _fiche(service.fiche(s, ident))


@routeur.get(
    "/documents/inventaires/{ident}/feuille",
    response_class=HTMLResponse,
    dependencies=[droit(*C)],
    summary="La feuille de comptage à imprimer (à l'aveugle), ou de recomptage.",
    responses={**reponses(401, 403, 404, 422), **rendu.REPONSES_HTML},
)
def feuille(
    ident: int, s: SessionDep, recomptage: bool = False, theorique: bool = False
) -> HTMLResponse:
    """Route 133 : A4 paysage, une page par magasin, papier à en-tête."""
    f = feuilles.feuille(s, ident, recomptage=recomptage, theorique=theorique)
    html = rendu.rendre(
        "feuille_comptage.html", societe=rendu.societe(s), titre=f.titre, paysage=True, feuille=f
    )
    return rendu.reponse(html)


@routeur.get(
    "/export/inventaires",
    response_class=Response,
    dependencies=[droit(D, A)],
    summary="Le classeur des inventaires (filtrés par état).",
    responses={**reponses(401, 403, 422), **REPONSES_XLSX},
)
def exporter(qui: QuiDep, s: SessionDep, statut: StatutInventaire | None = None) -> Response:
    """Route 239 : mêmes filtres que la liste (124)."""
    jour = horloge.aujourd_hui()
    contenu = classeurs.liste(service.liste(s, statut), qui.voit_prix, jour, statut or "")
    return reponse_xlsx(contenu, "inventaires", jour)


@routeur.get(
    "/export/inventaires/{ident}",
    response_class=Response,
    dependencies=[droit(D, A)],
    summary="Le classeur d'un inventaire : ses lignes, écarts en kilos et en dirhams.",
    responses={**reponses(401, 403, 404), **REPONSES_XLSX},
)
def exporter_lignes(ident: int, qui: QuiDep, s: SessionDep) -> Response:
    """Route 240."""
    lu = service.fiche(s, ident)
    jour = horloge.aujourd_hui()
    return reponse_xlsx(classeurs.lignes(lu, qui.voit_prix, jour), lu.numero.lower(), jour)
