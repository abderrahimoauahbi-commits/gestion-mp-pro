"""Ce que Gestion MP a changé dans son moteur pendant le portage (commit 26459d4, après le
commit f18b445 des jeux de parité) : la tolérance de C29 devient un réglage (E-10), un retour
au fournisseur d'un lot d'ouverture compte pour le fournisseur de l'opération (A-30)."""

from __future__ import annotations

from datetime import date

from gestion_mp_pro.calcul.chargement import EcritureLue, journal_du_moteur
from gestion_mp_pro.calcul.controles import controler
from gestion_mp_pro.calcul.modele import (
    Article,
    ChargeImport,
    Donnees,
    DossierImport,
    LigneImport,
    Parametres,
)

JOUR = date(2026, 10, 8)


def _c29(tolerance: float) -> tuple[str, int]:
    dossier = DossierImport(
        numero="12/26",
        lignes=[LigneImport(id=1, reference="FIL", quantite=100, valeur_devise=10_000)],
        # TVA attendue : (10 000 + 25 de TPI) × 20 % = 2 005 ; saisie 1 850, à 7,7 %.
        charges=[ChargeImport(poste="TVA", montant=1_850.0)],
    )
    donnees = Donnees(
        parametres=Parametres(toler_tva_import=tolerance, cours={"MAD": 1.0}),
        articles=[Article(reference="FIL", fournisseur="F")],
        dossiers_import=[dossier],
    )
    c29 = next(c for c in controler(donnees, [], JOUR) if c.code == "C29")
    return c29.libelle, c29.anomalies


def test_la_tolerance_de_c29_est_un_reglage() -> None:
    """Hérité : test_defauts_i::test_c29_tolerance_reglable (partie moteur)."""
    libelle, anomalies = _c29(0.1)
    assert "10 % de la TVA attendue" in libelle
    assert anomalies == 0
    libelle, anomalies = _c29(0.05)
    assert libelle.startswith("TVA d'importation à plus de 5 % de la TVA attendue")
    assert anomalies == 1


def test_un_retour_d_un_lot_d_ouverture_compte_pour_le_fournisseur_de_l_operation() -> None:
    """Hérité : test_defauts_i::test_retour_lot_d_ouverture_compte_pour_le_fournisseur_de_l_
    operation (partie chargeur : le lot n'a pas de fournisseur, l'opération en a un)."""
    commun = {"date": JOUR, "reference": "FIL", "magasin": "A", "lot": "ZI-RET"}
    mouvements = journal_du_moteur(
        [
            EcritureLue(id=1, type="OUVERTURE", quantite=30, **commun),  # type: ignore[arg-type]
            EcritureLue(
                id=2,
                type="RETOUR_FOURNISSEUR",
                quantite=-4,
                document="operation",
                fournisseur_operation="ZI FILATURE",
                **commun,  # type: ignore[arg-type]
            ),
            EcritureLue(
                id=3,
                type="RETOUR_FOURNISSEUR",
                quantite=-1,
                fournisseur="LOT FOURNI",
                document="operation",
                fournisseur_operation="ZI FILATURE",
                **commun,  # type: ignore[arg-type]
            ),
        ]
    )
    assert [m.fournisseur for m in mouvements] == ["", "ZI FILATURE", "LOT FOURNI"]
    assert [(m.type, m.quantite, m.magasin_source) for m in mouvements[1:]] == [
        ("RETOUR_FOURNISSEUR", 4, "A"),
        ("RETOUR_FOURNISSEUR", 1, "A"),
    ]
