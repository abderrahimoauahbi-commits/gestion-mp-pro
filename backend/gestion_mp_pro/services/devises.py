"""Devises et cours de change (routes 27–30 ; héritage K70–K73, E-02, E-13).

- Un cours dit combien de MAD vaut une unité ; le dirham vaut toujours 1 et reste en service.
- Un cours n'est historisé (`devise_cours`) que s'il **change** : renommer ou mettre hors service
  ne fait pas croire à un nouveau cours (E-13).
- **Un mois clos ne se revalorise pas** (E-02, V3) : avant qu'un cours change, les marchandises
  des dossiers d'importation ouverts entrées dans la période close, sans cours de banque,
  prennent le cours d'avant le changement (noté sur la ligne) ; la clôture d'une période fige de
  même le cours du jour (`figer_a_la_cloture`, branché sur `periode.APRES_CLOTURE`).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import (
    Devise,
    DeviseCours,
    Dossier,
    DossierLigne,
    Lot,
    Reception,
    ReceptionLigne,
    Utilisateur,
)
from gestion_mp_pro.modeles import longueurs as L
from gestion_mp_pro.modeles.enums import ObjetJournal, OrigineCours, StatutDossier
from gestion_mp_pro.modeles.types import COURS, arrondir
from gestion_mp_pro.services import audit, horloge, periode

DIRHAM = "MAD"
CODE_DEVISE = re.compile(r"[A-Za-z]{3}")


@dataclass(frozen=True)
class CoursSaisi:
    """Un cours de l'historique d'une devise, et sa variation sur le précédent (fraction)."""

    id: int
    cours: Decimal
    saisi_le: datetime
    par: str
    variation: float | None


def lisible(cours: Decimal) -> str:
    """« 10,85 » (virgule, sans zéros inutiles)."""
    return f"{cours.normalize():f}".replace(".", ",")


def code_valide(brut: str) -> str:
    """Trois lettres, en capitales (« usd » → USD)."""
    code = brut.strip()
    if not CODE_DEVISE.fullmatch(code):
        raise Refus.saisie(
            "Le code d'une devise s'écrit en trois lettres (EUR, USD, CNY…).",
            champs={"code": "trois lettres"},
        )
    return code.upper()


def lister(s: Session) -> tuple[list[Devise], set[str]]:
    """Les devises triées par code, et celles dont le cours n'a jamais été saisi (repris)."""
    devises = list(s.scalars(select(Devise).order_by(Devise.code)))
    saisis = set(s.scalars(select(DeviseCours.devise).distinct()))
    return devises, {d.code for d in devises if d.code not in saisis}


def devise(s: Session, code: str, *, verrou: bool = False) -> Devise:
    """Une devise par son code (404 sinon)."""
    trouvee = s.get(Devise, code.strip().upper()[: L.CODE_DEVISE], with_for_update=verrou)
    if trouvee is None:
        raise Refus.introuvable("Devise introuvable.")
    return trouvee


def cours_successifs(
    s: Session, code: str, apres: int | None, limite: int
) -> tuple[list[CoursSaisi], int, int | None]:
    """Les cours d'une devise, du plus récent ; la variation se lit sur le cours d'avant."""
    d = devise(s, code)
    total = int(s.scalar(select(func.count()).where(DeviseCours.devise == d.code)) or 0)
    requete = (
        select(DeviseCours, Utilisateur.nom)
        .outerjoin(Utilisateur, Utilisateur.id == DeviseCours.par_id)
        .where(DeviseCours.devise == d.code)
        .order_by(DeviseCours.id.desc())
    )
    if apres is not None:
        requete = requete.where(DeviseCours.id < apres)
    lignes = s.execute(requete.limit(limite + 2)).all()
    page = []
    for i, (c, nom) in enumerate(lignes[:limite]):
        precedent = lignes[i + 1][0].cours if i + 1 < len(lignes) else None
        variation = float(c.cours / precedent - 1) if precedent else None
        page.append(CoursSaisi(c.id, c.cours, c.saisi_le, nom or audit.SYSTEME, variation))
    return page, total, (page[-1].id if len(lignes) > limite else None)


def _cours(valeur: float | Decimal) -> Decimal:
    """Un cours à l'échelle de sa colonne, strictement positif."""
    cours = arrondir(valeur, COURS)
    if cours <= 0:
        raise Refus.saisie("Le cours doit être positif.", champs={"cours": "positif"})
    return cours


def _regle_du_dirham(code: str, cours: Decimal, actif: bool) -> None:
    """Le dirham est la référence : cours 1, toujours en service (KR50, E-13)."""
    if code != DIRHAM:
        return
    if cours != 1:
        raise Refus.saisie(
            "Le dirham est la devise de référence : son cours reste 1.", champs={"cours": "1"}
        )
    if not actif:
        raise Refus.saisie(
            "Le dirham est la devise de référence : il reste en service.",
            champs={"actif": "en service"},
        )


def _noter_cours(s: Session, qui: audit.Qui, d: Devise, avant: Decimal | None) -> None:
    """Le nouveau cours : historique, date du cours, journal « cours de change »."""
    instant = horloge.maintenant()
    s.add(DeviseCours(devise=d.code, cours=d.cours, saisi_le=instant, par_id=qui.id))
    d.cours_le = instant
    audit.journal(
        s,
        qui,
        "cours de change",
        ObjetJournal.devise,
        numero=d.code,
        detail=f"{d.code} : {lisible(d.cours)} MAD",
        avant={"cours": float(avant)} if avant is not None else None,
        apres={"cours": float(d.cours)},
    )


def creer(s: Session, qui: audit.Qui, code: str, nom: str, cours: float) -> Devise:
    """Une devise nouvelle et son premier cours (route 29)."""
    code = code_valide(code)
    valeur = _cours(cours)
    _regle_du_dirham(code, valeur, True)
    if s.get(Devise, code) is not None:
        raise Refus.etat(f"La devise « {code} » existe déjà.", code="doublon")
    d = Devise(code=code, nom=nom.strip(), cours=valeur, actif=True)
    s.add(d)
    s.flush()
    _noter_cours(s, qui, d, None)
    s.flush()
    return d


def modifier(
    s: Session, qui: audit.Qui, code: str, *, nom: str, cours: float, actif: bool, version: int
) -> Devise:
    """Nom, cours, mise en service (route 30) : un cours n'est historisé que s'il change."""
    d = devise(s, code, verrou=True)
    audit.verifier_version(s, d, version, "Cette devise")
    valeur = _cours(cours)
    _regle_du_dirham(d.code, valeur, actif)
    nom = nom.strip() or d.nom
    if valeur != d.cours:
        avant = d.cours
        figees = figer_cours_periode_close(s, qui, code=d.code, ancien=avant)
        d.cours = valeur
        _noter_cours(s, qui, d, avant)
        _journal_figees(s, qui, figees, f"{d.code} : ", f"gardent {lisible(avant)} MAD")
    if (nom, actif) != (d.nom, d.actif):
        with audit.suivre(s, qui, "devise", d, numero=d.code) as geste:
            d.nom, d.actif = nom, actif
            geste.detail = f"{d.code} : {d.nom}" + ("" if d.actif else " (hors service)")
    s.flush()
    return d


def _journal_figees(s: Session, qui: audit.Qui, n: int, debut: str, fin: str) -> None:
    """Une ligne « cours figé » quand des marchandises ont gardé leur cours."""
    if n:
        audit.journal(
            s,
            qui,
            "cours figé",
            ObjetJournal.devise,
            detail=f"{debut}{n} marchandise(s) de dossiers ouverts entrées en période close {fin}",
        )


def entrees_ouvertes(s: Session, jusqu_au: date) -> list[DossierLigne]:
    """Les marchandises des dossiers ouverts entrées au plus tard ce jour (leur coût bouge encore).

    L'entrée est la réception de la ligne, sinon l'entrée de son lot, sinon l'arrivée du dossier.
    """
    entree = func.coalesce(Reception.date, Lot.entre_le, Dossier.date_arrivee)
    requete = (
        select(DossierLigne)
        .join(Dossier, Dossier.id == DossierLigne.dossier_id)
        .outerjoin(ReceptionLigne, ReceptionLigne.id == DossierLigne.reception_ligne_id)
        .outerjoin(Reception, Reception.id == ReceptionLigne.reception_id)
        .outerjoin(Lot, Lot.id == DossierLigne.lot_id)
        .where(Dossier.statut == StatutDossier.ouvert, entree <= jusqu_au)
        .order_by(DossierLigne.id)
        .with_for_update(of=DossierLigne)
    )
    return list(s.scalars(requete))


def figer_cours_periode_close(
    s: Session,
    qui: audit.Qui,
    *,
    code: str | None = None,
    ancien: Decimal | None = None,
    jusqu_au: date | None = None,
    geste: str = "au changement",
) -> int:
    """Fige le cours des marchandises sans cours entrées dans la période close (E-02).

    `code` : une seule devise (son cours d'avant le changement : `ancien`) ; sinon toutes, au
    cours du jour. Rend le nombre de marchandises figées.
    """
    limite = jusqu_au or periode.fin_de_periode_close(s)
    if limite is None or code == DIRHAM:
        return 0
    cours = {d.code: d.cours for d in s.scalars(select(Devise))}
    note = f"cours figé {geste} du {horloge.aujourd_hui():%d/%m/%Y}"
    n = 0
    for ligne in entrees_ouvertes(s, limite):
        if ligne.devise == DIRHAM or ligne.cours is not None or (code and ligne.devise != code):
            continue
        taux = ancien if code and ancien else cours.get(ligne.devise)
        if not taux:
            continue
        ligne.cours, ligne.cours_origine = taux, OrigineCours.saisi
        texte = f"{ligne.commentaire} · {note}" if ligne.commentaire else note
        ligne.commentaire = texte[: L.COMMENTAIRE]
        n += 1
    return n


def figer_a_la_cloture(s: Session, qui: audit.Qui, jour: date) -> None:
    """À la clôture d'une période : les marchandises encore en dossier ouvert gardent leur cours."""
    n = figer_cours_periode_close(s, qui, jusqu_au=jour, geste="à la clôture")
    _journal_figees(s, qui, n, "", f"jusqu'au {jour:%d/%m/%Y} gardent leur cours du jour")


if figer_a_la_cloture not in periode.APRES_CLOTURE:
    periode.APRES_CLOTURE.append(figer_a_la_cloture)
