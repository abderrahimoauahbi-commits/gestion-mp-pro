"""L'échéancier des paiements (routes 228–230) : factures des fournisseurs, frais d'importation.

Le calcul est celui du moteur (`calcul.suivi.echeancier`) : une facture sans montant vaut ce
que ses réceptions validées ont apporté (« estimé ») ; dont toutes les réceptions sont annulées,
elle est écartée (réglée : un avoir est à demander) ; qui ne porte que des brouillons, elle
n'est pas encore due. PRO ajoute : les frais **dus** d'un dossier annulé sont écartés de même (un
frais réglé reste réglé, B-01) ; la
recherche (tous les mots, sans accents) et la nature filtrent au serveur et les indicateurs les
suivent ; l'échu reste compté quelle que soit la période affichée (une période qui commence
demain ne le cache pas). Chaque ligne porte sa `version` (règlement, route 229) et la fiche
qu'elle ouvre (réception ou dossier).

Réglées : sans période, les `REGLEES_AU_PLUS` (300) règlements les plus récents **parmi les
lignes gardées** par la recherche et la nature, et la réponse le dit (`reglees_plafond`,
`reglees_total`) ; avec une période `du`/`au`, **toutes** les pièces réglées dans la période
(date de règlement, bornes incluses), factures et frais, sans plafond (`reglees_plafond` nul).

Règlement (229) : une facture passe par `services.factures.regler` (lot D4) ; un frais suit les
mêmes règles (`verifier_date_reglement`, annulation par la direction seule avec un motif :
`verifier_annulation_reglement`) et s'écrit au journal de **son dossier** (l'historique de la
fiche le montre ; la version du dossier monte, lot D7).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from typing import Any, Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.calcul import suivi
from gestion_mp_pro.modeles import (
    Devise,
    Dossier,
    DossierFrais,
    Facture,
    Fournisseur,
    PosteFrais,
    Reception,
    ReceptionLigne,
)
from gestion_mp_pro.modeles.enums import StatutDossier
from gestion_mp_pro.services import audit, factures, horloge
from gestion_mp_pro.services.importations.socle import noter
from gestion_mp_pro.services.recherche import trouve

Genre = Literal["facture", "frais"]
DANS_30_JOURS = 30
RAISON_DOSSIER_ANNULE = "dossier annulé : plus dû"


@dataclass(frozen=True)
class Filtres:
    """Les filtres de l'échéancier (les mêmes pour la liste et le classeur)."""

    q: str = ""
    nature: Genre | None = None
    du: date | None = None
    au: date | None = None


@dataclass
class Echeancier:
    """L'échéancier filtré, ses indicateurs et ses quatre vues."""

    lignes: list[dict[str, Any]]
    par_mois: dict[str, float]
    total_mad: float
    echu_mad: float
    echues: int
    dans_30_jours_mad: float
    a_dater: list[dict[str, Any]]
    a_dater_mad: float
    reglees: list[dict[str, Any]]
    reglees_total: int
    reglees_plafond: int | None
    ecartees: list[dict[str, Any]]
    aujourdhui: date = field(default_factory=horloge.aujourd_hui)


@dataclass
class _Pieces:
    """Ce que la base dit des pièces : versions, fiches à ouvrir, frais des dossiers annulés."""

    versions: dict[tuple[str, int], int] = field(default_factory=dict)
    liens: dict[tuple[str, int], dict[str, int | None]] = field(default_factory=dict)
    annules: list[suivi.FraisAPayer] = field(default_factory=list)


def _factures(s: Session, p: _Pieces) -> list[suivi.FactureAPayer]:
    premiere = (
        select(Reception.facture_id, func.min(Reception.id))
        .where(Reception.facture_id.is_not(None))
        .group_by(Reception.facture_id)
    )
    receptions = dict(s.execute(premiere).all())
    resultat = []
    requete = select(Facture, Fournisseur.nom).join(
        Fournisseur, Fournisseur.id == Facture.fournisseur_id
    )
    for f, nom in s.execute(requete.order_by(Facture.id)):
        p.versions[("facture", f.id)] = f.version
        p.liens[("facture", f.id)] = {
            "reception_id": receptions.get(f.id),
            "fournisseur_id": f.fournisseur_id,
        }
        resultat.append(
            suivi.FactureAPayer(
                id=f.id,
                fournisseur=nom,
                numero=f.numero,
                devise=f.devise,
                montant=float(f.montant) if f.montant is not None else None,
                echeance=f.echeance,
                payee_le=f.payee_le,
            )
        )
    return resultat


def _frais(s: Session, p: _Pieces) -> list[suivi.FraisAPayer]:
    requete = (
        select(DossierFrais, PosteFrais.code, Dossier.numero, Dossier.statut)
        .join(PosteFrais, PosteFrais.id == DossierFrais.poste_id)
        .join(Dossier, Dossier.id == DossierFrais.dossier_id)
        .order_by(DossierFrais.id)
    )
    resultat: list[suivi.FraisAPayer] = []
    for ch, poste, numero, statut in s.execute(requete):
        p.versions[("frais", ch.id)] = ch.version
        p.liens[("frais", ch.id)] = {"dossier_id": ch.dossier_id}
        x = suivi.FraisAPayer(
            id=ch.id,
            poste=poste,
            dossier=numero,
            montant=float(ch.montant),
            prestataire=ch.prestataire,
            piece=ch.piece,
            echeance=ch.echeance,
            payee_le=ch.payee_le,
        )
        du_dossier_annule = statut == StatutDossier.annule and ch.payee_le is None
        (p.annules if du_dossier_annule else resultat).append(x)
    return resultat


def _dues(s: Session) -> suivi.FacturesDues:
    requete = (
        select(
            Reception.facture_id,
            Reception.statut,
            ReceptionLigne.quantite_pesee,
            ReceptionLigne.prix,
            ReceptionLigne.qualite,
        )
        .join(ReceptionLigne, ReceptionLigne.reception_id == Reception.id)
        .where(Reception.facture_id.is_not(None))
    )
    return suivi.factures_dues(
        [
            suivi.PeseeFacturee(int(fid or 0), str(statut), float(q), float(prix), str(qualite))
            for fid, statut, q, prix, qualite in s.execute(requete)
        ]
    )


def _ecartes(annules: list[suivi.FraisAPayer]) -> list[suivi.Echeance]:
    """Les frais dus d'un dossier annulé : écartés (plus dus) ; un frais réglé reste réglé."""
    resultat = []
    for ch in annules:
        if ch.montant <= 0:
            continue
        raison = RAISON_DOSSIER_ANNULE
        resultat.append(
            suivi.Echeance(
                id=ch.id,
                objet="frais",
                genre=f"Frais d'importation ({ch.poste})",
                tiers=ch.prestataire or "—",
                piece=f"{ch.dossier} · {ch.piece}".strip(" ·"),
                montant=ch.montant,
                estime=False,
                devise="MAD",
                montant_mad=ch.montant,
                date=ch.echeance,
                payee_le=ch.payee_le,
                raison=raison,
            )
        )
    return resultat


def _garde(x: suivi.Echeance, f: Filtres) -> bool:
    return (f.nature is None or x.objet == f.nature) and trouve(
        f.q, x.genre, x.tiers, x.piece, x.devise
    )


def calculer(s: Session, f: Filtres, *, plafonner: bool = True) -> Echeancier:
    """Route 228 : l'échéancier filtré (recherche et nature après le calcul, période dedans) ;
    sans période, les réglées plafonnées aux `REGLEES_AU_PLUS` plus récentes (`plafonner`)."""
    p = _Pieces()
    fac, frais, dues = _factures(s, p), _frais(s, p), _dues(s)
    taux = {code: float(c) for code, c in s.execute(select(Devise.code, Devise.cours))}
    jour = horloge.aujourd_hui()
    e = suivi.echeancier(
        fac, frais, dues, taux=taux, aujourdhui=jour, du=f.du, au=f.au, reglees_au_plus=None
    )
    toutes = suivi.echeancier(fac, frais, dues, taux=taux, aujourdhui=jour).lignes
    echues = [x for x in toutes if x.en_retard and _garde(x, f)]

    def rendre(liste: list[suivi.Echeance]) -> list[dict[str, Any]]:
        """Les lignes gardées par les filtres, avec version et fiches."""
        return [
            {**asdict(x), "version": p.versions[(x.objet, x.id)], **p.liens[(x.objet, x.id)]}
            for x in liste
            if _garde(x, f)
        ]

    lignes = rendre(e.lignes)
    a_dater = rendre(e.a_dater)
    par_mois: dict[str, float] = {}
    for x in lignes:
        cle = f"{x['date']:%Y-%m}"
        par_mois[cle] = par_mois.get(cle, 0.0) + x["montant_mad"]
    limite = jour + timedelta(days=DANS_30_JOURS)
    reglees = rendre(e.reglees)
    plafond = suivi.REGLEES_AU_PLUS if plafonner and not (f.du or f.au) else None
    return Echeancier(
        lignes=lignes,
        par_mois=dict(sorted(par_mois.items())),
        total_mad=sum(x["montant_mad"] for x in lignes),
        echu_mad=sum(x.montant_mad for x in echues),
        echues=len(echues),
        dans_30_jours_mad=sum(x["montant_mad"] for x in lignes if jour <= x["date"] <= limite),
        a_dater=a_dater,
        a_dater_mad=sum(x["montant_mad"] for x in a_dater),
        reglees=reglees if plafond is None else reglees[:plafond],
        reglees_total=len(reglees),
        reglees_plafond=plafond,
        ecartees=rendre(e.ecartees + _ecartes(p.annules)),
        aujourdhui=jour,
    )


def ligne(s: Session, genre: Genre, ident: int) -> dict[str, Any]:
    """La ligne d'une pièce, avec la vue où elle se range (`etat`) ; une réglée se retrouve
    quel que soit son rang parmi les règlements (pas de plafond ici)."""
    e = calculer(s, Filtres(nature=genre), plafonner=False)
    vues = (
        ("a_payer", e.lignes),
        ("a_dater", e.a_dater),
        ("reglee", e.reglees),
        ("ecartee", e.ecartees),
    )
    for etat, liste in vues:
        for x in liste:
            if x["id"] == ident:
                return {**x, "etat": etat}
    raise Refus.introuvable("Pièce introuvable.")


def _regler_frais(
    s: Session, qui: audit.Qui, ident: int, *, payee_le: date | None, version: int, motif: str
) -> None:
    ch = s.scalars(
        select(DossierFrais)
        .where(DossierFrais.id == ident)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).first()
    if ch is None:
        raise Refus.introuvable("Pièce introuvable.")
    audit.verifier_version(s, ch, version, "Ce frais", feminin=False)
    d = s.get(Dossier, ch.dossier_id)
    if d is None:
        raise Refus.introuvable("Pièce introuvable.")
    if payee_le is None:
        if ch.payee_le is None:
            raise Refus.etat("Ce frais n'est pas réglé : aucun règlement à annuler.")
        motif = factures.verifier_annulation_reglement(qui, ch.payee_le, motif)
        action, detail = "règlement annulé", f"motif : {motif}"
    else:
        factures.verifier_date_reglement(s, payee_le, ch.date_piece)
        action, detail = "règlement", f"réglé le {payee_le:%d/%m/%Y}"
    avant = {"frais": ch.id, "payee_le": ch.payee_le}
    ch.payee_le = payee_le
    ch.payee_par_id = qui.id if payee_le is not None else None
    poste = s.scalar(select(PosteFrais.code).where(PosteFrais.id == ch.poste_id)) or ""
    noter(s, qui, d, action, f"frais {poste} {ch.piece}".strip() + f" · {detail}",
          avant=avant, apres={"frais": ch.id, "payee_le": payee_le})  # fmt: skip


def regler(
    s: Session,
    qui: audit.Qui,
    genre: Genre,
    ident: int,
    *,
    payee_le: date | None,
    version: int,
    motif: str = "",
) -> dict[str, Any]:
    """Route 229 : marque la pièce réglée tel jour, ou annule son règlement (`payee_le` vide :
    la direction seule, motif exigé) ; rend sa ligne relue."""
    if genre == "facture":
        factures.regler(s, qui, ident, payee_le=payee_le, version=version, motif=motif)
    else:
        _regler_frais(s, qui, ident, payee_le=payee_le, version=version, motif=motif)
    return ligne(s, genre, ident)
