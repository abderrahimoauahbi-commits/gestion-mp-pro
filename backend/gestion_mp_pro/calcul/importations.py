"""Coût de revient à l'importation : frais répartis, TVA et droits attendus, facture.

Portage de `moteur.LigneRevient`, `tva_attendue`, `ecart_droits`, `ecart_tva_tolere`,
`valeur_ligne_import`, `revient_dossier`, `lignes_aberrantes`, `lignes_negatives`,
`ecart_facture`, `revient_par_reception`, `revient_par_lot` (CALCULS B § 9). Les frais se
répartissent à la valeur (ou au poids pour un poste réglé ainsi) ; la TVA, récupérable, pèse
sur la trésorerie, jamais sur le coût.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from gestion_mp_pro.calcul.constantes import (
    CENTIME,
    ECART_DROITS_MINIMUM,
    RECUPERABLES,
    TOLERANCE_DROITS_IMPORT,
    TOLERANCE_TVA_IMPORT,
)
from gestion_mp_pro.calcul.modele import (
    Donnees,
    DossierImport,
    FactureImport,
    LigneImport,
    Parametres,
)


@dataclass
class LigneRevient:
    """Ce qu'une marchandise d'un dossier coûte, une fois les frais répartis."""

    dossier: str
    ligne_id: int
    reference: str
    lot_fournisseur: str
    fournisseur: str
    quantite: float
    valeur_mad: float
    part: float
    charges_mad: float
    tva_mad: float
    detail: dict[str, float] = field(default_factory=dict)
    poids_kg: float = 0.0

    @property
    def revient_mad(self) -> float:
        """Marchandise + frais non récupérables."""
        return self.valeur_mad + self.charges_mad

    @property
    def revient_unite(self) -> float:
        """Le coût de revient au kilo."""
        return self.revient_mad / self.quantite if self.quantite else 0.0

    @property
    def valeur_unite(self) -> float:
        """La marchandise au kilo."""
        return self.valeur_mad / self.quantite if self.quantite else 0.0

    @property
    def surcout(self) -> float:
        """Le supplément par rapport à la facture, en part de celle-ci."""
        return self.charges_mad / self.valeur_mad if self.valeur_mad else 0.0

    @property
    def decaisse_mad(self) -> float:
        """Ce qui sort de la trésorerie : revient + TVA."""
        return self.revient_mad + self.tva_mad


def valeur_ligne_import(ligne: LigneImport, parametres: Parametres) -> float:
    """La marchandise en dirhams : au cours du dossier, sinon au taux des réglages ; une
    marchandise en dirhams n'a pas de cours (un cours porté par erreur est ignoré)."""
    if (ligne.devise or "MAD") == "MAD":
        return ligne.valeur_devise
    cours = ligne.cours or parametres.taux(ligne.devise)
    return ligne.valeur_devise * cours


def tva_attendue(dossier: DossierImport, parametres: Parametres) -> float:
    """TVA = taux × (valeur en douane + droits + TPI), valeur en douane = marchandise + les
    frais qui y entrent (CAF : fret, assurance) ; droits et TPI par la **nature** de leur poste
    (`ChargeImport.est_droits`, `est_tpi`) ; la TPI saisie se prend telle quelle, sinon elle se
    calcule."""
    if not dossier.lignes:
        return 0.0
    douane = sum(valeur_ligne_import(x, parametres) for x in dossier.lignes)
    douane += sum(c.montant for c in dossier.charges if c.dans_valeur_douane)
    droits = sum(c.montant for c in dossier.charges if c.est_droits)
    tpi_saisie = [c.montant for c in dossier.charges if c.est_tpi]
    tpi = sum(tpi_saisie) if tpi_saisie else douane * parametres.taux_tpi_import
    return (douane + droits + tpi) * parametres.taux_tva_import


def ecart_droits(saisis: float, attendus: float | None) -> float | None:
    """L'écart des droits saisis aux attendus quand il est à vérifier (> 2 % et ≥ 50 MAD)."""
    if attendus is None or not saisis:
        return None
    ecart = saisis - attendus
    seuil = max(ECART_DROITS_MINIMUM, attendus * TOLERANCE_DROITS_IMPORT)
    return ecart if abs(ecart) > seuil else None


def ecart_tva_tolere(attendue: float) -> float:
    """L'écart de TVA au-delà duquel la saisie se vérifie (5 %)."""
    return abs(attendue) * TOLERANCE_TVA_IMPORT


def _recuperables(dossier: DossierImport) -> set[str]:
    """Les postes récupérables du dossier : le référentiel des postes le dit."""
    return {c.poste for c in dossier.charges if c.recuperable} | {
        p
        for p in RECUPERABLES
        if not any(c.poste == p and c.recuperable_poste is False for c in dossier.charges)
    }


Directes = dict[int, dict[str, float]]
Globales = dict[tuple[str, str], float]


def _classer_charges(
    dossier: DossierImport, valeurs: dict[int, float]
) -> tuple[Directes, Globales]:
    """Une charge visée sur une ligne lui revient ; une répartition figée garde ses parts
    tant qu'elle couvre tout le frais ; le reste se répartit (valeur ou poids)."""
    directes: Directes = defaultdict(lambda: defaultdict(float))
    globales: Globales = defaultdict(float)
    for charge in dossier.charges:
        if charge.ligne is not None and charge.ligne in valeurs:
            directes[charge.ligne][charge.poste] += charge.montant
        elif (
            charge.parts
            and all(x in valeurs for x in charge.parts)
            and abs(sum(charge.parts.values()) - charge.montant) < CENTIME
        ):
            for ligne_id, montant in charge.parts.items():
                directes[ligne_id][charge.poste] += montant
        else:
            cle = "poids" if charge.cle == "poids" else "valeur"
            globales[(charge.poste, cle)] += charge.montant
    return directes, globales


def revient_dossier(dossier: DossierImport, parametres: Parametres) -> list[LigneRevient]:
    """Répartit les charges d'un dossier sur ses marchandises, sans arrondi."""
    valeurs = {ligne.id: valeur_ligne_import(ligne, parametres) for ligne in dossier.lignes}
    total = sum(valeurs.values())
    poids = {ligne.id: ligne.poids_kg for ligne in dossier.lignes}
    poids_total = sum(poids.values())
    recuperables = _recuperables(dossier)
    directes, globales = _classer_charges(dossier, valeurs)
    resultat = []
    for ligne in dossier.lignes:
        valeur = valeurs[ligne.id]
        part = valeur / total if total else 0.0
        part_poids = poids[ligne.id] / poids_total if poids_total else 0.0
        detail: dict[str, float] = defaultdict(float)
        for (poste, cle), montant in globales.items():
            detail[poste] += montant * (part_poids if cle == "poids" else part)
        for poste, montant in directes.get(ligne.id, {}).items():
            detail[poste] += montant
        resultat.append(
            LigneRevient(
                dossier=dossier.numero,
                ligne_id=ligne.id,
                reference=ligne.reference,
                lot_fournisseur=ligne.lot_fournisseur,
                fournisseur=ligne.fournisseur,
                quantite=ligne.quantite,
                valeur_mad=valeur,
                part=part,
                charges_mad=sum(m for poste, m in detail.items() if poste not in recuperables),
                tva_mad=sum(m for poste, m in detail.items() if poste in recuperables),
                detail=dict(detail),
                poids_kg=poids[ligne.id],
            )
        )
    return resultat


def lignes_aberrantes(repartis: list[LigneRevient], seuil: float) -> list[LigneRevient]:
    """Les marchandises dont les frais hors TVA dépassent le seuil de leur propre valeur."""
    return [
        x
        for x in repartis
        if x.charges_mad > CENTIME and (x.valeur_mad <= 0 or x.charges_mad > x.valeur_mad * seuil)
    ]


def lignes_negatives(repartis: list[LigneRevient]) -> list[LigneRevient]:
    """Les marchandises qu'un avoir rend négatives : une saisie à revoir."""
    return [x for x in repartis if x.revient_mad < -CENTIME]


@dataclass
class EcartFacture:
    """Une facture d'un dossier rapprochée de la marchandise qu'elle a apportée (pesée × prix)."""

    facture: str
    montant: float
    recu: float
    devise: str
    ecart: float
    part: float
    tolerance: float
    hors_tolerance: bool


def lignes_de_la_facture(dossier: DossierImport, facture: FactureImport) -> list[LigneImport]:
    """Les marchandises du dossier que cette facture a apportées."""
    siennes = set(facture.lignes)
    return [x for x in dossier.lignes if x.id in siennes]


def ecart_facture(
    dossier: DossierImport, facture: FactureImport, parametres: Parametres
) -> EcartFacture | None:
    """Une facture rapprochée de **sa** marchandise reçue (pesée × prix) : rien sans montant,
    sans marchandise, ou avec une marchandise hors de sa devise (jamais d'addition entre
    devises)."""
    lignes = lignes_de_la_facture(dossier, facture)
    if not facture.montant or not lignes:
        return None
    if any((x.devise or "MAD") != (facture.devise or "MAD") for x in lignes):
        return None
    recu = sum(x.valeur_devise for x in lignes)
    ecart = facture.montant - recu
    part = ecart / recu if recu else 1.0
    return EcartFacture(
        facture=facture.numero,
        montant=facture.montant,
        recu=recu,
        devise=facture.devise,
        ecart=ecart,
        part=part,
        tolerance=parametres.toler_facture_import,
        hors_tolerance=abs(ecart) > CENTIME and abs(part) > parametres.toler_facture_import,
    )


def ecarts_factures(dossier: DossierImport, parametres: Parametres) -> list[EcartFacture]:
    """Chaque facture du dossier rapprochée de sa marchandise (C36 facture par facture)."""
    ecarts = (ecart_facture(dossier, f, parametres) for f in dossier.factures)
    return [e for e in ecarts if e is not None]


def revient_par_reception(donnees: Donnees) -> dict[int, LigneRevient]:
    """Le coût de revient indexé par ligne de réception (le CMUP valorise une entrée à ce
    qu'elle a réellement coûté)."""
    index: dict[int, LigneRevient] = {}
    for dossier in donnees.dossiers_import:
        lignes = {x.id: x for x in dossier.lignes}
        for revient in revient_dossier(dossier, donnees.parametres):
            origine = lignes[revient.ligne_id].ligne_reception_id
            if origine is not None:
                index[origine] = revient
    return index


def revient_par_lot(donnees: Donnees) -> dict[tuple[str, str], float]:
    """Coût de revient unitaire par (référence, lot) des marchandises saisies à la main (sans
    ligne de réception) ; deux lignes du même lot se moyennent au poids."""
    cumul: dict[tuple[str, str], list[float]] = defaultdict(lambda: [0.0, 0.0])
    for dossier in donnees.dossiers_import:
        origine = {x.id: x.ligne_reception_id for x in dossier.lignes}
        for revient in revient_dossier(dossier, donnees.parametres):
            if origine.get(revient.ligne_id) is not None:
                continue
            if revient.lot_fournisseur and revient.revient_unite:
                bloc = cumul[(revient.reference, revient.lot_fournisseur)]
                bloc[0] += revient.quantite
                bloc[1] += revient.revient_mad
    return {cle: b[1] / b[0] for cle, b in cumul.items() if b[0] > 0}
