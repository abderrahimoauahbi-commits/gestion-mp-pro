"""Lire, écrire et historiser les réglages (routes 23–25 ; héritage K60–K66, REGLAGES § 2).

- `lire(s, role)` : les réglages tels que le rôle les voit (l'administrateur : la famille
  technique seule), avec la `version` de chaque ligne et la `version_globale` (Σ des versions).
- `ecrire(s, qui, valeurs, version_globale)` : tout ou rien. Clés connues, nombres finis et
  bornés, textes ≤ 500, courriels et adresse publique contrôlés, seuils dans l'ordre (vérifiés
  sur l'état final, avant d'écrire), version globale à jour (409 sinon). Une valeur inchangée
  n'écrit rien ; chaque changement a sa ligne d'historique et son journal avant/après.
- `nombre(s, cle)`, `texte(s, cle)` : la lecture des autres domaines (défaut si vide).

`date_cloture` ne passe plus par ici (route 26, `services/periode.clore`, motif obligatoire) ;
`seuil_bc_urgent` est sans effet et ne se modifie plus (E-16).
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import Parametre, ParametreHistorique, Utilisateur
from gestion_mp_pro.modeles import longueurs as L
from gestion_mp_pro.modeles.enums import ObjetJournal, Role
from gestion_mp_pro.services import audit, horloge, periode
from gestion_mp_pro.services.comptes import message_refus
from gestion_mp_pro.services.registre_reglages import (
    ORDRES_LARGES,
    ORDRES_STRICTS,
    PAR_CLE,
    REGLAGES,
    Reglage,
)

TEXTE_MAX = 500
ADRESSE_MAX = 200
ADRESSE_COURRIEL = re.compile(r"[^@\s,;<>]+@[^@\s,;<>]+\.[^@\s,;<>]+")


@dataclass(frozen=True)
class ReglageLu:
    """Un réglage lu : sa déclaration, sa valeur en base (texte), sa version."""

    reglage: Reglage
    valeur: str
    version: int
    version_globale: int


def visibles(role: str) -> list[Reglage]:
    """Les réglages qu'un rôle lit : tous, sauf pour l'administrateur (famille technique)."""
    if role == Role.administrateur:
        return [r for r in REGLAGES if r.technique]
    return list(REGLAGES)


def version_globale(s: Session) -> int:
    """La somme des versions des réglages : elle change à chaque écriture d'un réglage."""
    return int(s.scalar(select(func.coalesce(func.sum(Parametre.version), 0))) or 0)


def lire(s: Session, role: str) -> list[ReglageLu]:
    """Les réglages visibles du rôle, dans l'ordre de l'écran (valeur en base, sinon défaut)."""
    lignes = {p.cle: p for p in s.scalars(select(Parametre))}
    globale = version_globale(s)
    lus = []
    for r in visibles(role):
        p = lignes.get(r.cle)
        valeur = p.valeur if p is not None else str(r.defaut)
        lus.append(ReglageLu(r, valeur, p.version if p is not None else 0, globale))
    return lus


def texte(s: Session, cle: str) -> str:
    """La valeur texte d'un réglage (défaut s'il manque)."""
    p = s.get(Parametre, cle)
    return p.valeur if p is not None else str(PAR_CLE[cle].defaut)


def nombre(s: Session, cle: str) -> float:
    """La valeur numérique d'un réglage : défaut si vide ou illisible (lecture des domaines)."""
    return _en_nombre(texte(s, cle), PAR_CLE[cle])


def _en_nombre(brut: str, r: Reglage) -> float:
    """Un texte rangé en nombre, sinon le défaut du réglage."""
    try:
        valeur = float(brut)
    except ValueError:
        return float(r.defaut)
    return valeur if math.isfinite(valeur) else float(r.defaut)


def _format_nombre(x: float) -> str:
    """« 0.05 », « 30 » (entier sans « .0 »), comme Gestion MP et les semences."""
    return str(int(x)) if x == int(x) else repr(x)


def _borne(x: float) -> str:
    """Une borne lisible (« 0.5 », « 1e+12 ») : le `:g` de Gestion MP."""
    return f"{x:g}"


def normaliser_nombre(r: Reglage, brut: object) -> str:
    """Un nombre saisi (virgule acceptée), fini et borné, en texte normalisé (KR31, KR32)."""
    try:
        valeur = float(str(brut).strip().replace(",", "."))
    except ValueError:
        valeur = math.nan
    if not math.isfinite(valeur):
        raise Refus.saisie(f"« {r.libelle} » attend un nombre.", champs={r.cle: "nombre attendu"})
    bas = r.bas if r.bas is not None else -math.inf
    haut = r.haut if r.haut is not None else math.inf
    if not bas <= valeur <= haut:
        raise Refus.saisie(
            f"« {r.libelle} » doit rester entre {_borne(bas * r.echelle)} et "
            f"{_borne(haut * r.echelle)} {r.unite} — reçu {_borne(valeur * r.echelle)}.",
            champs={r.cle: "hors des bornes"},
        )
    return _format_nombre(valeur)


def normaliser_texte(r: Reglage, brut: object) -> str:
    """Un texte saisi : adresse publique, courriels, longueur (KR35, KR36, E-15)."""
    valeur = str(brut).strip() if brut is not None else ""
    if r.cle == "adresse_publique" and valeur:
        if not (
            valeur.startswith(("http://", "https://"))
            and len(valeur) <= ADRESSE_MAX
            and " " not in valeur
        ):
            raise Refus.saisie(
                "L'adresse commence par http:// ou https:// (ex. http://mac-usine:8050).",
                champs={r.cle: "adresse invalide"},
            )
    elif len(valeur) > TEXTE_MAX:
        raise Refus.saisie(f"« {r.libelle} » : texte trop long.", champs={r.cle: "trop long"})
    elif r.cle == "courriel_destinataires" and valeur:
        adresses = [x.strip() for x in re.split(r"[,;]", valeur) if x.strip()]
        fausses = [x for x in adresses if not ADRESSE_COURRIEL.fullmatch(x)]
        if fausses:
            raise Refus.saisie(
                f"Adresse de courriel illisible : {', '.join(fausses)} "
                "(ex. direction@usine.ma, séparées par des virgules).",
                champs={r.cle: "adresse illisible"},
            )
        valeur = ", ".join(adresses)
    return valeur


def _verifier_cle(r: Reglage, role: str) -> None:
    """Une clé que ce rôle peut écrire par cette route."""
    if r.cle == "date_cloture":
        raise Refus.saisie(
            "« Période close jusqu'au » se règle par la clôture de période (Réglages › Période "
            "close), avec un motif.",
            champs={r.cle: "réglé par la clôture de période"},
        )
    if not r.modifiable:
        raise Refus.saisie(
            f"« {r.libelle} » est sans effet, gardé pour mémoire : il ne se modifie plus.",
            champs={r.cle: "lecture seule"},
        )
    if role == Role.administrateur and not r.technique:
        raise Refus.droit(message_refus(frozenset({Role.direction})))


def _verifier_version(s: Session, lue: int) -> None:
    """409 si un réglage a changé depuis la lecture (auteur et heure du dernier changement)."""
    if lue == version_globale(s):
        return
    dernier = s.scalars(select(ParametreHistorique).order_by(ParametreHistorique.id.desc())).first()
    nom, heure = "un autre poste", "à l'instant"
    if dernier is not None:
        par = s.get(Utilisateur, dernier.par_id) if dernier.par_id is not None else None
        nom, heure = (par.nom if par else audit.SYSTEME), audit.horodatage(dernier.quand)
    raise Refus.etat(
        f"Les réglages ont été modifiés entre-temps par {nom} ({heure}) : rouvrez-les pour "
        "repartir de leur dernière version.",
        code="conflit_version",
    )


def _verifier_ordres(final: Mapping[str, str]) -> None:
    """Des seuils qui se contredisent vident une catégorie sans le dire (K65)."""
    for bas, haut, message in ORDRES_STRICTS:
        if _en_nombre(final[bas], PAR_CLE[bas]) >= _en_nombre(final[haut], PAR_CLE[haut]):
            raise Refus.saisie(message, champs={bas: "dans le désordre", haut: "dans le désordre"})
    for bas, haut, message in ORDRES_LARGES:
        if _en_nombre(final[bas], PAR_CLE[bas]) > _en_nombre(final[haut], PAR_CLE[haut]):
            raise Refus.saisie(message, champs={bas: "dans le désordre", haut: "dans le désordre"})


def lisible(valeur: str | None, r: Reglage | None = None) -> str:
    """« 9,5 », « 20 % », « — » pour vide (journal et historique, comme l'écran)."""
    if not valeur:
        return "—"
    try:
        x = float(valeur)
    except ValueError:
        return valeur
    if r is None or r.texte:
        return valeur.replace(".", ",")
    v = round(x * (r.echelle or 1), 6)
    chiffre = str(int(v)) if v == int(v) else f"{v:f}".rstrip("0").replace(".", ",")
    return f"{chiffre} {r.unite}" if r.unite else chiffre


def preparer(s: Session, role: str, valeurs: Mapping[str, object]) -> dict[str, str]:
    """Les valeurs reçues, contrôlées et normalisées (aucune écriture)."""
    inconnus = sorted(set(valeurs) - set(PAR_CLE))
    if inconnus:
        raise Refus.saisie(
            f"Paramètres inconnus : {', '.join(inconnus)}.",
            champs=dict.fromkeys(inconnus, "inconnu"),
        )
    nouvelles: dict[str, str] = {}
    for cle, brut in valeurs.items():
        r = PAR_CLE[cle]
        _verifier_cle(r, role)
        nouvelles[cle] = normaliser_texte(r, brut) if r.texte else normaliser_nombre(r, brut)
    return nouvelles


def ecrire(
    s: Session, qui: audit.Qui, valeurs: Mapping[str, object], version_lue: int
) -> list[str]:
    """Écrit un lot de réglages, tout ou rien ; rend les clés changées (route 24)."""
    nouvelles = preparer(s, qui.role, valeurs)
    lignes = {p.cle: p for p in s.scalars(select(Parametre).with_for_update())}
    _verifier_version(s, version_lue)
    final = {r.cle: (lignes[r.cle].valeur if r.cle in lignes else str(r.defaut)) for r in REGLAGES}
    final.update(nouvelles)
    _verifier_ordres(final)
    changees = []
    for cle, valeur in nouvelles.items():
        p = lignes.get(cle)
        if p is None or p.valeur == valeur:
            continue
        r, avant = PAR_CLE[cle], p.valeur
        instant: datetime = horloge.maintenant()
        s.add(ParametreHistorique(cle=cle, avant=avant, apres=valeur, quand=instant, par_id=qui.id))
        p.valeur, p.modifie_le, p.modifie_par_id = valeur, instant, qui.id
        audit.journal(
            s,
            qui,
            "paramètre",
            ObjetJournal.parametre,
            numero=cle[: L.NUMERO_DOCUMENT],
            detail=f"{r.libelle} : {lisible(avant, r)} → {lisible(valeur, r)}",
            avant={cle: avant},
            apres={cle: valeur},
        )
        changees.append(cle)
    s.flush()
    return changees


@dataclass(frozen=True)
class Changement:
    """Une ligne de l'historique des réglages (route 25)."""

    id: int
    cle: str
    libelle: str
    avant: str | None
    apres: str
    avant_lisible: str
    apres_lisible: str
    quand: datetime
    par: str
    motif: str


def historique(
    s: Session, role: str, cle: str | None, apres: int | None, limite: int
) -> tuple[list[Changement], int, int | None]:
    """Les changements, du plus récent ; rend (page, total, id du dernier rendu s'il en reste)."""
    cles = [r.cle for r in visibles(role)]
    if cle is not None:
        if cle not in PAR_CLE:
            raise Refus.saisie(f"Paramètres inconnus : {cle}.", champs={"cle": "inconnu"})
        cles = [c for c in cles if c == cle]
    filtre = ParametreHistorique.cle.in_(cles)
    total = int(s.scalar(select(func.count()).where(filtre)) or 0)
    requete = select(ParametreHistorique, Utilisateur.nom).outerjoin(
        Utilisateur, Utilisateur.id == ParametreHistorique.par_id
    )
    requete = requete.where(filtre).order_by(ParametreHistorique.id.desc())
    if apres is not None:
        requete = requete.where(ParametreHistorique.id < apres)
    lignes = s.execute(requete.limit(limite + 1)).all()
    page = [
        Changement(
            h.id,
            h.cle,
            PAR_CLE[h.cle].libelle,
            h.avant,
            h.apres,
            lisible(h.avant, PAR_CLE[h.cle]),
            lisible(h.apres, PAR_CLE[h.cle]),
            h.quand,
            nom or audit.SYSTEME,
            h.motif,
        )
        for h, nom in lignes[:limite]
    ]
    return page, total, (page[-1].id if len(lignes) > limite else None)


def clore_periode(
    s: Session, qui: audit.Qui, jour: date | None, motif: str, version: int
) -> periode.Periode:
    """Clôt ou rouvre la période (route 26) : version de la clôture lue, puis `periode.clore`."""
    p = s.get(Parametre, periode.CLE, with_for_update=True)
    if p is None:
        raise Refus.introuvable("Réglage introuvable.")
    audit.verifier_version(s, p, version, "La période close")
    return periode.clore(s, qui, jour, motif)


def version_cloture(s: Session) -> int:
    """La version du réglage de clôture (à renvoyer avec la prochaine clôture)."""
    p = s.get(Parametre, periode.CLE)
    return p.version if p is not None else 0
