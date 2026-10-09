"""Comptes gérés par la direction et l'administrateur (routes 15–18 ; B.5.5, F-01, F-03).

- Un compte ne se supprime pas : il se désactive (ses sessions sont fermées aussitôt).
- Il reste **toujours une direction active** (directions verrouillées `FOR UPDATE` pendant le
  contrôle : deux désactivations simultanées ne passent pas toutes les deux).
- On ne change ni son propre rôle ni son propre état (D9).
- Changer de rôle vers un rôle plus exigeant, ou vers l'alimentation (pavé à 4 chiffres),
  demande un nouveau code dans la même requête (F-01) ; nouveau code, nouveau rôle ou
  désactivation ferment les sessions du compte (F-03), sauf celle d'où l'on agit sur soi.
- Un compte `historique` (créé par la reprise pour un nom de Gestion MP) ne se modifie pas.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import SessionOuverte, Utilisateur
from gestion_mp_pro.modeles.enums import ObjetJournal, Role
from gestion_mp_pro.services import audit, horloge, sessions
from gestion_mp_pro.services.comptes import (
    LONGUEUR_MINI,
    Acteur,
    exiger_code,
    hacher,
    libelle_role,
    normaliser_identifiant,
    verifier_courriel,
)


@dataclass(frozen=True)
class FicheCompte:
    """Un compte et le nombre de ses sessions ouvertes."""

    utilisateur: Utilisateur
    sessions_ouvertes: int


def _sessions_par_compte(s: Session) -> dict[int, int]:
    """Sessions non expirées, par compte."""
    requete = (
        select(SessionOuverte.utilisateur_id, func.count())
        .where(SessionOuverte.expire_le > horloge.maintenant())
        .group_by(SessionOuverte.utilisateur_id)
    )
    return {int(i): int(n) for i, n in s.execute(requete).all()}


def lister(s: Session) -> list[FicheCompte]:
    """Tous les comptes, triés par nom (K40)."""
    ouvertes = _sessions_par_compte(s)
    comptes = s.scalars(select(Utilisateur).order_by(func.lower(Utilisateur.nom), Utilisateur.id))
    return [FicheCompte(u, ouvertes.get(u.id, 0)) for u in comptes]


def fiche(s: Session, ident: int) -> FicheCompte:
    """Un compte (404 « Compte introuvable. »)."""
    u = s.get(Utilisateur, ident)
    if u is None:
        raise Refus.introuvable("Compte introuvable.")
    return FicheCompte(u, _sessions_par_compte(s).get(u.id, 0))


def verifier_role(role: str) -> Role:
    """Le rôle demandé, ou 422 « Rôle inconnu. » (KR20)."""
    if role not in Role.__members__:
        raise Refus.saisie("Rôle inconnu.", code="valeur_inconnue", champs={"role": "inconnu"})
    return Role(role)


def creer(
    s: Session, qui: Acteur, *, identifiant: str, nom: str, role: str, email: str, code: str
) -> FicheCompte:
    """Un nouveau compte ; son code suit la règle de son rôle (K41, KR20–KR22)."""
    voulu = verifier_role(role)
    propre = normaliser_identifiant(identifiant)
    exiger_code(voulu, code)
    u = Utilisateur(
        identifiant=propre,
        nom=nom.strip(),
        role=voulu,
        email=verifier_courriel(email),
        empreinte_code=hacher(code),
        code_change_le=horloge.maintenant(),
    )
    try:
        with s.begin_nested():
            s.add(u)
            s.flush()
    except IntegrityError as exc:
        raise Refus.etat(f"L'identifiant « {propre} » est déjà pris.", code="doublon") from exc
    audit.creation(s, qui, "création de compte", u, detail=f"{u.nom} ({libelle_role(voulu)})")
    return FicheCompte(u, 0)


def _charger(s: Session, ident: int) -> Utilisateur:
    """Le compte verrouillé pour être modifié (404 sinon ; un compte de la reprise refusé)."""
    u = s.scalars(select(Utilisateur).where(Utilisateur.id == ident).with_for_update()).first()
    if u is None:
        raise Refus.introuvable("Compte introuvable.")
    if u.historique:
        raise Refus.etat(
            "Ce compte vient de la reprise de Gestion MP : il garde l'histoire et ne se "
            "connecte pas, il ne se modifie donc pas."
        )
    return u


def exige_nouveau_code(ancien: str | None, nouveau: str) -> bool:
    """Le code gardé ne convient plus : vers l'alimentation, depuis elle, ou plus long exigé."""
    if Role.alimentation in (ancien, nouveau):
        return ancien != nouveau
    return LONGUEUR_MINI[nouveau] > LONGUEUR_MINI.get(ancien or "", 0)


def _attendu(role: str) -> str:
    """« de 4 chiffres » ou « de 8 caractères au moins »."""
    if role == Role.alimentation:
        return "de 4 chiffres"
    return f"de {LONGUEUR_MINI[role]} caractères au moins"


def _garder_une_direction(s: Session, u: Utilisateur) -> None:
    """409 si ce compte est la dernière direction active (directions verrouillées)."""
    actives = select(Utilisateur.id).where(
        Utilisateur.role == Role.direction, Utilisateur.actif, Utilisateur.historique.is_(False)
    )
    autres = [i for i in s.scalars(actives.with_for_update()) if i != u.id]
    if not autres:
        raise Refus.etat(
            "Il doit toujours rester un compte de direction actif : en créer ou en réactiver "
            "un autre d'abord.",
            code="derniere_direction",
        )


@dataclass(frozen=True)
class Modification:
    """Ce qu'un `PUT /utilisateurs/{id}` remplace (la fiche entière) et un code facultatif."""

    nom: str
    role: str
    email: str
    actif: bool
    version: int
    code: str | None = None


def _controler(s: Session, qui: Acteur, u: Utilisateur, m: Modification) -> Role:
    """Soi-même, nouveau code exigé, dernière direction : les refus d'une modification."""
    voulu = verifier_role(m.role)
    if u.id == qui.id and (voulu != u.role or not m.actif):
        if u.role == Role.direction:
            raise Refus.etat("Vous ne pouvez pas retirer vos propres droits de direction.")
        raise Refus.etat("Vous ne pouvez ni changer votre propre rôle ni vous désactiver.")
    if voulu != u.role and not m.code and exige_nouveau_code(u.role, voulu):
        raise Refus.saisie(
            f"Ce rôle demande un code {_attendu(voulu)} : en donner un nouveau.",
            code="code_invalide",
            champs={"code": "nouveau code exigé"},
        )
    if m.code:
        exiger_code(voulu, m.code)
    if u.role == Role.direction and u.actif and (voulu != Role.direction or not m.actif):
        _garder_une_direction(s, u)
    return voulu


def modifier(s: Session, qui: Acteur, ident: int, m: Modification) -> FicheCompte:
    """Remplace nom, rôle, courriel, état (et le code s'il est donné) ; journal avant/après."""
    u = _charger(s, ident)
    audit.verifier_version(s, u, m.version, "Ce compte", feminin=False)
    voulu = _controler(s, qui, u, m)
    change_de_role, desactive = voulu != u.role, u.actif and not m.actif
    with audit.suivre(s, qui, "modification de compte", u) as geste:
        u.nom, u.role, u.email, u.actif = m.nom.strip(), voulu, verifier_courriel(m.email), m.actif
        if m.code:
            u.empreinte_code, u.code_change_le = hacher(m.code), horloge.maintenant()
        geste.detail = f"{u.nom} ({libelle_role(voulu)})" + (" ; nouveau code" if m.code else "")
    if desactive:
        sessions.expirer_sessions(s, u.id)
    elif m.code or change_de_role:
        sessions.fermer_sessions(s, u.id, sauf=qui.session if u.id == qui.id else None)
    if m.code:
        sessions.noter_succes(u.identifiant)
    s.flush()
    return fiche(s, u.id)


def remettre_code(s: Session, qui: Acteur, ident: int, code: str) -> None:
    """Remet le code d'un compte (code oublié) : ses sessions sont fermées, son blocage levé."""
    u = _charger(s, ident)
    exiger_code(str(u.role), code)
    u.empreinte_code, u.code_change_le = hacher(code), horloge.maintenant()
    sessions.fermer_sessions(s, u.id, sauf=qui.session if u.id == qui.id else None)
    sessions.noter_succes(u.identifiant)
    audit.journal(s, qui, "remise de code", ObjetJournal.utilisateur, u.id, detail=u.nom)
