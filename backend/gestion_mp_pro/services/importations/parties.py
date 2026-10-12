"""Les parties de la fiche qui se déduisent des totaux : frais lus, échéancier, alertes de
clôture, raisons « à vérifier », gestes permis (REGLES R-IMP-14, ECRANS-PRO 5.2 et 5.6 ;
défauts B-01, B-04, B-07 et anomalie 5.8 : une seule source pour la liste, la fiche, la
clôture).
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date

from gestion_mp_pro.documents.format import nombre, part
from gestion_mp_pro.modeles import Dossier, DossierFrais, Facture
from gestion_mp_pro.modeles.enums import StatutDossier
from gestion_mp_pro.services.importations.lignes import Marchandises
from gestion_mp_pro.services.importations.modele import (
    Actions,
    DossierResume,
    Echeance,
    FraisDossier,
    PartFigee,
)
from gestion_mp_pro.services.importations.socle import (
    DIRHAM,
    Contexte,
    a_la_main,
    factures_lues,
    frais_tries,
    refus_statut,
    repris,
)

CLES = {"valeur": "à la valeur", "poids": "au poids"}
FIGEE = "figée (clé d'avant son changement)"
NON_REPARTIS = (
    "Des frais ne trouvent pas de marchandise où se répartir : les affecter à tout le dossier, "
    "ou les retirer, avant de clore."
)
SANS_MARCHANDISE = "Un dossier sans marchandise n'a rien à clore."
DEJA_OUVERT = "Ce dossier est déjà ouvert."
DEJA_ANNULE = "Ce dossier est déjà annulé."
A_LA_MAIN = (
    "Ce dossier est saisi à la main (d'avant la mise en service) : une marchandise reçue entre "
    "par sa facture, dans le dossier de cette facture."
)
A_LA_MAIN_AJOUT = (
    "Ce dossier est saisi à la main (d'avant la mise en service) : une facture reçue ouvre son "
    "propre dossier, ou s'ajoute à un dossier ouvert depuis une facture."
)


def refus_retrait(d: Dossier, numero: str, lignes: set[int]) -> str | None:
    """Retirer une facture du dossier (route 254) : il est ouvert, et aucun frais ne vise une
    marchandise qu'elle a apportée (`lignes`) — il sortirait avec elle (I19)."""
    statut = refus_statut(d)
    if statut:
        return statut
    vises = [f for f in d.frais if f.ligne_id in lignes]
    if vises:
        return (
            f"{len(vises)} frais porte(nt) sur une marchandise de la facture {numero} : les "
            "affecter à tout le dossier (onglet Frais, « Porte sur »), ou les retirer, avant de "
            "retirer la facture — sinon ils sortiraient avec elle."
        )
    return None


def regle_le(x: DossierFrais) -> str | None:
    """Un frais réglé ne change ni de poste, ni de montant, ni de marchandise (B-01, I20)."""
    if x.payee_le is None:
        return None
    return (
        f"Frais réglé le {x.payee_le:%d/%m/%Y} : annuler d'abord le règlement (Analyse › "
        "Échéancier)."
    )


def repartition(x: DossierFrais, recuperable: bool, cle: str) -> str:
    """Comment le frais se répartit (le même libellé à l'écran et dans le classeur, B-09)."""
    if recuperable:
        return "hors coût (récupérable)"
    if x.ligne_id:
        return "sur cette marchandise"
    if x.parts:
        return FIGEE
    return CLES.get(cle, cle)


def frais_lus(d: Dossier, ctx: Contexte) -> list[FraisDossier]:
    """Les frais du dossier, leur répartition et leur règlement."""
    resultat = []
    for x in frais_tries(d):
        p = ctx.postes[x.poste_id]
        resultat.append(
            FraisDossier(
                id=x.id,
                poste_id=p.id,
                poste=p.code,
                libelle=p.libelle,
                recuperable=p.recuperable,
                cle=str(p.cle),
                repartition=repartition(x, p.recuperable, str(p.cle)),
                montant=x.montant,
                taux=x.taux,
                ligne_id=x.ligne_id,
                piece=x.piece,
                prestataire=x.prestataire,
                date_piece=x.date_piece,
                echeance=x.echeance,
                payee_le=x.payee_le,
                commentaire=x.commentaire,
                parts=[
                    PartFigee(y.ligne_id, y.montant)
                    for y in sorted(x.parts, key=lambda z: z.ligne_id)
                ],
                version=x.version,
                blocage=regle_le(x),
            )
        )
    return resultat


def _facture(f: Facture, ctx: Contexte, m: Marchandises) -> Echeance:
    """La facture de marchandise : son montant, sinon ce que sa marchandise a apporté
    (« estimé ») ; détachée, elle reste (B-07) mais n'apporte plus rien."""
    apporte = m.apporte.get(f.id, 0.0)
    return Echeance(
        echeance=f.echeance,
        nature="marchandise",
        quoi=f"Facture {f.numero}",
        tiers=ctx.nom(f.fournisseur_id),
        piece=f.numero,
        date_piece=f.date,
        montant=float(f.montant) if f.montant else apporte,
        estime=not f.montant and apporte > 0,
        detachee=f.id not in m.apporte,
        payee_le=f.payee_le,
        devise=f.devise,
        facture_id=f.id,
        frais_id=None,
    )


def echeancier(d: Dossier, ctx: Contexte, m: Marchandises) -> list[Echeance]:
    """Ce que le dossier engage à payer, échéance par échéance (R-IMP-14, B-07) : une échéance
    de marchandise par facture (les siennes, et celles dont il porte une marchandise), puis
    chaque frais."""
    factures = {x.facture_id: ctx.factures[x.facture_id] for x in factures_lues(d)}
    factures |= {f: ctx.factures[f] for f in m.apporte if f in ctx.factures}
    lignes = [_facture(f, ctx, m) for f in factures.values()]
    lignes += [
        Echeance(
            echeance=x.echeance,
            nature="frais",
            quoi=ctx.postes[x.poste_id].libelle,
            tiers=x.prestataire,
            piece=x.piece,
            date_piece=x.date_piece,
            montant=float(x.montant),
            estime=False,
            detachee=False,
            payee_le=x.payee_le,
            devise=DIRHAM,
            facture_id=None,
            frais_id=x.id,
        )
        for x in frais_tries(d)
    ]
    return sorted(lignes, key=lambda z: (z.echeance is None, z.echeance or date.min, z.quoi))


def _en_devise(r: DossierResume, lignes_devise: bool) -> list[str]:
    """Droits et TVA d'une marchandise en devise (alertes 9 à 11)."""
    alertes = []
    if lignes_devise and not r.droits_mad:
        alertes.append("Aucun droit de douane saisi.")
    if r.droits_ecart_mad is not None:
        alertes.append("Droits ≠ attendus.")
    if lignes_devise and not r.tva_saisie_mad:
        alertes.append("Aucune TVA saisie.")
    elif r.tva_ecart_mad is not None:
        alertes.append("TVA ≠ attendue.")
    return alertes


def alertes(r: DossierResume, sans_cours: int, lignes_devise: bool) -> list[str]:
    """Ce qu'il faut savoir avant de clore, dans l'ordre de la fenêtre de confirmation."""
    a = []
    if sans_cours:
        a.append("Les cours vides prendront le cours du jour (écrit sur chaque ligne).")
    if r.lignes_cours_bon:
        a.append(
            f"{r.lignes_cours_bon} ligne(s) gardent le cours du bon — celui des réglages le jour "
            "de la confirmation des prix, pas celui payé à la banque : saisir le cours de la "
            "banque (onglet Marchandises) avant de clore, sinon ce cours est figé."
        )
    for x in r.cours_disparates:
        cours = " et ".join(nombre(c, 0, 4) for c in x.cours)
        a.append(
            f"Les marchandises en {x.devise} ont plusieurs cours ({cours}) : un second camion ? "
            "Vérifier l'avis de la banque."
        )
    if r.surcout_aberrant:
        a.append(f"Les frais dépassent {part(r.seuil_surcout, 0)} de l'achat : les vérifier.")
    if r.lignes_aberrantes:
        a.append(f"Frais hors norme sur {', '.join(r.lignes_aberrantes)}.")
    for f in r.factures:
        if f.ecart is not None and f.ecart.hors_tolerance:
            a.append(
                f"La facture {f.numero} s'écarte de {part(f.ecart.part, 1)} de la marchandise "
                "qu'elle a apportée."
            )
    if r.cours_eloignes:
        a.append("Un cours s'écarte de plus de 5 % du cours du jour.")
    if len(r.fournisseurs) > 1:
        a.append(f"Le dossier mêle {len(r.fournisseurs)} fournisseurs.")
    return a + _en_devise(r, lignes_devise)


def a_verifier(r: DossierResume) -> list[str]:
    """Ce qui est à vérifier dans un dossier (étiquette de la liste ; anomalie 5.8)."""
    raisons = [
        "frais non répartis" if r.charges_non_reparties_mad or r.tva_non_repartie_mad else "",
        "droits ≠ attendus" if r.droits_ecart_mad is not None else "",
        "TVA ≠ attendue" if r.tva_ecart_mad is not None else "",
        "facture ≠ marchandise reçue"
        if any(f.ecart is not None and f.ecart.hors_tolerance for f in r.factures)
        else "",
        f"frais au-delà de {part(r.seuil_surcout, 0)} de l'achat" if r.surcout_aberrant else "",
        "frais hors norme sur une marchandise" if r.lignes_aberrantes else "",
        "marchandise négative (avoir)" if r.lignes_negatives else "",
        "cours à plus de 5 % du cours du jour" if r.cours_eloignes else "",
    ]
    raisons += [f"plusieurs cours en {x.devise}" for x in r.cours_disparates]
    return [x for x in raisons if x]


def refus_saisie(d: Dossier, factures: list[str]) -> str | None:
    """La saisie à la main : réservée aux dossiers d'avant la mise en service (X-IMP-18, 19)."""
    if len(factures) == 1:
        return (
            f"Le dossier de la facture {factures[0]} porte ce qu'elle a apporté, tel que reçu : "
            "la saisie à la main est réservée aux dossiers d'avant la mise en service."
        )
    if factures:
        return (
            f"Le dossier des factures {', '.join(factures)} porte ce qu'elles ont apporté, tel "
            "que reçu : la saisie à la main est réservée aux dossiers d'avant la mise en service."
        )
    if repris(d):
        return (
            f"Le dossier {d.numero} porte des réceptions : sa marchandise entre par ses "
            "factures, telle que reçue. La saisie à la main est réservée aux dossiers d'avant la "
            "mise en service."
        )
    if not a_la_main(d):
        return (
            f"Le dossier {d.numero} s'est ouvert depuis une facture : sa marchandise entre par "
            "ses factures (« Ajouter une facture »). La saisie à la main est réservée aux "
            "dossiers d'avant la mise en service."
        )
    return None


def _cloturer(r: DossierResume) -> str | None:
    """Clore : au moins une marchandise, aucun frais non réparti (X-IMP-40, 41 ; B-04)."""
    if not r.nb_lignes:
        return SANS_MARCHANDISE
    if r.charges_non_reparties_mad or r.tva_non_repartie_mad:
        return NON_REPARTIS
    return None


def actions(d: Dossier, r: DossierResume, devises: Iterable[str]) -> Actions:
    """Chaque geste : permis (`None`) ou la phrase exacte de son refus."""
    statut = refus_statut(d)
    factures = [f.numero for f in r.factures if f.liberee_le is None]
    rouvrir = {StatutDossier.ouvert: DEJA_OUVERT, StatutDossier.annule: refus_statut(d)}
    annuler = DEJA_ANNULE if d.statut == StatutDossier.annule else statut
    sans_devise = "Aucune marchandise en devise dans ce dossier."
    return Actions(
        modifier=statut,
        rattacher=statut or (A_LA_MAIN if a_la_main(d) else None),
        ajouter_facture=statut or (A_LA_MAIN_AJOUT if a_la_main(d) else None),
        saisir=statut or refus_saisie(d, factures),
        cours=statut or (None if any(x != DIRHAM for x in devises) else sans_devise),
        frais=statut,
        cloturer=statut or _cloturer(r),
        rouvrir=rouvrir.get(d.statut),
        annuler=annuler,
    )
