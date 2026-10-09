"""Le coût de revient des matières importées (routes 206–208) : par axe, par critères, lot par
lot, et le coût d'une qualité pondéré par sa recette (REGLES R-IMP-56 à R-IMP-61).

Le calcul est celui du moteur (`calcul/analyse_revient*.py`, porté à l'identique de Gestion MP) ;
ce service traduit les filtres de l'écran (qualité et matières par **identifiant**) et rend les
refus à la convention PRO : 422 (axe, sélection, statut inconnus — plus de 400, défaut B-09) et
404 (qualité inconnue ou sans recette), en phrases françaises. Les dossiers annulés n'entrent
jamais dans le calcul (le chargeur ne les lit pas).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.calcul.analyse_revient import (
    AnalyseRevient,
    FiltresRevient,
    QualiteInconnue,
    analyse_revient,
)
from gestion_mp_pro.calcul.analyse_revient_qualite import AnalyseQualite, analyse_qualite
from gestion_mp_pro.modeles import Dossier, Matiere, Qualite, TypeFil
from gestion_mp_pro.modeles.enums import StatutDossier
from gestion_mp_pro.services import donnees_moteur


@dataclass(frozen=True)
class FiltresAnalyse:
    """Les filtres de la route 206 (et du classeur 208) : l'état de l'écran, dans l'adresse."""

    axe: str = "reference"
    q: str = ""
    statut: str = ""
    du: date | None = None
    au: date | None = None
    qualite: int | None = None
    matieres: tuple[int, ...] = ()
    selection: str = ""
    composition: str = ""
    type_fil: str = ""
    titrage: str = ""
    couleur: str = ""
    fournisseur: str = ""
    detail: bool = False


def phrase(message: str) -> str:
    """Un refus du moteur en phrase : majuscule, point final (API-PRO § 2)."""
    texte = message.strip()
    texte = texte[:1].upper() + texte[1:]
    return texte if texte.endswith((".", "»", ")")) else f"{texte}."


def _ids_dossiers(s: Session) -> dict[str, int]:
    """Le numéro de chaque dossier non annulé → son identifiant (lien vers sa fiche)."""
    requete = select(Dossier.numero, Dossier.id).where(Dossier.statut != StatutDossier.annule)
    return dict(s.execute(requete).all())


def _qualite(s: Session, ident: int | None) -> str:
    """Le code de la qualité choisie (404 si elle n'existe pas)."""
    if ident is None:
        return ""
    code = s.scalar(select(Qualite.code).where(Qualite.id == ident))
    if code is None:
        raise Refus.introuvable("Qualité introuvable.")
    return code


def _references(s: Session, ids: tuple[int, ...]) -> str:
    """Les références des matières choisies, séparées par « ; » (422 pour une inconnue)."""
    if not ids:
        return ""
    requete = select(Matiere.id, Matiere.reference).where(Matiere.id.in_(ids))
    trouvees = dict(s.execute(requete).all())
    inconnues = sorted(set(ids) - set(trouvees))
    if inconnues:
        raise Refus.saisie(
            f"Matière inconnue : {', '.join(str(x) for x in inconnues)}.",
            code="valeur_inconnue",
            champs={"matieres": "inconnue"},
        )
    return ";".join(trouvees[x] for x in ids)


def analyser(s: Session, f: FiltresAnalyse) -> AnalyseRevient:
    """Ce que la matière importée a coûté, rendue usine (route 206)."""
    filtres = FiltresRevient(
        axe=f.axe,
        q=f.q,
        debut=f.du,
        fin=f.au,
        composition=f.composition,
        type_fil=f.type_fil,
        titrage=f.titrage,
        couleur=f.couleur,
        fournisseur=f.fournisseur,
        qualite=_qualite(s, f.qualite),
        statut=f.statut,
        references=_references(s, f.matieres),
        selection=f.selection,
        detail=f.detail,
    )
    types = dict(s.execute(select(TypeFil.code, TypeFil.libelle)).all())
    donnees = donnees_moteur.charger(s, avec_journal=False)
    try:
        return analyse_revient(donnees, filtres, types_fil=types, ids_dossiers=_ids_dossiers(s))
    except QualiteInconnue as refus:
        raise Refus.introuvable(phrase(str(refus))) from None
    except ValueError as refus:
        raise Refus.saisie(phrase(str(refus))) from None


def qualite(s: Session, ident: int, du: date | None, au: date | None) -> AnalyseQualite:
    """Le coût matière d'une qualité, pondéré par sa recette (route 207)."""
    code = _qualite(s, ident)
    donnees = donnees_moteur.charger(s, avec_journal=False)
    try:
        return analyse_qualite(donnees, code, debut=du, fin=au, ids_dossiers=_ids_dossiers(s))
    except QualiteInconnue as refus:
        raise Refus.introuvable(phrase(str(refus))) from None
