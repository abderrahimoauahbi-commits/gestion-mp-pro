"""Les fabriques des référentiels (lot D1) bâtissent des fiches valides, dans les deux modes."""

from __future__ import annotations

from decimal import Decimal

from fabriques.referentiels import (
    code_douanier,
    devise,
    fournisseur,
    magasin,
    magasin_seme,
    matiere,
    poste_frais,
    poste_seme,
    qualite,
    valeur_classification,
)
from sqlalchemy.orm import Session

from gestion_mp_pro.db import fabrique, moteur
from gestion_mp_pro.modeles import Devise, Magasin, Matiere, PosteFrais, Qualite
from gestion_mp_pro.modeles.enums import TypeMagasin


def test_chaque_fabrique_ecrit_une_fiche_lue_par_l_api() -> None:
    code = devise(cours="11.5")
    f = fournisseur(devise=code, pays="turkey")
    m = matiere(fournisseur_id=f, devise=code, prix="2.5")
    cuir = matiere(role="Cuir", unite_prix="ml", prix="0.5")
    q = qualite(recette={m: 100}, poids={"Poil": "1.2"})
    with fabrique()() as s:
        assert s.get(Devise, code).cours == Decimal("11.5")  # type: ignore[union-attr]
        lue = s.get(Matiere, m)
        assert lue is not None and lue.fournisseur_id == f and lue.devise == code
        assert s.get(Matiere, cuir).densite == Decimal("0.014")  # type: ignore[union-attr]
        assert s.get(Qualite, q) is not None
        assert s.get(Magasin, magasin_seme(TypeMagasin.quarantaine)).type == "quarantaine"  # type: ignore[union-attr]
        assert s.get(PosteFrais, poste_seme("TVA")).recuperable  # type: ignore[union-attr]
    assert magasin() != magasin()
    assert poste_frais() != poste_frais()
    assert code_douanier() != code_douanier()
    assert valeur_classification("couleur") != valeur_classification("couleur")


def test_dans_la_transaction_d_un_essai_rien_ne_reste() -> None:
    with moteur().connect() as c:
        t = c.begin()
        with Session(bind=c, join_transaction_mode="create_savepoint") as s:
            m = matiere(s=s)
            assert s.get(Matiere, m) is not None
        t.rollback()
    with fabrique()() as s:
        assert s.get(Matiere, m) is None
