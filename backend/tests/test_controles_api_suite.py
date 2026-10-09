"""Les contrôles par l'API, un essai par contrôle : C20–C38 et les contrôles garantis (lot D8).

Même méthode que `test_controles_api.py` : une usine isolée, la donnée qui fait sonner, le
détail par `GET /api/controles/{code}` avec les ids des fiches. Les contrôles d'importation
(C28, C29, C34, C35, C36) lisent des dossiers posés en base (le lot D7 les ouvre par l'API) ;
C28 lit `delai_frais_import_jours`, C29 `toler_tva_import`.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from fabrique import *  # noqa: F403
from fabriques.pilotage import Usine, fixture_usine, jour, ok  # noqa: F401
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from test_controles_api import lignes, reglage, verdict

from gestion_mp_pro.modeles import Facture, Lot, Matiere


def sortie_sql(u: Usine, x: Lot, kg: float, le: date, type_: str = "SORTIE") -> None:
    """Une sortie écrite **hors du chemin** (SQL) : ce que la saisie refuse, une reprise ou un
    détour peuvent l'écrire ; les contrôles d'intégrité doivent le voir."""
    u.s.execute(
        text(
            "INSERT INTO mouvement (date_effet, type, matiere_id, lot_id, magasin_id, quantite,"
            " document, auteur_id) VALUES (:j, :t, :m, :l, :g, :q, 'reprise', :a)"
        ),
        {
            "t": type_,
            "j": le,
            "m": x.matiere_id,
            "l": x.id,
            "g": u.courant,
            "q": -kg,
            "a": u.auteur,
        },
    )


def test_c20_c27_stock_negatif_et_lot_vide_trop(usine: Usine) -> None:
    """C27 : un lot dont il est sorti plus qu'il n'est entré (un ajustement écrit hors du
    chemin) ; C20 : la matière, qui ne se consomme pas, est sous zéro (bloquants)."""
    u = usine
    m = u.matiere("C20-FIL")
    x = u.ouvrir(m, 100, 10)
    assert lignes(u, "C27") == [] and lignes(u, "C20") == []
    sortie_sql(u, x, 150, jour(), "AJUSTEMENT")
    c27 = lignes(u, "C27")
    assert [(y["lot"], y["lot_id"]) for y in c27] == [(x.numero, x.id)]
    assert [(y["reference"], y["stock_net"]) for y in lignes(u, "C20")] == [("C20-FIL", -50)]
    assert verdict(u, "C20")["gravite"] == verdict(u, "C27")["gravite"] == "bloquant"


def test_c37_lot_sous_zero_a_une_date_passee(usine: Usine) -> None:
    """Hérité : test_valeur_et_dates::test_c37_et_le_verificateur_voient_un_lot_sous_zero_dans_le_passe
    (partie C37) — une sortie datée avant l'entrée du lot : manque 50 le premier jour."""  # noqa: E501
    u = usine
    x = u.ouvrir(u.matiere("C37-FIL"), 100, 10)
    sortie_sql(u, x, 50, jour(-3))
    y = lignes(u, "C37")
    assert len(y) == 1 and y[0]["lot_id"] == x.id and y[0]["manque"] == 50
    assert lignes(u, "C27") == []


def test_c22_c23_c24_c25_fil_monte(usine: Usine) -> None:
    """C22 : 5 m montés sur une laize de 4 ; C23 : un fil sans poids de bobine ; C24 : un fil à
    l'étage 5 d'un métier de 3 étages ; C25 : un fil monté que rien n'a sorti."""
    u = usine
    sans_poids = u.matiere("C23-FIL")
    pese = u.matiere("C25-FIL", poids_bobine=Decimal(2))
    m = u.metier(laize=4, etages=3, fils=((1, sans_poids, 5), (5, pese, 1)))
    assert [(y["metier_id"], y["etage"]) for y in lignes(u, "C22")] == [(m.id, 1)]
    assert [y["reference"] for y in lignes(u, "C23")] == ["C23-FIL"]
    assert [(y["etage"], y["etages"]) for y in lignes(u, "C24")] == [(5, 3)]
    c25 = {y["reference"]: y for y in lignes(u, "C25")}
    assert c25["C25-FIL"]["poids"] == 20 and c25["C25-FIL"]["sorties"] == 0
    x = u.ouvrir(pese, 100, 10)
    u.sortir(x, 30)
    assert "C25-FIL" not in {y["reference"] for y in lignes(u, "C25")}


def _dossier_frais(u: Usine, **champs: Any) -> int:
    return u.dossier(**champs).id


def test_c28_dossier_sans_frais_lit_son_reglage(usine: Usine) -> None:
    """C28 : un dossier arrivé il y a 40 jours sans frais hors TVA sonne au délai de 30 jours ;
    réglé à 60 jours (`delai_frais_import_jours`), il se tait ; le libellé dit le délai."""
    u = usine
    m = u.matiere()
    d = _dossier_frais(u, arrivee=jour(-40), marchandises=((m, 100, 1000),), frais={"TVA": 200})
    assert [y["dossier_id"] for y in lignes(u, "C28")] == [d]
    assert "30 jours" in verdict(u, "C28")["libelle"]
    assert "sans frais hors TVA" in verdict(u, "C28")["libelle"]
    reglage(u, "delai_frais_import_jours", "60")
    assert lignes(u, "C28") == []
    assert "60 jours" in verdict(u, "C28")["libelle"]


def test_c29_tva_lit_sa_tolerance(usine: Usine) -> None:
    """C29 : 100 MAD de TVA pour 200 attendus (20 % de 1 000) sonnent à 5 % de tolérance ;
    à 60 % (`toler_tva_import`) non ; le libellé dit la tolérance (E-10)."""
    u = usine
    m = u.matiere()
    d = _dossier_frais(u, arrivee=jour(-5), marchandises=((m, 100, 1000),), frais={"TVA": 100})
    y = lignes(u, "C29")
    assert [(z["dossier_id"], z["tva_saisie"]) for z in y] == [(d, 100)]
    assert y[0]["tva_attendue"] == pytest.approx(200, abs=1)
    assert "5 %" in verdict(u, "C29")["libelle"]
    reglage(u, "toler_tva_import", "0.6")
    assert lignes(u, "C29") == []


def test_c34_frais_sans_marchandise(usine: Usine) -> None:
    """C34 : un dossier qui porte des frais sans marchandise ; la TVA dans sa colonne (E-10)."""
    u = usine
    d = _dossier_frais(u, frais={"TRANSIT": 300, "TVA": 50})
    y = lignes(u, "C34")
    assert [(z["dossier_id"], z["frais"], z["tva"]) for z in y] == [(d, 300, 50)]


def test_c35_frais_au_dela_de_la_marchandise_en_fraction(usine: Usine) -> None:
    """C35 : 500 MAD de droits sur 100 MAD de marchandise ; le rapport est une fraction (P8-3)."""
    u = usine
    m = u.matiere()
    d = _dossier_frais(u, marchandises=((m, 10, 100),), frais={"DD": 500})
    y = [z for z in lignes(u, "C35") if z["dossier_id"] == d]
    assert y and all(z["surcout"] is None or z["surcout"] < 100 for z in y)
    assert any(z["surcout"] == pytest.approx(5) for z in y if z["surcout"] is not None)


def test_c36_facture_sans_montant(usine: Usine) -> None:
    """Hérité : test_defauts_e::test_dossier_facture_sans_montant_signale (par l'API) — la
    facture du dossier n'a pas de montant : le dossier est signalé."""
    u = usine
    f = u.fournisseur("C36 FILATURE")
    facture = Facture(fournisseur_id=f, numero="FAC-C36", devise="MAD")
    u.s.add(facture)
    u.s.flush()
    m = u.matiere(fournisseur_id=f)
    d = _dossier_frais(u, marchandises=((m, 10, 100),), facture_id=facture.id)
    y = lignes(u, "C36")
    assert [z["dossier_id"] for z in y] == [d] and "non saisi" in y[0]["motif"]


def test_c30_poids_de_bobine_recu_eloigne(usine: Usine) -> None:
    """C30 : 100 kg pour 10 bobines (10 kg) face à 8 kg au catalogue : 25 %, en fraction."""
    u = usine
    f = u.fournisseur("C30 FILATURE")
    m = u.matiere("C30-FIL", fournisseur_id=f, poids_bobine=Decimal(8))
    r = ok(u.achats.post("/api/receptions", json={
        "date": jour().isoformat(), "fournisseur_id": f, "lignes": [
            {"matiere_id": m, "lot_numero": "C30-1", "quantite_pesee": 100, "bobines_en_plus": 10,
             "magasin_id": u.courant, "prix": 10}]}), 201)[0]  # fmt: skip
    ok(u.achats.post(f"/api/receptions/{r['id']}/valider", json={"version": r["version"]}))
    y = lignes(u, "C30")
    assert [(z["reference"], z["ecart"]) for z in y] == [("C30-FIL", 0.25)]


def test_c31_c32_ordres_servis_a_plusieurs_dates_et_dans_le_desordre(usine: Usine) -> None:
    """C31 : un ordre servi à deux dates ; C32 : OF-2026-0902 daté avant OF-2026-0901."""
    u = usine
    x = u.ouvrir(u.matiere(), 500, 10, le=jour(-10))
    un = u.ordre("OF-2026-0901", le=jour(-2))
    deux = u.ordre("OF-2026-0902", le=jour(-5))
    u.sortir(x, 10, le=jour(-2), ordre_id=un)
    u.sortir(x, 10, le=jour(-1), ordre_id=un)
    u.sortir(x, 10, le=jour(-5), ordre_id=deux)
    assert [(y["numero_of"], y["ordre_id"], y["nb_dates"]) for y in lignes(u, "C31")] == [
        ("OF-2026-0901", un, 2)
    ]
    assert [(y["numero_of"], y["apres"]) for y in lignes(u, "C32")] == [
        ("OF-2026-0902", "OF-2026-0901")
    ]


def test_c33_stock_minimum_plafonne(usine: Usine) -> None:
    """C33 : un stock minimum de 10 000 kg pour 1 000 kg consommés par mois : plafonné à 3 mois."""
    u = usine
    from test_controles_api import _consommee

    _consommee(u, "C33-FIL", stock_min=Decimal(10000))
    y = {z["reference"]: z for z in lignes(u, "C33")}
    assert y["C33-FIL"]["stock_min_catalogue"] == 10000 and y["C33-FIL"]["mois"] > 3


def test_c38_prix_du_catalogue_loin_du_paye(usine: Usine) -> None:
    """Hérité : test_audit2_achats::test_c38_signale_un_prix_du_catalogue_eloigne_du_dernier_prix_paye
    — payé 10 MAD, catalogue 100 : rapport 10 ; le catalogue n'est pas touché."""  # noqa: E501
    u = usine
    f = u.fournisseur("C38 FILATURE")
    m = u.matiere("C38-FIL", fournisseur_id=f, prix="100")
    r = ok(u.achats.post("/api/receptions", json={
        "date": jour().isoformat(), "fournisseur_id": f, "lignes": [
            {"matiere_id": m, "lot_numero": "C38-1", "quantite_pesee": 50,
             "magasin_id": u.courant, "prix": 10}]}), 201)[0]  # fmt: skip
    ok(u.achats.post(f"/api/receptions/{r['id']}/valider", json={"version": r["version"]}))
    y = lignes(u, "C38")
    assert [(z["reference"], z["rapport"]) for z in y] == [("C38-FIL", 10)]
    fiche = u.s.get(Matiere, m)
    assert fiche is not None and fiche.prix == 100


GARANTIS = {
    "C09": "UPDATE matiere SET prix = -1 WHERE id = :m",
    "C10": "UPDATE fournisseur SET delai_jours = -1"
    " WHERE id = (SELECT fournisseur_id FROM matiere WHERE id = :m)",
    "C11": "UPDATE devise SET cours = 0 WHERE code = 'USD' AND :m > 0",
    "C16": "UPDATE mouvement SET matiere_id = -1 WHERE matiere_id = :m",
    "C21": "UPDATE matiere SET devise = 'ZZZ' WHERE id = :m",
    "C26": "UPDATE mouvement SET lot_id = NULL WHERE matiere_id = :m",
}  # fmt: skip


@pytest.mark.parametrize("code", sorted(GARANTIS))
def test_les_controles_impossibles_se_disent_garantis_par_la_base(usine: Usine, code: str) -> None:
    """Hérité : test_audit2_pilotage::test_les_controles_impossibles_se_disent_garantis_par_la_base
    — conforme, garanti (hors du total), et la base refuse vraiment la faute (T11)."""
    u = usine
    m = u.matiere()
    u.ouvrir(m, 10, 10)
    c = verdict(u, code)
    assert c["conforme"] and c["garanti"], code
    point = u.s.begin_nested()
    with pytest.raises(IntegrityError):
        u.s.execute(text(GARANTIS[code]), {"m": m})
        u.s.flush()
    point.rollback()
    note = u.get(u.direction, "/api/controles")["synthese"]
    assert note["total"] == 38 - note["garantis"]
