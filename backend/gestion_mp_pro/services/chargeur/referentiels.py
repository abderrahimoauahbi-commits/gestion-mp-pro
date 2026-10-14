"""Réglages, fournisseurs, matières, magasins, métiers et poids de bobine mesurés, pour le
moteur (CALCULS A § 4.4, § 4.6 ; `parametres.pour_le_moteur`, `depot._charger`).
"""

from __future__ import annotations

from dataclasses import fields

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from gestion_mp_pro.calcul import modele as c
from gestion_mp_pro.modeles import (
    CLES_REGLAGES,
    Composition,
    Couleur,
    Devise,
    Fournisseur,
    Lot,
    Magasin,
    Matiere,
    Metier,
    Montage,
    Mouvement,
    Parametre,
    Titrage,
    TypeFil,
)
from gestion_mp_pro.modeles.enums import TypeMagasin, TypeMouvement
from gestion_mp_pro.services.chargeur.contexte import Noms, nombre, nombre_ou_rien

TYPES_MAGASIN = {TypeMagasin.stock_courant: "Stock courant", TypeMagasin.quarantaine: "Quarantaine"}
"""Type d'un magasin en base → libellé du moteur (« Quarantaine » retient la marchandise)."""


def parametres(s: Session) -> c.Parametres:
    """Les réglages tels que le moteur les attend : chaque champ de `Parametres` qui est une
    clé de réglage prend sa valeur (texte pour un réglage texte, nombre sinon ; un nombre
    illisible ou vide garde le défaut) ; les cours sont ceux de la table des devises."""
    valeurs = dict(s.execute(select(Parametre.cle, Parametre.valeur)).all())
    p = c.Parametres()
    for f in fields(c.Parametres):
        if f.name not in valeurs or f.name not in CLES_REGLAGES:
            continue
        brut = valeurs[f.name]
        if isinstance(getattr(p, f.name), str):
            setattr(p, f.name, brut)
            continue
        try:
            setattr(p, f.name, float(brut))
        except ValueError:
            continue
    p.cours = {
        code: float(cours)
        for code, cours in s.execute(select(Devise.code, Devise.cours).order_by(Devise.code))
    }
    p.taux_eur_mad = p.cours.get("EUR", p.taux_eur_mad)
    p.taux_usd_mad = p.cours.get("USD", p.taux_usd_mad)
    return p


def fournisseurs(s: Session) -> list[c.Fournisseur]:
    """Les fournisseurs, dans l'ordre de leurs identifiants."""
    return [
        c.Fournisseur(
            nom=f.nom,
            code=f.code,
            contact=f.contact,
            telephone=f.telephone,
            email=f.email,
            pays=f.pays,
            delai_jours=float(f.delai_jours),
            conditions_paiement=f.conditions_paiement,
            devise=f.devise,
            delai_paiement_jours=float(f.delai_paiement_jours),
            couverture_commande_jours=float(f.couverture_commande_jours),
            actif=f.actif,
        )
        for f in s.scalars(select(Fournisseur).order_by(Fournisseur.id))
    ]


def _classification(s: Session) -> tuple[dict[int, Composition], dict[int, str], dict[int, Titrage],
                                         dict[int, Couleur]]:  # fmt: skip
    """Les quatre tables de classification, par identifiant."""
    return (
        {x.id: x for x in s.scalars(select(Composition))},
        dict(s.execute(select(TypeFil.id, TypeFil.code)).all()),
        {x.id: x for x in s.scalars(select(Titrage))},
        {x.id: x for x in s.scalars(select(Couleur))},
    )


def articles(s: Session, noms: Noms) -> list[c.Article]:
    """Les matières par référence (ordre de la base) : nature = libellé de la composition,
    couleur = son libellé sinon son code ; unité de commande vide quand on achète au kilo."""
    compositions, types_fil, titrages, couleurs = _classification(s)
    resultat = []
    for a in s.scalars(select(Matiere).order_by(Matiere.reference)):
        composition = compositions.get(a.composition_id) if a.composition_id else None
        titrage = titrages.get(a.titrage_id) if a.titrage_id else None
        couleur = couleurs.get(a.couleur_id) if a.couleur_id else None
        au_kilo = a.unite_achat == "kg"
        resultat.append(
            c.Article(
                reference=a.reference,
                role_bom=noms.roles.get(a.role_id, ""),
                nature=composition.libelle if composition else "",
                designation=a.designation,
                titrage=titrage.valeur if titrage else "",
                unite_prix=str(a.unite_prix) or "kg",
                fournisseur=noms.fournisseur(a.fournisseur_id),
                prix_unite=nombre(a.prix),
                devise=a.devise,
                stock_min=nombre(a.stock_min),
                couv_min_mois=nombre(a.couv_min_mois),
                poids_bobine=nombre(a.poids_bobine),
                bob_palette=nombre(a.bobines_palette),
                unite_commande="" if au_kilo else a.unite_achat,
                contenance_commande=0.0 if au_kilo else nombre(a.contenance_achat),
                minimum_commande=nombre(a.minimum_commande),
                actif=a.actif,
                densite=nombre(a.densite),
                groupe_equiv=a.groupe_equiv,
                priorite_equiv=nombre_ou_rien(a.priorite_equiv),
                composition=composition.code if composition else "",
                type_fil=types_fil.get(a.type_fil_id, "") if a.type_fil_id else "",
                couleur=(couleur.libelle or couleur.code) if couleur else "",
                couleur_code=a.couleur_code,
                titrage_unite=titrage.unite if titrage else "",
            )
        )
    return resultat


def magasins(s: Session) -> list[c.Magasin]:
    """Les magasins (le contenu n'est pas tenu par le moteur)."""
    return [
        c.Magasin(code=g.code, nom=g.nom, type=TYPES_MAGASIN[g.type], actif=g.actif)
        for g in s.scalars(select(Magasin).order_by(Magasin.id))
    ]


ENTREES_DU_LOT = {
    TypeMouvement.RECEPTION.value: "reçu",
    TypeMouvement.OUVERTURE.value: "ouvert",
    TypeMouvement.AJUSTEMENT.value: "ajusté",
    TypeMouvement.RETOUR_MACHINE.value: "revenu des machines",
}
"""Comment un lot pesé est entré : le type de sa première écriture positive → le mot dit."""


def _entrees_des_lots(s: Session) -> dict[int, str]:
    """Le type de la première écriture positive de chaque lot (comment il est entré)."""
    premieres = (
        select(Mouvement.lot_id, func.min(Mouvement.id).label("id"))
        .where(Mouvement.quantite > 0, Mouvement.contrepasse_id.is_(None))
        .group_by(Mouvement.lot_id)
        .subquery()
    )
    requete = select(premieres.c.lot_id, Mouvement.type).join(
        Mouvement, Mouvement.id == premieres.c.id
    )
    return {lot: str(type_) for lot, type_ in s.execute(requete)}


def poids_bobine_mesures(s: Session) -> dict[int, tuple[float, str, str]]:
    """Le poids d'une bobine pesé, matière par matière (M43) : celui du lot sorti le plus
    récemment vers les machines (une sortie annulée n'a rien monté), sinon celui du dernier
    lot entré, quelle que soit son entrée — une ouverture ou un ajustement pesés sont réels
    (audit 2). {matière : (kg par bobine, n° de lot, « sorti » | « reçu » | « ouvert » |
    « ajusté » | « entré »)} : le mot dit comment le lot est entré, sans mentir."""
    annulees = select(Mouvement.contrepasse_id).where(Mouvement.contrepasse_id.is_not(None))
    pesees: dict[int, tuple[float, str, str]] = {}
    sorties = (
        select(Mouvement.matiere_id, Lot.poids_bobine, Lot.numero)
        .join(Lot, Lot.id == Mouvement.lot_id)
        .where(
            Mouvement.type == TypeMouvement.SORTIE,
            Mouvement.quantite < 0,
            Lot.poids_bobine > 0,
            Mouvement.contrepasse_id.is_(None),
            Mouvement.id.not_in(annulees),
        )
        .order_by(Mouvement.matiere_id, Mouvement.date_effet.desc(), Mouvement.id.desc())
    )
    for matiere, poids, numero in s.execute(sorties):
        pesees.setdefault(matiere, (float(poids), numero, "sorti"))
    entres = (
        select(Lot.id, Lot.matiere_id, Lot.poids_bobine, Lot.numero)
        .where(Lot.poids_bobine > 0)
        .order_by(Lot.matiere_id, Lot.entre_le.desc(), Lot.id.desc())
    )
    entrees = None
    for ident, matiere, poids, numero in s.execute(entres):
        if matiere in pesees:
            continue
        if entrees is None:
            entrees = _entrees_des_lots(s)
        genre = ENTREES_DU_LOT.get(entrees.get(ident, ""), "entré")
        pesees[matiere] = (float(poids), numero, genre)
    return pesees


def metiers(s: Session, noms: Noms) -> list[c.Metier]:
    """Les métiers par code et le fil monté (poids d'une bobine : celui mesuré, sinon 0)."""
    pesees = poids_bobine_mesures(s)
    montages: dict[int, list[c.FilMonte]] = {}
    for f in s.scalars(select(Montage).order_by(Montage.id)):
        montages.setdefault(f.metier_id, []).append(
            c.FilMonte(
                reference=noms.references[f.matiere_id],
                etage=f.etage,
                metres=nombre(f.metres),
                pourcentage=nombre(f.pourcentage),
                poids_bobine=pesees.get(f.matiere_id, (0.0, "", ""))[0],
            )
        )
    return [
        c.Metier(
            code=x.code,
            nom=x.nom,
            laize=nombre(x.laize),
            densite=nombre(x.bobines_par_metre),
            etages=x.etages,
            actif=x.actif,
            fils=montages.get(x.id, []),
        )
        for x in s.scalars(select(Metier).order_by(Metier.code))
    ]
