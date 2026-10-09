"""Un jeu figé de S3 (`tests/moteur/jeux/`) réécrit en base PRO, première partie (lot S4) :
réglages, comptes, référentiels, matières, magasins, qualités, recettes, bons de commande.

C'est la reprise à l'envers : chaque structure du moteur devient les lignes de la base que le
chargeur relit. Les valeurs sont arrondies à l'échelle des colonnes (K1, MODELE-DONNEES § 10.2).
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from datetime import date, datetime

from fabriques.moteur_base import ajouter
from sqlalchemy import delete, insert, select, update
from sqlalchemy.orm import Session

from gestion_mp_pro.calcul import modele as c
from gestion_mp_pro.modeles import (
    CLES_REGLAGES,
    Commande,
    CommandeLigne,
    Composition,
    Couleur,
    Devise,
    Fournisseur,
    Magasin,
    Matiere,
    Parametre,
    Qualite,
    QualitePoids,
    QualiteSaison,
    Recette,
    RecetteVersion,
    RecetteVersionLigne,
    RecetteVersionPoids,
    RoleNomenclature,
    Titrage,
    TypeFil,
    Utilisateur,
)
from gestion_mp_pro.modeles.enums import OrigineSolde
from gestion_mp_pro.services import horloge

STATUTS = {
    "Brouillon": "brouillon",
    "Envoyée": "envoyee",
    "Confirmée": "confirmee",
    "Soldée": "soldee",
    "Annulée": "annulee",
}
TYPES_MAGASIN = {"Stock courant": "stock_courant", "Quarantaine": "quarantaine"}


def instant(jour: date | datetime) -> datetime:
    """Un instant du moteur (sans fuseau, heure de l'usine) ou un jour (midi) pour la base."""
    if isinstance(jour, datetime):
        return jour.replace(tzinfo=horloge.FUSEAU)
    return datetime(jour.year, jour.month, jour.day, 12, tzinfo=horloge.FUSEAU)


@dataclass
class Index:
    """Les identifiants donnés en base, par clé du moteur."""

    comptes: dict[str, int] = field(default_factory=dict)
    fournisseurs: dict[str, int] = field(default_factory=dict)
    matieres: dict[str, int] = field(default_factory=dict)
    roles: dict[str, int] = field(default_factory=dict)
    role_de: dict[str, int] = field(default_factory=dict)
    magasins: dict[str, int] = field(default_factory=dict)
    qualites: dict[str, int] = field(default_factory=dict)
    lignes_bc: dict[tuple[str, str], int] = field(default_factory=dict)
    lots: dict[tuple[str, str], int] = field(default_factory=dict)
    ordres: dict[str, int] = field(default_factory=dict)
    factures: dict[str, int] = field(default_factory=dict)
    devises_bc: dict[str, str] = field(default_factory=dict)


def reglages(s: Session, p: c.Parametres) -> None:
    """Les réglages du moteur et la table des devises."""
    for f in fields(c.Parametres):
        if f.name in CLES_REGLAGES:
            valeur = getattr(p, f.name)
            texte = valeur if isinstance(valeur, str) else repr(float(valeur))
            s.execute(update(Parametre).where(Parametre.cle == f.name).values(valeur=texte))
    for code, cours in p.cours.items():
        if s.get(Devise, code) is None:
            s.add(Devise(code=code, nom=code, cours=cours))
        elif code != "MAD":
            s.execute(update(Devise).where(Devise.code == code).values(cours=cours))
    s.flush()


def comptes(s: Session, d: c.Donnees, ix: Index) -> None:
    """Un compte historique par nom cité (auteur, réceptionnaire, contrôleur)."""
    noms = {m.utilisateur for m in d.mouvements}
    noms |= {r.receptionnaire for r in d.receptions} | {r.controleur_qualite for r in d.receptions}
    for i, nom in enumerate(sorted(n for n in noms if n)):
        u = ajouter(s, Utilisateur(identifiant=f"jeu.{i}", nom=nom, historique=True, actif=False))
        ix.comptes[nom] = u.id


def _classification(s: Session, a: c.Article) -> dict[str, int | None]:
    """Composition, type de fil, titrage et couleur de la matière (créés au besoin)."""
    ids: dict[str, int | None] = {}
    for cle, modele, code, champs in (
        ("composition_id", Composition, a.composition, {"libelle": a.nature}),
        ("type_fil_id", TypeFil, a.type_fil, {}),
        (
            "titrage_id",
            Titrage,
            f"{a.titrage} {a.titrage_unite}".strip(),
            {"valeur": a.titrage or "", "unite": a.titrage_unite},
        ),
        ("couleur_id", Couleur, a.couleur, {}),
    ):
        if not code:
            ids[cle] = None
            continue
        trouve = s.scalar(select(modele.id).where(modele.code == code))  # type: ignore[attr-defined]
        ids[cle] = trouve or ajouter(s, modele(code=code, **champs)).id
    return ids


def referentiels(s: Session, d: c.Donnees, ix: Index) -> None:
    """Fournisseurs, rôles, matières, magasins (dans l'ordre du jeu)."""
    for f in d.fournisseurs:
        ix.fournisseurs[f.nom] = ajouter(
            s,
            Fournisseur(
                nom=f.nom,
                code=f.code,
                contact=f.contact,
                telephone=f.telephone,
                email=f.email,
                pays=f.pays.upper(),
                delai_jours=int(f.delai_jours),
                devise=f.devise,
                conditions_paiement=f.conditions_paiement,
                actif=f.actif,
                delai_paiement_jours=int(f.delai_paiement_jours),
                couverture_commande_jours=int(f.couverture_commande_jours),
            ),
        ).id
    ix.roles = dict(s.execute(select(RoleNomenclature.code, RoleNomenclature.id)).all())
    for a in d.articles:
        m = ajouter(
            s,
            Matiere(
                reference=a.reference,
                designation=a.designation,
                role_id=ix.roles[a.role_bom],
                couleur_code=a.couleur_code,
                unite_prix=a.unite_prix,
                densite=a.densite,
                fournisseur_id=ix.fournisseurs.get(a.fournisseur),
                prix=a.prix_unite,
                devise=a.devise,
                unite_achat=a.unite_commande if a.contenance_commande else "kg",
                contenance_achat=a.contenance_commande or 1,
                minimum_commande=a.minimum_commande,
                poids_bobine=a.poids_bobine,
                bobines_palette=a.bob_palette,
                stock_min=a.stock_min,
                couv_min_mois=a.couv_min_mois,
                groupe_equiv=a.groupe_equiv,
                priorite_equiv=a.priorite_equiv,
                actif=a.actif,
                **_classification(s, a),
            ),
        )
        ix.matieres[a.reference], ix.role_de[a.reference] = m.id, m.role_id
    s.execute(delete(Magasin))
    for g in d.magasins:
        ix.magasins[g.code] = ajouter(
            s, Magasin(code=g.code, nom=g.nom, type=TYPES_MAGASIN[g.type], actif=g.actif)
        ).id


def qualites(s: Session, d: c.Donnees, ix: Index) -> None:
    """Qualités, poids, saisonnalité, recettes et leurs versions."""
    plans = {p.qualite: p for p in d.plan}
    for q in d.qualites:
        p = plans[q.code]
        qid = ajouter(
            s, Qualite(code=q.code, nom=q.nom, base_mensuelle=p.base_mensuelle, actif=p.actif)
        ).id
        ix.qualites[q.code] = qid
        s.add_all(
            QualitePoids(qualite_id=qid, role_id=ix.roles[r], poids=kg) for r, kg in q.poids.items()
        )
        s.add_all(
            QualiteSaison(qualite_id=qid, mois=i + 1, coefficient=k)
            for i, k in enumerate(p.saisonnalite)
        )
    s.add_all(
        Recette(
            qualite_id=ix.qualites[r.qualite],
            matiere_id=ix.matieres[r.reference],
            pourcentage=r.pourcentage,
        )
        for r in d.recettes
    )
    for code, versions in d.versions_recette.items():
        for i, v in enumerate(versions):
            rv = ajouter(
                s,
                RecetteVersion(
                    qualite_id=ix.qualites[code],
                    numero=i + 1,
                    valide_depuis=instant(v.quand),
                    poids_connus=v.poids is not None,
                ),
            )
            s.add_all(
                RecetteVersionLigne(
                    version_id=rv.id,
                    matiere_id=ix.matieres[ref],
                    role_id=ix.role_de[ref],
                    pourcentage=pct,
                )
                for ref, pct in v.lignes
            )
            s.add_all(
                RecetteVersionPoids(version_id=rv.id, role_id=ix.roles[r], poids=kg)
                for r, kg in (v.poids or {}).items()
            )
    s.flush()


def commandes(s: Session, d: c.Donnees, ix: Index) -> None:
    """Les bons et leurs lignes (cours figé du bon s'il en a un)."""
    for cmd in d.commandes:
        devise = cmd.lignes[0].devise if cmd.lignes else "MAD"
        cours = cmd.lignes[0].cours if cmd.lignes and devise != "MAD" else 0.0
        statut = STATUTS[cmd.statut]
        ix.devises_bc[cmd.numero] = devise
        clos = statut in ("soldee", "annulee")
        bc = ajouter(
            s,
            Commande(
                numero=None if cmd.numero.startswith("BC-brouillon") else cmd.numero,
                statut=statut,
                fournisseur_id=ix.fournisseurs[cmd.fournisseur],
                date_commande=cmd.date_bc,
                date_livraison_prevue=cmd.date_livraison_prevue,
                eta=cmd.eta,
                devise=devise,
                cours=cours or None,
                cours_fige_le=instant(cmd.date_bc) if cours else None,  # type: ignore[arg-type]
                observations=cmd.observations,
                solde_origine=(
                    OrigineSolde.manuel
                    if cmd.solde_a_la_main_le or cmd.annulee_le
                    else OrigineSolde.automatique
                )
                if clos
                else None,
                solde_le=instant(cmd.solde_a_la_main_le or cmd.annulee_le)  # type: ignore[arg-type]
                if cmd.solde_a_la_main_le or cmd.annulee_le
                else None,
            ),
        )
        for x in cmd.lignes:
            ix.lignes_bc[(cmd.numero, x.reference)] = ajouter(
                s,
                CommandeLigne(
                    commande_id=bc.id,
                    matiere_id=ix.matieres[x.reference],
                    quantite=x.quantite_commandee,
                    unite_achat=x.unite_commande or "kg",
                    contenance=x.contenance_commande or 1,
                    prix=x.prix_unite,
                    prix_confirme=x.prix_confirme,
                    confirme_le=instant(cmd.date_bc) if x.prix_confirme and cmd.date_bc else None,  # type: ignore[arg-type]
                ),
            ).id


def inserer(s: Session, modele: type, lignes: list[dict[str, object]]) -> None:
    """Une insertion groupée (une requête)."""
    if lignes:
        s.execute(insert(modele), lignes)
