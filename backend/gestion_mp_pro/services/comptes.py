"""Comptes, codes, installation, connexion, son propre compte (ARCHITECTURE § 5.1 ; héritage B.5).

- Codes : `scrypt` (n = 2¹⁴, r = 8, p = 1, sel 16 octets), vérifiés en temps constant. Règle par
  rôle (D10, F-01) : l'alimentation tape **exactement 4 chiffres** (le téléphone envoie au 4ᵉ) ;
  achats et direction 8 caractères au moins ; l'administrateur technique 12.
- Installation : une seule fois (verrou de la table des comptes), crée la direction.
- Connexion : par identifiant tapé, ou par le nom touché (`compte`) sur le poste local ou un
  appareil enrôlé seulement ; essais comptés avant la vérification (`sessions`).
- Changer son code : un mauvais « code actuel » compte un échec ; le nouveau ferme les autres
  sessions (F-03). La gestion des comptes par la direction est dans `services.utilisateurs`.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import Parametre, Utilisateur
from gestion_mp_pro.modeles import longueurs as L
from gestion_mp_pro.modeles.enums import ObjetJournal, Role
from gestion_mp_pro.services import audit, horloge, sessions

ROLES_LIBELLES: dict[str, str] = {
    Role.direction: "Direction",
    Role.achats: "Responsable achats",
    Role.alimentation: "Responsable alimentation machines",
    Role.administrateur: "Administrateur technique",
}
"""Libellés des rôles (héritage K1 ; « Administrateur technique » ajouté, D12)."""

LONGUEUR_MINI: dict[str, int] = {
    Role.alimentation: 4,
    Role.achats: 8,
    Role.direction: 8,
    Role.administrateur: 12,
}
VOIT_PRIX = frozenset({Role.direction, Role.achats})
CODE_ATELIER = re.compile(r"[0-9]{4}")
IDENTIFIANT_PERMIS = re.compile(r"\S{2,40}")
COURRIEL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
MESSAGE_INCORRECT = "Identifiant ou code incorrect."

N, R, P, OCTETS = 2**14, 8, 1, 32


@dataclass(frozen=True)
class Acteur:
    """La personne connectée, telle que les services la reçoivent (et le journal la cite)."""

    id: int
    identifiant: str
    nom: str
    role: str
    requete: str = ""
    adresse: str = ""
    session: str = ""
    appareil_id: int | None = None

    @property
    def voit_prix(self) -> bool:
        """Direction et achats voient prix et montants ; ni l'alimentation ni l'administrateur."""
        return self.role in VOIT_PRIX


def acteur_de(u: Utilisateur, adresse: str = "") -> Acteur:
    """L'acteur d'un compte (connexion, installation : avant toute session)."""
    return Acteur(u.id, u.identifiant, u.nom, str(u.role or ""), adresse=adresse)


def libelle_role(role: str | None) -> str:
    """« Responsable achats »."""
    return ROLES_LIBELLES.get(role or "", role or "")


def message_refus(roles: Iterable[str]) -> str:
    """« Cette action est réservée à : responsable achats. » (KR14, mot pour mot).

    Comme dans Gestion MP, la direction n'est pas citée quand un rôle métier est permis ; une
    route de la direction seule dit « la direction ».
    """
    permis = set(roles)
    noms = [libelle_role(r).lower() for r in (Role.achats, Role.alimentation) if r in permis]
    if not noms:
        noms = ["la direction"] if Role.direction in permis else []
        if Role.administrateur in permis:
            noms.append("l'administrateur technique")
    return f"Cette action est réservée à : {', '.join(noms)}."


# ── Codes ───────────────────────────────────────────────────────────────────


def hacher(code: str) -> str:
    """`scrypt$<sel hex>$<empreinte hex>` (héritage K10)."""
    sel = secrets.token_bytes(16)
    h = hashlib.scrypt(code.encode(), salt=sel, n=N, r=R, p=P, dklen=OCTETS)
    return f"scrypt${sel.hex()}${h.hex()}"


def verifier(code: str, empreinte: str) -> bool:
    """Le code correspond-il à l'empreinte ? Une empreinte illisible ne correspond à rien."""
    try:
        _, sel, attendu = empreinte.split("$")
        h = hashlib.scrypt(code.encode(), salt=bytes.fromhex(sel), n=N, r=R, p=P, dklen=OCTETS)
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(h.hex(), attendu)


def defaut_du_code(role: str, code: str) -> str:
    """Pourquoi ce code ne convient pas à ce rôle (« » s'il convient) — D10, F-01."""
    if role == Role.alimentation:
        return (
            "" if CODE_ATELIER.fullmatch(code) else "Le code de l'atelier est fait de 4 chiffres."
        )
    mini = LONGUEUR_MINI.get(role, 8)
    if len(code) < mini:
        return f"Le code doit faire au moins {mini} caractères."
    return ""


def exiger_code(role: str, code: str, champ: str = "code", nouveau: bool = False) -> None:
    """422 `code_invalide` si le code ne suit pas la règle du rôle (KR16, KR22)."""
    defaut = defaut_du_code(role, code)
    if defaut:
        if nouveau:
            defaut = defaut.replace("Le code", "Le nouveau code", 1)
        raise Refus.saisie(defaut, code="code_invalide", champs={champ: defaut})


def normaliser_identifiant(identifiant: str) -> str:
    """Minuscules, sans espace autour ; refus s'il contient un blanc ou sort de 2–40."""
    propre = identifiant.strip().lower()
    if not IDENTIFIANT_PERMIS.fullmatch(propre):
        raise Refus.saisie(
            "L'identifiant fait de 2 à 40 caractères, sans espace.",
            champs={"identifiant": "2 à 40 caractères, sans espace"},
        )
    return propre


def verifier_courriel(email: str) -> str:
    """Un courriel vide ou lisible (ex. direction@usine.ma)."""
    propre = email.strip()
    if propre and not COURRIEL.fullmatch(propre):
        raise Refus.saisie(
            f"Adresse de courriel illisible : {propre} (ex. direction@usine.ma).",
            champs={"email": "adresse illisible"},
        )
    return propre[: L.EMAIL_COMPTE]


# ── Installation et connexion ───────────────────────────────────────────────


@dataclass(frozen=True)
class Ouverture:
    """Un compte et le jeton de la session qui vient de s'ouvrir."""

    utilisateur: Utilisateur
    jeton: str


@dataclass(frozen=True)
class Poste:
    """D'où vient la connexion : adresse, navigateur, appareil enrôlé, poste autorisé."""

    adresse: str = ""
    agent: str = ""
    appareil_id: int | None = None
    autorise: bool = False


def est_installe(s: Session) -> bool:
    """Au moins un compte existe."""
    return bool(s.scalar(select(func.count()).select_from(Utilisateur)))


def societe(s: Session) -> str:
    """La raison sociale réglée (vide si l'installation ne l'a pas donnée)."""
    p = s.get(Parametre, "nom_entreprise")
    return p.valeur if p is not None else ""


def installer(
    s: Session, *, societe: str, identifiant: str, nom: str, code: str, poste: Poste
) -> Ouverture:
    """Le premier compte, celui de la direction ; ne sert qu'une fois (K20–K22, KR1)."""
    s.execute(text("LOCK TABLE utilisateur IN SHARE ROW EXCLUSIVE MODE"))
    if est_installe(s):
        raise Refus.etat("Gestion MP PRO est déjà installé : connectez-vous.", code="deja_installe")
    exiger_code(Role.direction, code)
    u = Utilisateur(
        identifiant=normaliser_identifiant(identifiant),
        nom=nom.strip(),
        role=Role.direction,
        empreinte_code=hacher(code),
        code_change_le=horloge.maintenant(),
    )
    s.add(u)
    s.flush()
    qui = acteur_de(u, adresse=poste.adresse)
    if societe.strip():
        p = s.get(Parametre, "nom_entreprise")
        if p is not None:
            with audit.suivre(s, qui, "paramètre", p, detail="Raison sociale (installation)"):
                p.valeur = societe.strip()[: L.VALEUR_REGLAGE]
                p.modifie_par_id = u.id
    audit.creation(s, qui, "installation", u, detail=f"{u.nom} ({libelle_role(u.role)})")
    jeton = sessions.ouvrir(s, u, adresse=poste.adresse, agent=poste.agent)
    return Ouverture(u, jeton)


def _compte_vise(
    s: Session, compte_id: int | None, identifiant: str, poste: Poste
) -> tuple[Utilisateur | None, str]:
    """Le compte visé par la connexion et la clé de ses essais."""
    if compte_id is not None:
        if not poste.autorise:
            raise Refus.droit(
                "Choisir son nom n'est possible que sur le poste de l'usine ou un téléphone "
                "enrôlé : tapez votre identifiant.",
                code="poste_non_autorise",
            )
        u = s.get(Utilisateur, compte_id)
        return u, (u.identifiant if u is not None else f"#{compte_id}")
    cle = sessions.cle_identifiant(identifiant)
    if not cle:
        raise Refus.saisie("Tapez votre identifiant.", champs={"identifiant": "à renseigner"})
    return s.scalars(select(Utilisateur).where(Utilisateur.identifiant == cle)).first(), cle


def connecter(
    s: Session, *, compte_id: int | None, identifiant: str, code: str, poste: Poste
) -> Ouverture:
    """Connexion : essai compté d'abord (compte et adresse), puis code vérifié (K31, F-02)."""
    u, cle = _compte_vise(s, compte_id, identifiant, poste)
    adresse = sessions.cle_adresse(poste.adresse)
    attente = sessions.reserver_essai(
        (cle, sessions.ECHECS_TOLERES), (adresse, sessions.ECHECS_TOLERES_ADRESSE)
    )
    if attente:
        raise sessions.refus_patienter(attente)
    if u is None or not u.actif or u.historique or not verifier(code, u.empreinte_code):
        raise Refus.non_connecte(MESSAGE_INCORRECT, code="identifiants_incorrects")
    sessions.noter_succes(cle, adresse)
    sessions.purger(s)
    jeton = sessions.ouvrir(
        s, u, adresse=poste.adresse, agent=poste.agent, appareil_id=poste.appareil_id
    )
    audit.journal(
        s, acteur_de(u, adresse=poste.adresse), "connexion", ObjetJournal.utilisateur, u.id
    )
    return Ouverture(u, jeton)


def visages(s: Session) -> list[Utilisateur]:
    """Les comptes actifs, triés par nom, pour toucher son nom à la connexion (K30)."""
    requete = select(Utilisateur).where(Utilisateur.actif, Utilisateur.historique.is_(False))
    return list(s.scalars(requete.order_by(func.lower(Utilisateur.nom), Utilisateur.id)))


# ── Son propre compte ───────────────────────────────────────────────────────


def moi(s: Session, qui: Acteur) -> Utilisateur:
    """Le compte de la personne connectée."""
    u = s.get(Utilisateur, qui.id)
    if u is None:
        raise Refus.non_connecte()
    return u


def modifier_moi(s: Session, qui: Acteur, email: str, version: int) -> Utilisateur:
    """Son courriel (route 13) ; la version lue est exigée."""
    u = s.scalars(select(Utilisateur).where(Utilisateur.id == qui.id).with_for_update()).one()
    audit.verifier_version(s, u, version, "Votre compte", feminin=False)
    propre = verifier_courriel(email)
    if propre != u.email:
        with audit.suivre(s, qui, "modification de compte", u, detail=f"{u.nom} : courriel"):
            u.email = propre
        s.flush()
    return u


def changer_mon_code(s: Session, qui: Acteur, ancien: str, nouveau: str) -> None:
    """Son code (route 14) : ancien vérifié et compté, nouveau à la règle du rôle (F-01, F-03)."""
    u = moi(s, qui)
    attente = sessions.reserver_essai((u.identifiant, sessions.ECHECS_TOLERES))
    if attente:
        raise sessions.refus_patienter(attente)
    if not verifier(ancien, u.empreinte_code):
        raise Refus.droit("Le code actuel ne correspond pas.")
    sessions.noter_succes(u.identifiant)
    exiger_code(str(u.role), nouveau, champ="nouveau", nouveau=True)
    u.empreinte_code = hacher(nouveau)
    u.code_change_le = horloge.maintenant()
    sessions.fermer_sessions(s, u.id, sauf=qui.session or None)
    audit.journal(s, qui, "changement de code", ObjetJournal.utilisateur, u.id, detail=u.nom)
