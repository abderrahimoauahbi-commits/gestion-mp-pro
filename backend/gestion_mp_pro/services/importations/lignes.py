"""Les marchandises d'un dossier lues une à une : coût de revient, cours, valeur en douane et
droits attendus, et ce que le dossier en tire (familles, pièces, cours disparates) — REGLES
R-IMP-05 à R-IMP-13 (`gestion_mp/api/importations.py`, `dossier_dict`).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from gestion_mp_pro.calcul.importations import LigneRevient
from gestion_mp_pro.modeles import CodeDouanier, Dossier, DossierLigne
from gestion_mp_pro.services.importations.modele import (
    CoursDisparates,
    Famille,
    LigneDossier,
    MatiereCitee,
    Piece,
    ReceptionCitee,
)
from gestion_mp_pro.services.importations.socle import DIRHAM, Contexte, lignes_triees

ECART_COURS = 0.05
"""Un cours saisi à plus de 5 % du cours du jour : une devise confondue, une faute de frappe."""
DECIMALES_COURS = 6


@dataclass
class _Groupe:
    """Une famille de fil en cours de compte."""

    references: set[int] = field(default_factory=set)
    lots: set[int | str] = field(default_factory=set)
    quantite: float = 0.0
    valeur_mad: float = 0.0
    charges_mad: float = 0.0


@dataclass
class Marchandises:
    """Les marchandises lues, et ce que le dossier en tire."""

    lignes: list[LigneDossier] = field(default_factory=list)
    droits_attendus: float = 0.0
    sans_code: dict[int, str] = field(default_factory=dict)
    inactifs: dict[int, str] = field(default_factory=dict)
    cours_par_devise: dict[str, set[float]] = field(default_factory=lambda: defaultdict(set))
    au_cours_du_bon: int = 0
    pieces: dict[str | None, set[str]] = field(default_factory=lambda: defaultdict(set))
    receptions: dict[int, str] = field(default_factory=dict)
    apporte: dict[int, float] = field(default_factory=lambda: defaultdict(float))
    groupes: dict[str, _Groupe] = field(default_factory=dict)

    @property
    def matieres_sans_code(self) -> list[MatiereCitee]:
        """Les matières sans code douanier actif (codes désactivés compris)."""
        return [MatiereCitee(i, r) for i, r in sorted(self.sans_code.items(), key=lambda z: z[1])]

    @property
    def matieres_code_inactif(self) -> list[MatiereCitee]:
        """Les matières dont le code douanier est désactivé."""
        return [MatiereCitee(i, r) for i, r in sorted(self.inactifs.items(), key=lambda z: z[1])]

    @property
    def cours_disparates(self) -> list[CoursDisparates]:
        """Les devises à plusieurs cours dans le dossier : à dire avant de clore (R-IMP-12)."""
        return [
            CoursDisparates(devise, sorted(cours))
            for devise, cours in sorted(self.cours_par_devise.items())
            if len(cours) > 1
        ]

    @property
    def cours_eloignes(self) -> int:
        """Les marchandises à un cours éloigné de plus de 5 % du cours du jour."""
        return sum(1 for x in self.lignes if x.cours_ecart is not None)

    def liste_pieces(self) -> list[Piece]:
        """Chaque facture et ses réceptions (les marchandises sans facture à la fin)."""
        ordre = sorted(self.pieces.items(), key=lambda z: (z[0] is None, z[0] or ""))
        return [Piece(f, sorted(r)) for f, r in ordre]

    def liste_receptions(self) -> list[ReceptionCitee]:
        """Les réceptions du dossier, par numéro."""
        return [
            ReceptionCitee(i, n) for i, n in sorted(self.receptions.items(), key=lambda z: z[1])
        ]

    def familles(self) -> list[Famille]:
        """Les familles de fil, la plus lourde d'abord (R-IMP-13)."""
        resultat = [
            Famille(
                famille=nom,
                references=len(g.references),
                lots=len(g.lots),
                quantite=g.quantite,
                valeur_mad=g.valeur_mad,
                charges_mad=g.charges_mad,
                revient_mad=g.valeur_mad + g.charges_mad,
                valeur_kg=g.valeur_mad / g.quantite if g.quantite else 0.0,
                revient_kg=(g.valeur_mad + g.charges_mad) / g.quantite if g.quantite else 0.0,
                surcout=g.charges_mad / g.valeur_mad if g.valeur_mad else 0.0,
            )
            for nom, g in self.groupes.items()
        ]
        return sorted(resultat, key=lambda g: -g.quantite)


def cours_ecart(cours: float, cours_jour: float, devise: str) -> float | None:
    """L'écart d'un cours saisi au cours du jour, au-delà de 5 % ; sinon `None`."""
    if not cours or not cours_jour or devise == DIRHAM:
        return None
    ecart = cours / cours_jour - 1
    return ecart if abs(ecart) > ECART_COURS else None


class _Lecteur:
    """Lit les marchandises d'un dossier dans son contexte."""

    def __init__(self, ctx: Contexte, revient: dict[int, LigneRevient]) -> None:
        self.ctx = ctx
        self.revient = revient
        self.m = Marchandises()
        self.douane = {p.code for p in ctx.postes.values() if p.entre_valeur_douane}

    def droits(
        self, x: DossierLigne, r: LigneRevient
    ) -> tuple[float, float | None, CodeDouanier | None]:
        """Valeur en douane (achat + les frais qui y entrent : fret, assurance — le drapeau
        `entre_valeur_douane` du poste), droits attendus, code actif."""
        douane = r.valeur_mad + sum(r.detail.get(p, 0.0) for p in self.douane)
        matiere = self.ctx.matieres[x.matiere_id]
        code = self.ctx.codes.get(matiere.code_douanier_id) if matiere.code_douanier_id else None
        if code is not None and not code.actif:
            self.m.inactifs[x.matiere_id] = matiere.reference
            code = None
        if code is None:
            self.m.sans_code[x.matiere_id] = matiere.reference
            return douane, None, None
        attendu = douane * float(code.taux_droits)
        self.m.droits_attendus += attendu
        return douane, attendu, code

    def cours(self, x: DossierLigne) -> tuple[float, float, float | None]:
        """Cours du jour, cours appliqué, écart au cours du jour ; cours retenus par devise."""
        p = self.ctx.parametres
        jour = 1.0 if x.devise == DIRHAM else p.taux(x.devise)
        applique = 1.0 if x.devise == DIRHAM else float(x.cours or 0) or jour
        if x.devise != DIRHAM:
            self.m.cours_par_devise[x.devise].add(round(applique, DECIMALES_COURS))
            bon = self.ctx.bons.get(x.reception_ligne_id) if x.reception_ligne_id else None
            if x.cours and bon and bon.devise == x.devise and x.cours == bon.cours:
                self.m.au_cours_du_bon += 1
        return jour, applique, cours_ecart(float(x.cours or 0), jour, x.devise)

    def origine(self, x: DossierLigne) -> tuple[int | None, str | None, str | None]:
        """La réception et la facture d'une marchandise reçue ; les pièces du dossier."""
        o = self.ctx.origines.get(x.reception_ligne_id) if x.reception_ligne_id else None
        if o is None:
            return None, None, None
        facture = self.ctx.factures.get(o.facture_id) if o.facture_id else None
        self.m.pieces[facture.numero if facture else None].add(o.reception)
        self.m.receptions[o.reception_id] = o.reception
        if facture is not None:
            self.m.apporte[facture.id] += float(x.valeur_devise)
        return o.reception_id, o.reception, facture.numero if facture else None

    def grouper(self, x: DossierLigne, nom: str, r: LigneRevient) -> None:
        """La marchandise compte dans sa famille de fil (au poids)."""
        g = self.m.groupes.setdefault(nom, _Groupe())
        g.references.add(x.matiere_id)
        g.lots.add(x.lot_id or f"ligne {x.id}")
        g.quantite += r.poids_kg
        g.valeur_mad += r.valeur_mad
        g.charges_mad += r.charges_mad

    def lire(self, x: DossierLigne, aberrantes: set[int], negatives: set[int]) -> LigneDossier:
        """Une marchandise : origine, cours, coût, douane."""
        r = self.revient[x.id]
        matiere = self.ctx.matieres[x.matiere_id]
        reception_id, reception, facture = self.origine(x)
        jour, applique, ecart = self.cours(x)
        douane, attendu, code = self.droits(x, r)
        bon = self.ctx.bons.get(x.reception_ligne_id) if x.reception_ligne_id else None
        meme = bon is not None and bon.devise == x.devise
        self.grouper(x, matiere.famille, r)
        return LigneDossier(
            id=x.id,
            reception_ligne_id=x.reception_ligne_id,
            reception_id=reception_id,
            reception=reception,
            facture=facture,
            famille=matiere.famille,
            matiere_id=x.matiere_id,
            reference=matiere.reference,
            lot_id=x.lot_id,
            lot=self.ctx.lots.get(x.lot_id, "") if x.lot_id else "",
            fournisseur_id=x.fournisseur_id,
            fournisseur=self.ctx.nom(x.fournisseur_id),
            quantite_kg=x.quantite_kg,
            valeur_devise=x.valeur_devise,
            devise=x.devise,
            cours=x.cours,
            cours_origine=str(x.cours_origine) if x.cours_origine else None,
            cours_applique=applique,
            cours_jour=jour,
            cours_bon=bon.cours if bon and meme else None,
            bon=bon.numero if bon else None,
            bon_id=bon.commande_id if bon else None,
            cours_ecart=ecart,
            valeur_mad=r.valeur_mad,
            part=r.part,
            charges_mad=r.charges_mad,
            tva_mad=r.tva_mad,
            revient_mad=r.revient_mad,
            valeur_kg=r.valeur_unite,
            revient_kg=r.revient_mad / r.poids_kg if r.poids_kg else None,
            surcout=r.surcout,
            frais_par_poste=dict(r.detail),
            aberrante=x.id in aberrantes,
            negative=x.id in negatives,
            commentaire=x.commentaire,
            code_douanier=code.code if code else None,
            taux_droits=code.taux_droits if code else None,
            valeur_douane_mad=douane,
            droits_attendus_mad=attendu,
        )


def lire_marchandises(
    d: Dossier,
    ctx: Contexte,
    revient: dict[int, LigneRevient],
    aberrantes: set[int],
    negatives: set[int],
) -> Marchandises:
    """Les marchandises du dossier et ce qu'il en tire."""
    lecteur = _Lecteur(ctx, revient)
    lecteur.m.lignes = [lecteur.lire(x, aberrantes, negatives) for x in lignes_triees(d)]
    return lecteur.m
