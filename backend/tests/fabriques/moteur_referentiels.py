"""La petite usine du chargeur, première partie : référentiels, qualités, bons (lot S4)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from fabriques.moteur_base import Monde, ajouter, instant
from fabriques.stock import fournisseur, matiere, role, utilisateur
from sqlalchemy.orm import Session

from gestion_mp_pro.modeles import (
    Commande,
    CommandeLigne,
    Composition,
    Couleur,
    Parametre,
    PlanVersion,
    PlanVersionSaison,
    Qualite,
    QualitePoids,
    QualiteSaison,
    Recette,
    RecetteVersion,
    RecetteVersionLigne,
    RecetteVersionPoids,
    Titrage,
    TypeFil,
)
from gestion_mp_pro.modeles.enums import OrigineSolde


def referentiels(s: Session, w: Monde) -> None:
    """Réglages, classification, comptes, fournisseurs, matières."""
    for cle, valeur in (
        ("toler_ecart_pesee", "0.03"),
        ("seuil_alerte", "95"),
        ("nom_entreprise", "Tapis Essai"),
        ("dso", "illisible"),
    ):
        p = s.get(Parametre, cle)
        assert p is not None
        p.valeur = valeur
    pp = ajouter(s, Composition(code="PP", libelle="Polypropylène"))
    frise = ajouter(s, TypeFil(code="FRZ", libelle="Frisé"))
    titre = ajouter(s, Titrage(code="2900 Dtex", valeur="2900", unite="Dtex"))
    rouge = ajouter(s, Couleur(code="R01", libelle="Rouge"))
    karim, sara = utilisateur(s, "Karim — magasin"), utilisateur(s, "Sara")
    hasirci = fournisseur(
        s, "HASIRCI", "USD", code="FRS-1", contact="ETHEM", delai_jours=65,
        couverture_commande_jours=60, delai_paiement_jours=180,
    )  # fmt: skip
    local = fournisseur(s, "LOCAL PLAST")
    rouge_pp = matiere(
        s, "PP Rouge", "Poil", hasirci.id, designation="Rouge vif", composition_id=pp.id,
        type_fil_id=frise.id, titrage_id=titre.id, couleur_id=rouge.id, prix=Decimal("2.5"),
        devise="USD", poids_bobine=Decimal("2.5"), bobines_palette=40, unite_achat="Palette",
        contenance_achat=100, stock_min=50, couv_min_mois=Decimal("1.5"), groupe_equiv="G1",
        priorite_equiv=1,
    )  # fmt: skip
    cuir = matiere(s, "Cuir brun", "Cuir", local.id, unite_prix="ml", prix=Decimal("0.0196"))
    jute = matiere(s, "Jute", "Trame", local.id, prix=12)
    w.ids |= {
        "karim": karim.id,
        "sara": sara.id,
        "hasirci": hasirci.id,
        "local": local.id,
        "pp": rouge_pp.id,
        "cuir": cuir.id,
        "jute": jute.id,
    }


def qualites(s: Session, w: Monde) -> None:
    """Deux qualités (une arrêtée), recettes, plan et recettes versionnés."""
    roles = {"Poil": "pp", "Trame": "jute", "Cuir": "cuir"}
    q = ajouter(s, Qualite(code="8F", nom="8F MOSQUEE", base_mensuelle=2500))
    for code, poids in (("Poil", "1.53"), ("Trame", "0.4"), ("Cuir", "1")):
        s.add(QualitePoids(qualite_id=q.id, role_id=role(s, code).id, poids=Decimal(poids)))
        s.add(Recette(qualite_id=q.id, matiere_id=w.ids[roles[code]], pourcentage=100))
    s.add(QualiteSaison(qualite_id=q.id, mois=1, coefficient=Decimal("1.2")))
    vieille = ajouter(s, Qualite(code="OLD", nom="Arrêtée", base_mensuelle=300, actif=False))
    for quand, base, janvier in (
        (instant(2000, 1, 1), 2000, None),
        (instant(2026, 3, 1), 2500, "1.2"),
        (instant(2026, 6, 1), 2500, "1.3"),
    ):
        v = ajouter(s, PlanVersion(qualite_id=q.id, valide_depuis=quand, base_mensuelle=base))
        if janvier:
            s.add(PlanVersionSaison(version_id=v.id, mois=1, coefficient=Decimal(janvier)))
    for numero, quand, avec_poids in (
        (1, instant(2026, 2, 1), False),
        (2, instant(2026, 5, 1), True),
    ):
        v = ajouter(
            s,
            RecetteVersion(
                qualite_id=q.id, numero=numero, valide_depuis=quand, poids_connus=avec_poids
            ),
        )
        for cle, role_id in (("pp", "Poil"), ("jute", "Trame")):
            s.add(
                RecetteVersionLigne(
                    version_id=v.id,
                    matiere_id=w.ids[cle],
                    role_id=role(s, role_id).id,
                    pourcentage=100,
                )
            )
        if avec_poids:
            s.add(
                RecetteVersionPoids(
                    version_id=v.id, role_id=role(s, "Poil").id, poids=Decimal("1.53")
                )
            )
    s.flush()
    w.ids |= {"8f": q.id, "old": vieille.id}


def commandes(s: Session, w: Monde) -> None:
    """Un bon parti, un brouillon, un bon soldé à la main, un bon annulé."""
    bc = ajouter(
        s,
        Commande(
            numero="BC-2026-0001", fournisseur_id=w.ids["hasirci"], statut="envoyee",
            date_commande=date(2026, 9, 1), date_livraison_prevue=date(2026, 9, 20),
            eta=date(2026, 9, 25), devise="USD", cours=Decimal("9.8"),
            cours_fige_le=instant(2026, 9, 1), observations="Urgent",
        ),
    )  # fmt: skip
    l1 = ajouter(
        s,
        CommandeLigne(
            commande_id=bc.id, matiere_id=w.ids["pp"], quantite=1000, prix=Decimal("2.4"),
            prix_confirme=True, confirme_le=instant(2026, 9, 2), unite_achat="Palette",
            contenance=100,
        ),
    )  # fmt: skip
    l2 = ajouter(s, CommandeLigne(commande_id=bc.id, matiere_id=w.ids["jute"], quantite=500))
    brouillon = ajouter(
        s, Commande(fournisseur_id=w.ids["local"], date_commande=date(2026, 9, 3), devise="MAD")
    )
    ajouter(s, CommandeLigne(commande_id=brouillon.id, matiere_id=w.ids["cuir"], quantite=20))
    for numero, statut in (("BC-2026-0002", "soldee"), ("BC-2026-0003", "annulee")):
        c = ajouter(
            s,
            Commande(
                numero=numero, fournisseur_id=w.ids["local"], statut=statut,
                date_commande=date(2026, 8, 1), devise="MAD",
                solde_origine=OrigineSolde.manuel, solde_le=instant(2026, 9, 15),
            ),
        )  # fmt: skip
        ajouter(
            s,
            CommandeLigne(
                commande_id=c.id,
                matiere_id=w.ids["jute"],
                quantite=100,
                prix=11,
                prix_confirme=True,
                confirme_le=instant(2026, 8, 1),
            ),
        )
        w.ids[statut] = c.id
    w.ids |= {"bc": bc.id, "l1": l1.id, "l2": l2.id, "brouillon": brouillon.id}
