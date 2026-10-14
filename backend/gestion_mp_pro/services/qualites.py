"""Les gestes de la direction sur une qualité (routes 84–87, 89, 90 ; REGLES A § 1.7–1.9).

Chaque geste : verrou de la ligne de la qualité, `version` lue comparée (409 qui nomme
l'auteur), règles, écriture, version de recette si la recette ou les poids changent (D-04),
version du plan si le plan change, ligne de journal avec avant/après. La `version` de la
qualité monte à chaque geste qui touche sa fiche, ses poids, sa recette ou son plan : c'est
la version de **tout** ce que l'écran a lu.

Poids au m² : remplacement complet (un rôle absent vaut 0) ; un poids nul n'est pas
enregistré (P7-5). Un rôle pesant sans matière : refusé pour une qualité en service dont la
recette est commencée, averti sinon (D-05).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import (
    OrdreQualite,
    PlanVersion,
    Qualite,
    QualitePoids,
    Recette,
    RecetteVersion,
)
from gestion_mp_pro.modeles.enums import ObjetJournal, OrigineVersion
from gestion_mp_pro.modeles.types import MESURE, arrondir
from gestion_mp_pro.services import audit, recettes
from gestion_mp_pro.services import production as plans
from gestion_mp_pro.services.audit import Qui
from gestion_mp_pro.services.recettes import LigneSaisie

QUOI = "Cette qualité"


@dataclass(frozen=True)
class PoidsSaisi:
    """Le poids au m² d'un rôle (kg/m², ou ml/m² pour un rôle au mètre)."""

    role_id: int
    poids: Decimal


@dataclass(frozen=True)
class FicheSaisie:
    """Ce que la fiche d'une qualité envoie (création ou modification)."""

    code: str
    nom: str = ""
    actif: bool = True
    poids: Sequence[PoidsSaisi] = ()
    recette: Sequence[LigneSaisie] | None = None
    motif: str = ""


@dataclass
class Resultat:
    """La qualité écrite et ce qu'il faut en dire (rôles pesants sans matière)."""

    qualite: Qualite
    avertissement: str = ""
    versions: list[str] = field(default_factory=list)


def verrouiller(s: Session, qualite_id: int) -> Qualite:
    """La qualité sous verrou de ligne (404 « Qualité introuvable. »)."""
    q = s.get(Qualite, qualite_id, with_for_update=True, populate_existing=True)
    if q is None:
        raise Refus.introuvable("Qualité introuvable.")
    return q


def toucher(q: Qualite, qui: Qui) -> None:
    """Fait monter la `version` de la qualité (même si seule une table liée a changé)."""
    q.modifie_par_id = qui.id
    flag_modified(q, "modifie_par_id")


def _code_libre(s: Session, code: str, qualite_id: int | None = None) -> None:
    """Deux qualités ne portent pas le même code, quelle que soit sa casse (409, X-REF-39,
    A-12 : « 8m » et « 8M » seraient deux qualités sur les ordres de fabrication)."""
    requete = select(Qualite.code).where(func.lower(Qualite.code) == code.lower())
    if qualite_id is not None:
        requete = requete.where(Qualite.id != qualite_id)
    autre = s.scalar(requete)
    if autre is not None:
        en_plus = f" (« {code} »)" if autre != code else ""
        raise Refus.etat(f"La qualité « {autre} » existe déjà{en_plus}.", code="doublon")


def ecrire_poids(s: Session, q: Qualite, poids: Sequence[PoidsSaisi]) -> None:
    """Remplace les poids au m² (rôle inconnu, négatif, en double : 422)."""
    roles = recettes.codes_des_roles(s)
    vus: set[int] = set()
    for p in poids:
        if p.role_id not in roles:
            raise Refus.saisie(f"Rôle inconnu : « {p.role_id} ».", code="valeur_inconnue")
        if p.poids < 0:
            raise Refus.saisie("Un poids au m² ne peut pas être négatif.")
        if p.role_id in vus:
            raise Refus.saisie(
                f"Le rôle « {roles[p.role_id].code} » figure deux fois dans les poids.",
                code="ligne_en_double",
            )
        vus.add(p.role_id)
    s.execute(delete(QualitePoids).where(QualitePoids.qualite_id == q.id))
    for p in poids:
        valeur = arrondir(p.poids, MESURE)
        if valeur > 0:
            s.add(QualitePoids(qualite_id=q.id, role_id=p.role_id, poids=valeur))
    s.flush()


def photo(s: Session, q: Qualite) -> dict[str, object]:
    """La fiche pour le journal : code, nom, en service, poids et lignes (identifiants)."""
    e = recettes.etat(s, q.id)
    return {
        "code": q.code,
        "nom": q.nom,
        "actif": q.actif,
        "poids": [{"role_id": r, "poids": float(p)} for r, p in sorted(e.poids.items())],
        "recette": [
            {"matiere_id": m, "pourcentage": float(p)} for m, p in sorted(e.lignes.items())
        ],
    }


def _journal(s: Session, qui: Qui, action: str, q: Qualite, avant: dict[str, object]) -> bool:
    """Une ligne de journal avec les seuls champs changés ; rien (faux) si rien n'a changé."""
    a, b = audit.differences(avant, photo(s, q))
    if not a and not b:
        return False
    audit.journal(s, qui, action, ObjetJournal.qualite, q.id, detail=q.code, avant=a, apres=b)
    return True


def avertir_oublis(s: Session, q: Qualite) -> str:
    """Rôles pesants sans matière : refus pour une qualité en service dont la recette est
    commencée (D-05), sinon avertissement (R-REF-62)."""
    roles = recettes.codes_des_roles(s)
    manquants = recettes.oublies(recettes.poids_de(s, q.id), recettes.roles_portes(s, q.id), roles)
    if not manquants:
        return ""
    sans_matiere = recettes.roles_sans_matiere(s)
    commencee = s.scalar(
        select(func.count())
        .select_from(Recette)
        .where(Recette.qualite_id == q.id, Recette.pourcentage > 0)
    )
    if q.actif and commencee:
        raise Refus.saisie(
            recettes.message_oublies(manquants, sans_matiere), code="recette_incomplete"
        )
    a_creer = " ni ".join(code for code, _ in manquants if code in sans_matiere)
    return (
        "Rôle(s) avec un poids au m² mais sans matière dans la recette : "
        + ", ".join(code for code, _ in manquants)
        + ". Les besoins et la sortie vers les machines ne les comptent pas tant que la "
        "recette ne les nomme pas."
        + (
            f" Aucune matière {a_creer} n'existe au catalogue : la créer d'abord (Matières, "
            "classification, fournisseurs)."
            if a_creer
            else ""
        )
    )


def avertissement_arretee(s: Session, oublies: Sequence[tuple[str, Decimal]]) -> str:
    """L'avertissement d'une recette incomplète enregistrée sur une qualité arrêtée."""
    if not oublies:
        return ""
    message = recettes.message_oublies(oublies, recettes.roles_sans_matiere(s))
    return (
        f"Qualité arrêtée : recette enregistrée telle quelle. {message} À faire avant de la "
        "remettre en service."
    )


def creer(s: Session, qui: Qui, f: FicheSaisie) -> Resultat:
    """Route 84 : la qualité, ses poids, son plan « d'avant » et sa première recette (D-18)."""
    _code_libre(s, f.code)
    q = Qualite(code=f.code, nom=f.nom, actif=f.actif, base_mensuelle=Decimal(0))
    s.add(q)
    s.flush()
    ecrire_poids(s, q, f.poids)
    plans.ecrire_version(s, q, plans.plan_de(s, q), qui.id)
    recettes.enregistrer_version(s, q, qui.id)
    audit.journal(
        s, qui, "création qualité", ObjetJournal.qualite, q.id, detail=q.code, apres=photo(s, q)
    )
    return Resultat(q, avertir_oublis(s, q))


def modifier(s: Session, qui: Qui, qualite_id: int, f: FicheSaisie, version: int) -> Resultat:
    """Route 85 : fiche, poids et, si elle est envoyée, recette — une seule transaction (P7-8)."""
    q = verrouiller(s, qualite_id)
    audit.verifier_version(s, q, version, QUOI)
    _code_libre(s, f.code, q.id)
    avant, plan_avant = photo(s, q), plans.plan_de(s, q)
    q.code, q.nom, q.actif = f.code, f.nom, f.actif
    ecrire_poids(s, q, f.poids)
    oublies = recettes.remplacer(s, q, f.recette) if f.recette is not None else []
    avertissement = avertissement_arretee(s, oublies) or avertir_oublis(s, q)
    if _journal(s, qui, "modification qualité", q, avant):
        toucher(q, qui)
    if plan_avant.actif != q.actif:
        etat = "remise en service" if q.actif else "arrêtée"
        plans.noter_plan(s, qui, q, plan_avant, detail=f"{q.code} : {etat}")
    recettes.enregistrer_version(s, q, qui.id, motif=f.motif)
    return Resultat(q, avertissement)


def supprimer(s: Session, qui: Qui, qualite_id: int, version: int) -> None:
    """Route 86 : refusée si un ordre l'a tissée (X-REF-44) ; sinon tout part, versions
    comprises."""
    q = verrouiller(s, qualite_id)
    audit.verifier_version(s, q, version, QUOI)
    n = s.scalar(
        select(func.count()).select_from(OrdreQualite).where(OrdreQualite.qualite_id == q.id)
    )
    if n:
        raise Refus.etat(
            f"« {q.code} » a été fabriquée par {n} ordre(s) : elle appartient à "
            "l'historique. La désactiver plutôt que la supprimer.",
            code="fiche_utilisee",
        )
    audit.journal(
        s, qui, "suppression qualité", ObjetJournal.qualite, q.id, detail=q.code, avant=photo(s, q)
    )
    s.execute(delete(RecetteVersion).where(RecetteVersion.qualite_id == q.id))
    s.execute(delete(PlanVersion).where(PlanVersion.qualite_id == q.id))
    s.execute(delete(Recette).where(Recette.qualite_id == q.id))
    s.delete(q)
    s.flush()


def ecrire_recette(
    s: Session,
    qui: Qui,
    qualite_id: int,
    lignes: Sequence[LigneSaisie],
    *,
    motif: str,
    version: int,
) -> Resultat:
    """Route 87 : remplace la recette (R-REF-64, R-REF-65) ; journal « recette »."""
    q = verrouiller(s, qualite_id)
    audit.verifier_version(s, q, version, QUOI)
    oublies = recettes.remplacer(s, q, lignes)
    toucher(q, qui)
    detail = f"{q.code} : {len(lignes)} ligne(s)" + (f" — {motif}" if motif else "")
    audit.journal(s, qui, "recette", ObjetJournal.qualite, q.id, detail=detail)
    recettes.enregistrer_version(s, q, qui.id, motif=motif)
    return Resultat(q, avertissement_arretee(s, oublies))


def _poids_a_restaurer(s: Session, v: RecetteVersion) -> dict[int, Decimal]:
    """Les poids d'une version ; sans poids gardés, ceux de la suivante qui les a, sinon
    ceux d'aujourd'hui (R-REF-69)."""
    if v.poids_connus:
        return recettes.etat_de_version(s, v.id).poids
    suivante = s.scalars(
        select(RecetteVersion)
        .where(
            RecetteVersion.qualite_id == v.qualite_id,
            RecetteVersion.numero > v.numero,
            RecetteVersion.poids_connus.is_(True),
        )
        .order_by(RecetteVersion.numero)
        .limit(1)
    ).first()
    if suivante is not None:
        return recettes.etat_de_version(s, suivante.id).poids
    return recettes.poids_de(s, v.qualite_id)


def restaurer(
    s: Session, qui: Qui, qualite_id: int, version_id: int, *, motif: str, version: int
) -> Resultat:
    """Route 89 : revient d'un bloc aux parts **et** aux poids d'une version ; une seule
    version nouvelle, signée et motivée (R-REF-69)."""
    q = verrouiller(s, qualite_id)
    v = s.get(RecetteVersion, version_id)
    if v is None or v.qualite_id != q.id:
        raise Refus.introuvable("Version introuvable.")
    audit.verifier_version(s, q, version, QUOI)
    cible = recettes.Etat(recettes.etat_de_version(s, v.id).lignes, _poids_a_restaurer(s, v))
    if cible == recettes.etat(s, q.id):
        raise Refus.etat(
            "La recette en vigueur est déjà celle de cette version : rien à restaurer."
        )
    ecrire_poids(s, q, [PoidsSaisi(r, p) for r, p in cible.poids.items()])
    oublies = recettes.remplacer(s, q, [LigneSaisie(m, p) for m, p in cible.lignes.items()])
    toucher(q, qui)
    quand = audit.horodatage(v.valide_depuis)
    detail = f"{q.code} : retour à la version du {quand} — {motif}"
    audit.journal(s, qui, "recette", ObjetJournal.qualite, q.id, detail=detail)
    recettes.enregistrer_version(
        s, q, qui.id, origine=OrigineVersion.restauration, motif=motif, restauree_de_id=v.id
    )
    return Resultat(q, avertissement_arretee(s, oublies))


def ecrire_plan(
    s: Session,
    qui: Qui,
    qualite_id: int,
    base: Decimal,
    *,
    coefficients: Sequence[Decimal],
    motif: str,
    version: int,
) -> Resultat:
    """Route 90 : le plan d'une qualité (même chemin que le plan global, route 146)."""
    q = verrouiller(s, qualite_id)
    audit.verifier_version(s, q, version, QUOI)
    if not plans.coefficients_valables(coefficients):
        raise Refus.saisie("Un coefficient de saisonnalité reste entre 0 et 20.")
    plans.refuser_si_arretee(s, q, base, coefficients)
    if plans.enregistrer_plan(s, qui, q, base, coefficients=coefficients, motif=motif):
        toucher(q, qui)
    return Resultat(q)
