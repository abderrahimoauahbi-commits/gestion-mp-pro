"""Le modèle vu de l'ORM (lot S1) : verrou optimiste, `texte_recherche`, arrondi, défauts,
tables d'activité, relations chargées explicitement, semences vérifiées."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import InvalidRequestError, StatementError
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.orm.exc import StaleDataError

from gestion_mp_pro import modeles as m
from gestion_mp_pro.db import moteur
from gestion_mp_pro.modeles import recherche
from gestion_mp_pro.modeles.enums import StatutCommande
from gestion_mp_pro.modeles.types import MONTANT, PRIX, QUANTITE, arrondir
from gestion_mp_pro.services import horloge, installation


@pytest.fixture
def s() -> Iterator[Session]:
    """Une session ORM dans une transaction annulée à la fin de l'essai."""
    with moteur().connect() as c:
        transaction = c.begin()
        with Session(bind=c, join_transaction_mode="create_savepoint") as session:
            yield session
        transaction.rollback()


def _poil(s: Session) -> m.RoleNomenclature:
    return s.scalars(select(m.RoleNomenclature).where(m.RoleNomenclature.code == "Poil")).one()


def test_defauts_orm_et_horloge_figee(s: Session) -> None:
    f = m.Fournisseur(nom="Filature du Nord")
    s.add(f)
    s.flush()
    assert f.devise == "MAD"
    assert f.delai_jours == 60
    assert f.version == 1
    assert f.cree_le == horloge.maintenant()
    assert f.modifie_le is None
    f.pays = "TURQUIE"
    s.flush()
    assert f.version == 2
    assert f.modifie_le == horloge.maintenant()


def test_verrou_optimiste(s: Session) -> None:
    f = m.Fournisseur(nom="Fournisseur concurrent")
    s.add(f)
    s.flush()
    s.execute(text("UPDATE fournisseur SET version = version + 1 WHERE id = :i"), {"i": f.id})
    f.code = "FC"
    with pytest.raises(StaleDataError):
        s.flush()


def test_texte_recherche_tenu_et_suivi_des_renommages(s: Session) -> None:
    f = m.Fournisseur(nom="Société Écru", pays="MAROC")
    s.add(f)
    s.flush()
    matiere = m.Matiere(reference="Fil Rouge 2900", role_id=_poil(s).id, fournisseur_id=f.id)
    s.add(matiere)
    s.flush()
    lot = m.Lot(matiere_id=matiere.id, numero="LOT-A1", entre_le=date(2026, 10, 1))
    commande = m.Commande(fournisseur_id=f.id, date_commande=date(2026, 10, 1), devise="MAD")
    s.add_all([lot, commande])
    s.flush()
    assert f.texte_recherche == "societe ecru maroc"
    assert matiere.texte_recherche == "fil rouge 2900 societe ecru"
    assert lot.texte_recherche == "lot-a1 fil rouge 2900"
    assert commande.texte_recherche == "societe ecru"
    f.nom = "Filature Énergie"
    matiere.reference = "Fil Bleu"
    s.flush()
    assert matiere.texte_recherche == "fil bleu filature energie"
    assert lot.texte_recherche == "lot-a1 fil bleu"
    assert commande.texte_recherche == "filature energie"
    assert recherche.recalculer_table(s, m.Fournisseur) >= 1


def test_normaliser_comme_l_ecran() -> None:
    assert recherche.normaliser("  Écru\tPOLYESTER  ça ") == "ecru polyester ca"
    assert recherche.normaliser("") == ""


def test_arrondir_une_fois_demi_vers_le_haut() -> None:
    assert arrondir(Decimal("2.0005"), QUANTITE) == Decimal("2.001")
    assert arrondir(-2.0005, QUANTITE) == Decimal("-2.001")
    assert arrondir(0.1, PRIX) == Decimal("0.100000")
    assert arrondir("2.675", MONTANT) == Decimal("2.68")
    assert arrondir(12, MONTANT) == Decimal("12.00")
    for faux in (float("nan"), float("inf"), "abc", Decimal("NaN"), Decimal("1e20")):
        with pytest.raises(ValueError, match="quantité"):
            arrondir(faux, QUANTITE)


def test_enumeration_lue_et_refusee_par_l_orm(s: Session) -> None:
    c = m.Commande(fournisseur_id=None, date_commande=date(2026, 10, 1), devise="MAD")
    assert c.statut is None
    f = m.Fournisseur(nom="Pour un bon")
    s.add(f)
    s.flush()
    c.fournisseur_id = f.id
    s.add(c)
    s.flush()
    s.expire(c)
    assert c.statut is StatutCommande.brouillon
    c.statut = "inconnu"  # type: ignore[assignment]
    with pytest.raises(StatementError, match="inconnu"):
        s.flush()


def test_relations_chargees_explicitement(s: Session) -> None:
    f = m.Fournisseur(nom="Pour des lignes")
    s.add(f)
    s.flush()
    matiere = m.Matiere(reference="Fil lignes", role_id=_poil(s).id)
    s.add(matiere)
    s.flush()
    ligne = m.CommandeLigne(matiere_id=matiere.id, quantite=Decimal(10))
    c = m.Commande(
        fournisseur_id=f.id, date_commande=date(2026, 10, 1), devise="MAD", lignes=[ligne]
    )
    s.add(c)
    s.flush()
    s.expire_all()
    relue = s.get(m.Commande, c.id)
    assert relue is not None
    with pytest.raises(InvalidRequestError):
        _ = relue.lignes
    chargee = s.scalars(
        select(m.Commande).where(m.Commande.id == c.id).options(selectinload(m.Commande.lignes))
    ).one()
    assert [x.quantite for x in chargee.lignes] == [Decimal("10.000")]
    s.delete(chargee)
    s.flush()
    restantes = text("SELECT count(*) FROM commande_ligne WHERE commande_id = :c")
    assert s.scalar(restantes, {"c": c.id}) == 0


def test_tables_d_activite() -> None:
    activite = set(m.tables_d_activite())
    assert {"mouvement", "solde", "lot", "commande", "reception", "dossier", "compteur"} <= activite
    referentiels = {"matiere", "fournisseur", "qualite", "recette_version", "plan_version"}
    gardees = {"utilisateur", "journal", "parametre", "devise_cours", "metier", "montage"}
    assert not activite & (referentiels | gardees | {"piece_jointe"})
    assert len(activite) == 32


def test_semences_completes() -> None:
    with moteur().connect() as c:
        assert installation.semences_manquantes(c) == []
