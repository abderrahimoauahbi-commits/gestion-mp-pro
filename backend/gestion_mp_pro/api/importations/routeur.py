"""Le routeur du domaine « Importations » et les filtres de ses listes : la liste des dossiers
et son classeur (187, 205), l'analyse du coût de revient et son classeur (206, 208) prennent
chacune la **même dépendance de filtres** (filtres = écran)."""

from __future__ import annotations

from dataclasses import asdict
from datetime import date
from typing import Annotated

from fastapi import Depends, Query

from gestion_mp_pro.api.communs import nouveau_routeur
from gestion_mp_pro.api.dependances import SessionDep
from gestion_mp_pro.api.erreurs import reponses
from gestion_mp_pro.api.importations.schemas_fiche import DossierFiche
from gestion_mp_pro.services.analyse_revient import FiltresAnalyse
from gestion_mp_pro.services.importations.fiche import fiche
from gestion_mp_pro.services.importations.lecture import FiltresDossiers

routeur = nouveau_routeur("importations")

GESTE = reponses(401, 403, 404, 409, 422)
"""Les refus possibles d'un geste sur un dossier."""


def fiche_relue(s: SessionDep, did: int) -> DossierFiche:
    """La fiche relue après un geste (la session ne s'écrit pas d'elle-même : `autoflush=False`)."""
    s.flush()
    return DossierFiche.model_validate(asdict(fiche(s, did)))


TEXTE = Query(max_length=200, description="mots, sans accents")
CRITERE = Query(max_length=80)


def filtres_dossiers(
    statut: Annotated[str, Query(pattern="^(ouvert|clos|annule)?$")] = "",
    q: Annotated[str, TEXTE] = "",
    fournisseur: Annotated[int | None, Query(ge=1)] = None,
) -> FiltresDossiers:
    """`?statut=&q=&fournisseur=` (route 187 et son classeur 205) ; sans statut : ouverts et
    clos."""
    return FiltresDossiers(statut, q, fournisseur)


def filtres_analyse(
    *,
    axe: Annotated[str, Query(max_length=20)] = "reference",
    q: Annotated[str, TEXTE] = "",
    statut: Annotated[str, Query(max_length=20, description="ouvert ou clos")] = "",
    du: date | None = None,
    au: date | None = None,
    qualite: Annotated[int | None, Query(ge=1, description="les fils de sa recette")] = None,
    matieres: Annotated[list[int] | None, Query(description="identifiants")] = None,
    selection: Annotated[str, Query(max_length=4000, description="combinaisons, en JSON")] = "",
    composition: Annotated[str, CRITERE] = "",
    type_fil: Annotated[str, CRITERE] = "",
    titrage: Annotated[str, CRITERE] = "",
    couleur: Annotated[str, CRITERE] = "",
    fournisseur: Annotated[str, Query(max_length=120, description="nom")] = "",
    detail: bool = False,
) -> FiltresAnalyse:
    """`?axe=&q=&statut=&du=&au=&qualite=&matieres=&selection=&composition=&type_fil=&
    titrage=&couleur=&fournisseur=&detail=` (route 206 et son classeur 208)."""
    return FiltresAnalyse(
        axe=axe,
        q=q,
        statut=statut,
        du=du,
        au=au,
        qualite=qualite,
        matieres=tuple(matieres or ()),
        selection=selection,
        composition=composition,
        type_fil=type_fil,
        titrage=titrage,
        couleur=couleur,
        fournisseur=fournisseur,
        detail=detail,
    )


FiltresDossiersDep = Annotated[FiltresDossiers, Depends(filtres_dossiers)]
FiltresAnalyseDep = Annotated[FiltresAnalyse, Depends(filtres_analyse)]
