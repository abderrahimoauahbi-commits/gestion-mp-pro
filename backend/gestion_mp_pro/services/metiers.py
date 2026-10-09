"""Les gestes sur les métiers à tisser : réglage (96–98) et montage (97, 99, 100).

Le réglage (code, laize, bobines par mètre, étages, en service) appartient à la direction ;
le montage, à l'alimentation et à la direction. Le montage d'un étage est protégé par la
`version` de son étage (`metier_etage`) : deux téléphones sur le même étage, un seul passe ;
le réglage, par la `version` du métier. La direction enregistre réglage et fils dans une
seule transaction (route 97, `montage` facultatif). Règles et effet : `services/montage`.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import (
    Metier,
    MetierEtage,
    Montage,
    MontageEvenement,
    Ordre,
    Utilisateur,
)
from gestion_mp_pro.modeles.enums import ObjetJournal
from gestion_mp_pro.modeles.types import QUANTITE, arrondir
from gestion_mp_pro.services import audit, horloge
from gestion_mp_pro.services import montage as mt
from gestion_mp_pro.services.audit import Qui
from gestion_mp_pro.services.montage import Fil, Reglage

QUOI = "Ce métier"


@dataclass(frozen=True)
class FicheMetier:
    """Le réglage d'un métier tel que la direction le saisit."""

    code: str
    nom: str = ""
    laize: Decimal = Decimal("4.2")
    bobines_par_metre: Decimal = Decimal(0)
    etages: int = 6
    actif: bool = True
    commentaire: str = ""

    def reglage(self) -> Reglage:
        """Ce qui compte pour un montage."""
        return Reglage(self.code, self.laize, self.bobines_par_metre, self.etages, self.actif)


@dataclass(frozen=True)
class EtageMonte:
    """Le montage demandé pour un étage, avec la version de l'étage lue par l'écran."""

    etage: int
    version: int
    fils: Sequence[Fil]


@dataclass
class ResultatMontage:
    """Ce que le montage a fait au stock sur les métiers, et ce qu'il faut en dire."""

    metier: Metier
    effet_kg: Decimal = Decimal(0)
    avant_kg: Decimal = Decimal(0)
    apres_kg: Decimal = Decimal(0)
    alertes: list[str] = field(default_factory=list)
    message: str = ""


def verrouiller(s: Session, metier_id: int) -> Metier:
    """Le métier sous verrou de ligne (404 « Métier introuvable. »)."""
    x = s.get(Metier, metier_id, with_for_update=True, populate_existing=True)
    if x is None:
        raise Refus.introuvable("Métier introuvable.")
    return x


def _code_libre(s: Session, code: str, metier_id: int | None = None) -> None:
    """Deux métiers ne portent pas le même code (X-REF-59)."""
    requete = select(Metier.id).where(Metier.code == code)
    if metier_id is not None:
        requete = requete.where(Metier.id != metier_id)
    if s.scalar(requete) is not None:
        raise Refus.etat(f"Le métier « {code} » existe déjà.", code="doublon")


def _etages(s: Session, x: Metier) -> dict[int, MetierEtage]:
    """Les lignes d'étage d'un métier, relues (leur `version` est le verrou du montage)."""
    requete = (
        select(MetierEtage)
        .where(MetierEtage.metier_id == x.id)
        .execution_options(populate_existing=True)
    )
    return {e.etage: e for e in s.scalars(requete)}


def _ajuster_etages(s: Session, x: Metier, etages: int) -> None:
    """Une ligne `metier_etage` par étage, de 1 à `etages` (retirer un étage retire ses fils)."""
    existants = _etages(s, x)
    for n in range(1, etages + 1):
        if n not in existants:
            s.add(MetierEtage(metier_id=x.id, etage=n))
    s.execute(delete(MetierEtage).where(MetierEtage.metier_id == x.id, MetierEtage.etage > etages))
    s.flush()


def creer(s: Session, qui: Qui, f: FicheMetier) -> Metier:
    """Route 96 : le métier et ses étages."""
    _code_libre(s, f.code)
    x = Metier(
        code=f.code, nom=f.nom, laize=f.laize, bobines_par_metre=f.bobines_par_metre,
        etages=f.etages, actif=f.actif, commentaire=f.commentaire,
    )  # fmt: skip
    s.add(x)
    s.flush()
    _ajuster_etages(s, x, f.etages)
    audit.creation(s, qui, "création métier", x, detail=x.code)
    return x


def _verifier_reglage(f: FicheMetier, fils: Sequence[Fil]) -> None:
    """On ne ramène pas un métier sous ses fils (X-REF-62, X-REF-63)."""
    trop_haut = sorted({x.etage for x in fils if x.etage > f.etages})
    if trop_haut:
        raise Refus.saisie(
            f"Des fils sont montés à l'étage {trop_haut[-1]} : les retirer ou les déplacer "
            f"avant de ramener le métier à {f.etages} étage(s)."
        )
    largeur: dict[int, Decimal] = defaultdict(Decimal)
    for x in fils:
        largeur[x.etage] += x.largeur
    large = sorted(n for n, m in largeur.items() if f.laize and m > f.laize)
    if large:
        n = large[0]
        raise Refus.saisie(
            f"Étage {n} : {mt.texte(largeur[n])} m montés, plus que la laize de "
            f"{mt.texte(f.laize)} m demandée. Retirer d'abord du fil."
        )


def _verifier_etages(
    s: Session, x: Metier, demandes: Sequence[EtageMonte], etages: int
) -> dict[int, MetierEtage]:
    """Étages connus, une fois chacun, à la version lue (409 qui nomme l'auteur)."""
    lignes = _etages(s, x)
    vus: set[int] = set()
    for d in demandes:
        if d.etage in vus:
            raise Refus.saisie(
                f"L'étage {d.etage} figure deux fois dans le montage.", code="ligne_en_double"
            )
        vus.add(d.etage)
        ligne = lignes.get(d.etage)
        if ligne is None or d.etage > etages:
            raise Refus.introuvable(f"Étage {d.etage} : ce métier n'en a que {etages}.")
        if ligne.version != d.version:
            auteur = s.get(Utilisateur, ligne.monte_par_id) if ligne.monte_par_id else None
            nom = auteur.nom if auteur is not None else "un autre poste"
            heure = audit.horodatage(ligne.monte_le) if ligne.monte_le else "à l'instant"
            raise Refus.etat(
                f"L'étage {d.etage} a été modifié entre-temps par {nom} ({heure}) : "
                "rouvrez-le pour repartir de sa dernière version.",
                code="conflit_version",
            )
    return lignes


def _remplacer(avant: Sequence[Fil], demandes: Sequence[EtageMonte]) -> list[Fil]:
    """Le montage après : les étages demandés remplacés, les autres inchangés."""
    touches = {d.etage for d in demandes}
    nouveaux = [
        Fil(d.etage, f.matiere_id, f.metres, f.pourcentage, f.commentaire).arrondi()
        for d in demandes
        for f in d.fils
    ]
    return sorted([f for f in avant if f.etage not in touches] + nouveaux, key=lambda f: f.etage)


def _ecrire_montage(
    s: Session, qui: Qui, x: Metier, demandes: Sequence[EtageMonte], lignes: dict[int, MetierEtage]
) -> None:
    """Remplace les fils des étages demandés et fait monter la version de chacun."""
    touches = [d.etage for d in demandes]
    s.execute(delete(Montage).where(Montage.metier_id == x.id, Montage.etage.in_(touches)))
    for d in demandes:
        for f in d.fils:
            g = Fil(d.etage, f.matiere_id, f.metres, f.pourcentage, f.commentaire).arrondi()
            s.add(
                Montage(metier_id=x.id, etage=g.etage, matiere_id=g.matiere_id, metres=g.metres,
                        pourcentage=g.pourcentage, commentaire=g.commentaire)
            )  # fmt: skip
        ligne = lignes[d.etage]
        ligne.monte_le = horloge.maintenant()
        ligne.monte_par_id = qui.id
        flag_modified(ligne, "monte_par_id")
    s.flush()


def _monter(
    s: Session,
    qui: Qui,
    x: Metier,
    demandes: Sequence[EtageMonte],
    *,
    confirme: Decimal,
    avant: tuple[Reglage, list[Fil]],
    au_telephone: bool = False,
) -> ResultatMontage:
    """Vérifie, confirme l'effet, écrit le montage, l'événement et le journal.

    `avant` : le réglage et les fils d'avant le geste ; `x` porte déjà le réglage d'après.
    """
    r_avant, fils_avant = avant
    r = Reglage.de(x)
    lignes = _verifier_etages(s, x, demandes, r.etages)
    fils_apres = _remplacer(fils_avant, demandes)
    matieres = mt.verifier(s, r, fils_apres)
    touches = sorted({d.etage for d in demandes})
    avant_touches = [f for f in fils_avant if f.etage in touches]
    apres_touches = [f for f in fils_apres if f.etage in touches]
    matieres |= mt.charger_matieres(s, {f.matiere_id for f in fils_avant})
    mt.pas_d_ajout(r, avant_touches, apres_touches, matieres)
    poids = mt.bobines(s, matieres.values())
    effet = arrondir(
        mt.peser(fils_apres, r, poids) - mt.peser(fils_avant, r_avant, poids), QUANTITE
    )
    mt.confirmer(effet, confirme)
    alertes = mt.alertes(s, x.id, r, apres=fils_apres, touches=apres_touches, matieres=matieres)
    _ecrire_montage(s, qui, x, demandes, lignes)
    kg_avant = mt.peser(avant_touches, r_avant, poids)
    kg_apres = mt.peser(apres_touches, r, poids)
    for n in touches if au_telephone else [None]:  # origine : `etage` = téléphone (route 100)
        s.add(
            MontageEvenement(
                metier_id=x.id, etage=n, par_id=qui.id, effet_kg=effet,
                avant=mt.lignes_json(avant_touches, r_avant, matieres, poids),
                apres=mt.lignes_json(apres_touches, r, matieres, poids),
                alerte=" ; ".join(alertes)[: mt.LONGUEUR_ALERTE],
            )
        )  # fmt: skip
    detail = mt.detail_journal(
        x.code, touches, apres_touches, matieres, avant=kg_avant, apres=kg_apres
    )
    audit.journal(s, qui, "montage", ObjetJournal.metier, x.id, detail=detail)
    total_avant = _total_sur_les_metiers(s, x.id) + mt.peser(fils_avant, r_avant, poids)
    return ResultatMontage(
        x, effet, kg_avant, kg_apres, alertes,
        mt.message(r, total_avant, total_avant + effet),
    )  # fmt: skip


def _total_sur_les_metiers(s: Session, sauf: int) -> Decimal:
    """Ce que pèsent les fils des autres métiers en service (le stock sur les métiers)."""
    ailleurs, ids = mt.montes_ailleurs(s, sauf)
    poids = mt.bobines(s, mt.charger_matieres(s, ids).values())
    return sum((mt.peser([f], r, poids) for f, r in ailleurs), start=Decimal(0))


def monter(
    s: Session,
    qui: Qui,
    metier_id: int,
    demandes: Sequence[EtageMonte],
    confirme: Decimal,
    *,
    au_telephone: bool = False,
) -> ResultatMontage:
    """Routes 99 et 100 : le montage d'un ou de plusieurs étages (les autres ne bougent pas).

    `au_telephone` (route 100, un étage) : l'événement porte son étage, ce qui le dit
    « téléphone » dans l'historique (101) ; un montage du bureau (99, 97), même d'un seul étage,
    n'en porte pas (« bureau » : RESTES3, F3)."""
    x = verrouiller(s, metier_id)
    avant = (Reglage.de(x), mt.fils_du_metier(s, x.id))
    return _monter(s, qui, x, demandes, confirme=confirme, avant=avant, au_telephone=au_telephone)


def modifier(
    s: Session,
    qui: Qui,
    metier_id: int,
    f: FicheMetier,
    *,
    version: int,
    montage: tuple[Sequence[EtageMonte], Decimal] | None = None,
) -> ResultatMontage:
    """Route 97 : le réglage et, facultatif, le montage, dans une seule transaction."""
    x = verrouiller(s, metier_id)
    audit.verifier_version(s, x, version, QUOI, feminin=False)
    _code_libre(s, f.code, x.id)
    avant = (Reglage.de(x), mt.fils_du_metier(s, x.id))
    demandes = montage[0] if montage else []
    _verifier_reglage(f, _remplacer(avant[1], demandes))
    with audit.suivre(s, qui, "réglage métier", x, detail=f.code):
        x.code, x.nom, x.laize, x.bobines_par_metre = f.code, f.nom, f.laize, f.bobines_par_metre
        x.etages, x.actif, x.commentaire = f.etages, f.actif, f.commentaire
        s.flush()
    _ajuster_etages(s, x, max(f.etages, max((d.etage for d in demandes), default=0)))
    resultat = ResultatMontage(x)
    if montage:
        resultat = _monter(s, qui, x, demandes, confirme=montage[1], avant=avant)
    _ajuster_etages(s, x, f.etages)
    return resultat


def supprimer(s: Session, qui: Qui, metier_id: int, version: int) -> None:
    """Route 98 : sans fil monté (X-REF-64), jamais nommé par un ordre (X-REF-65)."""
    x = verrouiller(s, metier_id)
    audit.verifier_version(s, x, version, QUOI, feminin=False)
    fils = s.scalar(select(func.count()).select_from(Montage).where(Montage.metier_id == x.id))
    if fils:
        raise Refus.etat(
            f"« {x.code} » porte encore {fils} fil(s) : les retirer d'abord.",
            code="fiche_utilisee",
        )
    n = s.scalar(select(func.count()).select_from(Ordre).where(Ordre.metier_id == x.id))
    if n:
        raise Refus.etat(
            f"« {x.code} » est nommé par {n} ordre(s) de fabrication : il appartient à "
            "l'historique. L'arrêter plutôt que le supprimer.",
            code="fiche_utilisee",
        )
    audit.suppression(s, qui, "suppression métier", x, detail=x.code)
    s.execute(delete(MontageEvenement).where(MontageEvenement.metier_id == x.id))
    s.delete(x)
    s.flush()
