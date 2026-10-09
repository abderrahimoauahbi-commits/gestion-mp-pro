"""Le fil monté sur les métiers : règles, poids, effet, alerte 30 j, événement (REGLES A § 1.11).

Le fil monté est du stock « sur les métiers » (décision de Mohamed, U8) : compté dans le stock
global, sa valeur, le disponible et le projeté. **Monter n'écrit aucun mouvement** : le fil a
déjà été sorti par un ordre (ARCHITECTURE T1). Chaque montage confirmé s'écrit dans
`montage_evenement` (avant, après, effet, alerte) et au journal (« montage »).

- Poids d'un fil = mètres × bobines par mètre du métier × part / 100 × poids d'une bobine
  retenu (pesé au lot : le dernier sorti vers les machines, sinon le dernier reçu ; à défaut
  le catalogue — M43). Un métier arrêté ne compte pas (0).
- L'effet annoncé à l'écran est **confirmé** (`confirme_effet_kg`) : si le calcul du serveur en
  diffère de plus de 0,05 kg (un poids de bobine pesé entre-temps, un autre étage monté), 409
  `effet_change` : l'écran relit l'effet et redemande.
- Alerte : une matière dont le poids sur les métiers en service dépasse 1,1 × ce qui est parti
  aux machines en 30 jours (sorties nettes des retours) + 1 kg.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import Matiere, Metier, Montage, Mouvement, RoleNomenclature
from gestion_mp_pro.modeles.enums import TypeMouvement
from gestion_mp_pro.modeles.types import LONGUEUR, POURCENTAGE, QUANTITE, arrondir
from gestion_mp_pro.services import donnees_moteur, horloge
from gestion_mp_pro.services.conversions import kg

CENT = Decimal(100)
JOURS_SORTIES = 30
MARGE_ALERTE = Decimal("1.1")
PLANCHER_ALERTE = Decimal(1)
TOLERANCE_EFFET = Decimal("0.05")
LONGUEUR_ALERTE = 300


@dataclass(frozen=True)
class Fil:
    """Un fil monté (ou à monter) : étage, matière, mètres, part de l'étage, observations."""

    etage: int
    matiere_id: int
    metres: Decimal
    pourcentage: Decimal = CENT
    commentaire: str = ""

    def arrondi(self) -> Fil:
        """Le fil à l'échelle de ses colonnes."""
        return Fil(
            self.etage,
            self.matiere_id,
            arrondir(self.metres, LONGUEUR),
            arrondir(self.pourcentage, POURCENTAGE),
            self.commentaire,
        )

    @property
    def largeur(self) -> Decimal:
        """La largeur occupée : mètres × part (deux fils à 60 et 40 % sur 4 m en occupent 4)."""
        return self.metres * self.pourcentage / CENT


@dataclass(frozen=True)
class Reglage:
    """Ce qui, d'un métier, compte pour un montage."""

    code: str
    laize: Decimal
    bobines_par_metre: Decimal
    etages: int
    actif: bool

    @classmethod
    def de(cls, x: Metier) -> Reglage:
        """Le réglage d'un métier en base."""
        return cls(x.code, x.laize, x.bobines_par_metre, x.etages, x.actif)


@dataclass(frozen=True)
class Bobine:
    """Le poids d'une bobine retenu pour une matière, et d'où il vient."""

    poids: Decimal
    source: str


def fils_du_metier(s: Session, metier_id: int) -> list[Fil]:
    """Le montage d'un métier, étage par étage."""
    requete = (
        select(Montage).where(Montage.metier_id == metier_id).order_by(Montage.etage, Montage.id)
    )
    return [
        Fil(f.etage, f.matiere_id, f.metres, f.pourcentage, f.commentaire)
        for f in s.scalars(requete)
    ]


def charger_matieres(s: Session, ids: Iterable[int]) -> dict[int, Matiere]:
    """Les matières citées, par id."""
    return {m.id: m for m in s.scalars(select(Matiere).where(Matiere.id.in_(list(ids))))}


def bobines(s: Session, matieres: Iterable[Matiere]) -> dict[int, Bobine]:
    """Le poids d'une bobine retenu de chaque matière (M43) : pesé au lot, sinon catalogue."""
    pesees = donnees_moteur.poids_bobine_mesures(s)
    resultat = {}
    for m in matieres:
        poids, lot, genre = pesees.get(m.id, (0.0, "", ""))
        if poids:
            resultat[m.id] = Bobine(Decimal(str(poids)), f"lot {lot} ({genre})")
        else:
            resultat[m.id] = Bobine(m.poids_bobine, "catalogue" if m.poids_bobine else "")
    return resultat


def bobines_du_fil(f: Fil, r: Reglage) -> Decimal:
    """Les bobines d'un fil : mètres × bobines par mètre × part."""
    return f.metres * r.bobines_par_metre * f.pourcentage / CENT


def peser(fils: Iterable[Fil], r: Reglage, poids: dict[int, Bobine]) -> Decimal:
    """Ce que pèsent ces fils sur ce métier, comme le compte le stock (0 s'il est arrêté)."""
    if not r.actif:
        return Decimal(0)
    return sum((bobines_du_fil(f, r) * poids[f.matiere_id].poids for f in fils), start=Decimal(0))


def verifier(s: Session, r: Reglage, fils: Sequence[Fil]) -> dict[int, Matiere]:
    """Les règles d'un montage (X-REF-68 à X-REF-73) ; rend les matières citées."""
    ids = {f.matiere_id for f in fils}
    matieres = {m.id: m for m in s.scalars(select(Matiere).where(Matiere.id.in_(ids)))}
    roles = {x.id: x for x in s.scalars(select(RoleNomenclature))}
    vus: set[tuple[int, int]] = set()
    largeur: dict[int, Decimal] = defaultdict(Decimal)
    for f in fils:
        m = matieres.get(f.matiere_id)
        if m is None:
            raise Refus.saisie("Matière inconnue.", code="valeur_inconnue")
        role = roles[m.role_id]
        if role.lineaire:
            raise Refus.saisie(
                f"« {m.reference} » ({role.code}) se pose au mètre linéaire : elle ne se monte "
                "pas en bobines sur un métier."
            )
        if f.etage > r.etages:
            raise Refus.saisie(f"Étage {f.etage} : ce métier n'en a que {r.etages}.")
        if (f.etage, f.matiere_id) in vus:
            raise Refus.saisie(
                f"« {m.reference} » est monté deux fois à l'étage {f.etage}.",
                code="ligne_en_double",
            )
        if f.metres <= 0:
            raise Refus.saisie(f"« {m.reference} » à l'étage {f.etage} : saisir les mètres montés.")
        vus.add((f.etage, f.matiere_id))
        largeur[f.etage] += f.largeur
    trop = sorted(n for n, metres in largeur.items() if r.laize and metres > r.laize)
    if trop:
        n = trop[0]
        raise Refus.saisie(
            f"Étage {n} : {texte(largeur[n])} m montés (mètres × part de chaque fil) pour une "
            f"laize de {texte(r.laize)} m."
        )
    return matieres


def texte(valeur: Decimal) -> str:
    """« 4,5 » : le nombre court, à la française."""
    return f"{valeur.normalize():f}".replace(".", ",")


def pas_d_ajout(
    r: Reglage, avant: Sequence[Fil], apres: Sequence[Fil], matieres: dict[int, Matiere]
) -> None:
    """Sur un métier arrêté, ou d'une matière désactivée, on démonte (retirer, réduire) mais
    on ne monte pas : ce fil disparaîtrait du stock (D-12)."""
    deja: dict[tuple[int, int], Decimal] = defaultdict(Decimal)
    for f in avant:
        deja[(f.etage, f.matiere_id)] += f.largeur
    for f in apres:
        if f.largeur <= deja.get((f.etage, f.matiere_id), Decimal(0)):
            continue
        if not r.actif:
            raise Refus.etat(
                f"Le métier {r.code} est arrêté : le remettre en service avant d'y monter du fil."
            )
        m = matieres[f.matiere_id]
        if not m.actif:
            raise Refus.etat(
                f"« {m.reference} » est désactivée : la réactiver (Catalogue) avant de la monter.",
                code="fiche_inactive",
            )


def sorties_recentes(s: Session) -> dict[int, Decimal]:
    """Les kilos partis aux machines ces 30 derniers jours, retours déduits, par matière."""
    depuis = horloge.aujourd_hui() - timedelta(days=JOURS_SORTIES)
    requete = (
        select(Mouvement.matiere_id, func.sum(Mouvement.quantite))
        .where(
            Mouvement.type.in_((TypeMouvement.SORTIE, TypeMouvement.RETOUR_MACHINE)),
            Mouvement.date_effet >= depuis,
        )
        .group_by(Mouvement.matiere_id)
    )
    return {matiere: -quantite for matiere, quantite in s.execute(requete)}


def montes_ailleurs(s: Session, metier_id: int) -> tuple[list[tuple[Fil, Reglage]], set[int]]:
    """Les fils des **autres** métiers en service, avec leur réglage, et leurs matières."""
    autres = {
        x.id: Reglage.de(x)
        for x in s.scalars(select(Metier).where(Metier.actif.is_(True), Metier.id != metier_id))
    }
    fils = [
        (Fil(f.etage, f.matiere_id, f.metres, f.pourcentage), autres[f.metier_id])
        for f in s.scalars(select(Montage).where(Montage.metier_id.in_(list(autres))))
    ]
    return fils, {f.matiere_id for f, _ in fils}


def alertes(
    s: Session,
    metier_id: int,
    r: Reglage,
    *,
    apres: Sequence[Fil],
    touches: Sequence[Fil],
    matieres: dict[int, Matiere],
) -> list[str]:
    """Les matières des étages montés dont le poids sur les métiers dépasse ce qui est parti
    aux machines en 30 jours (1,1 × sorti + 1 kg)."""
    ailleurs, ids = montes_ailleurs(s, metier_id)
    toutes = charger_matieres(s, ids)
    poids = bobines(s, [*matieres.values(), *toutes.values()])
    total: dict[int, Decimal] = defaultdict(Decimal)
    for f, reglage in ailleurs:
        total[f.matiere_id] += peser([f], reglage, poids)
    for f in apres:
        total[f.matiere_id] += peser([f], r, poids)
    sorti = sorties_recentes(s)
    resultat = []
    for mid in dict.fromkeys(f.matiere_id for f in touches):
        parti = sorti.get(mid, Decimal(0))
        if total[mid] > MARGE_ALERTE * parti + PLANCHER_ALERTE:
            resultat.append(
                f"{matieres[mid].reference} : {kg(total[mid], 1)} kg sur les métiers pour "
                f"{kg(parti, 1)} kg partis aux machines en {JOURS_SORTIES} jours : vérifier "
                "qu'il est bien sorti par un ordre avant de le monter."
            )
    return resultat


def confirmer(effet: Decimal, confirme: Decimal) -> None:
    """L'effet calculé doit être celui que l'écran a annoncé (409 `effet_change`)."""
    if abs(effet - confirme) > TOLERANCE_EFFET:
        raise Refus.etat(
            "L'effet du montage sur le stock a changé depuis son calcul : sur les métiers "
            f"{signe(effet)} kg au lieu de {signe(confirme)} kg annoncés. Relire l'effet puis "
            "confirmer de nouveau.",
            code="effet_change",
        )


def signe(valeur: Decimal) -> str:
    """« +40,0 », « −3,5 » : un écart signé, à la française."""
    return ("+" if valeur >= 0 else "−") + kg(abs(valeur), 1)


def message(r: Reglage, avant: Decimal, apres: Decimal) -> str:
    """Le texte unique « sur les métiers » d'un montage confirmé (ECRANS-PRO partie 3, (a))."""
    if not r.actif:
        return "Métier arrêté : rien n'est compté sur lui."
    if abs(apres - avant) < TOLERANCE_EFFET:
        return "Le stock sur les métiers ne change pas."
    return (
        "Monter n'écrit aucun mouvement : ce fil est déjà sorti par un ordre. Le stock sur les "
        f"métiers passe de {kg(avant, 1)} à {kg(apres, 1)} kg ({signe(apres - avant)} kg) ; il "
        "compte dans le stock global, sa valeur, le disponible et le projeté."
    )


def lignes_json(
    fils: Sequence[Fil], r: Reglage, matieres: dict[int, Matiere], poids: dict[int, Bobine]
) -> list[dict[str, object]]:
    """Les lignes d'un étage pour l'historique (`montage_evenement.avant/apres`)."""
    return [
        {
            "etage": f.etage,
            "matiere_id": f.matiere_id,
            "reference": matieres[f.matiere_id].reference,
            "metres": float(f.metres),
            "pourcentage": float(f.pourcentage),
            "commentaire": f.commentaire,
            "kg": float(arrondir(peser([f], r, poids), QUANTITE)),
        }
        for f in fils
    ]


def detail_journal(
    code: str, etages: Sequence[int], fils: Sequence[Fil], refs: dict[int, Matiere],
    *, avant: Decimal, apres: Decimal,
) -> str:  # fmt: skip
    """« M1, étage 2 : étage 2 POIL 1,5 m (50 %) — sur les métiers 40,0 → 55,0 kg (+15,0 kg) »."""
    quoi = (
        f", étage {etages[0]}"
        if len(etages) == 1
        else ", étages " + ", ".join(str(n) for n in etages)
    )
    lignes = ", ".join(
        f"étage {f.etage} {refs[f.matiere_id].reference} {texte(f.metres)} m"
        + (f" ({texte(f.pourcentage)} %)" if f.pourcentage != CENT else "")
        for f in fils
    )
    return (
        f"{code}{quoi} : {lignes or 'vide'} — sur les métiers {kg(avant, 1)} → {kg(apres, 1)} kg "
        f"({signe(apres - avant)} kg)"
    )
