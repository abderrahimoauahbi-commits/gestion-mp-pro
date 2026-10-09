"""Le bilan du mois par l'API (lot D8 ; routes 233, 234 ; défaut E-03 ; décision U8).

Usine isolée : le bilan s'équilibre en kilos **et** en dirhams (magasins et métiers), une
réception annulée dans le mois n'est nulle part, les bons annulés ne sont pas émis, un mois
invalide ou futur est refusé ; les écarts d'ordres sont ceux de l'écran Sorties.
"""

from __future__ import annotations

from datetime import datetime, time
from decimal import Decimal
from typing import Any

import pytest
from fabrique import *  # noqa: F403
from fabriques import referentiels as ref
from fabriques.ordres import acteur, atelier, saisie, valide
from fabriques.pilotage import Usine, fixture_usine, jour, ok  # noqa: F401

from gestion_mp_pro.modeles import (
    Commande,
    Dossier,
    DossierFrais,
    DossierLigne,
    MontageEvenement,
    PosteFrais,
    ReceptionLigne,
)
from gestion_mp_pro.modeles.enums import OrigineSolde, Role, StatutCommande, StatutDossier
from gestion_mp_pro.services import horloge, stock
from gestion_mp_pro.services.ordres.consommation import consommations

MOIS = "2026-10"


def bilan(u: Usine, mois: str = MOIS) -> dict[str, Any]:
    """Le bilan du mois lu par les achats."""
    return u.get(u.achats, "/api/bilan", mois=mois)  # type: ignore[no-any-return]


def reception(u: Usine, f: int, m: int, kg: float, prix: float, lot: str) -> dict[str, Any]:  # noqa: PLR0917
    """Une réception validée hors commande."""
    r = ok(u.achats.post("/api/receptions", json={
        "date": jour().isoformat(), "fournisseur_id": f, "lignes": [
            {"matiere_id": m, "lot_numero": lot, "quantite_pesee": kg, "magasin_id": u.courant,
             "prix": prix}]}), 201)[0]  # fmt: skip
    return ok(u.achats.post(f"/api/receptions/{r['id']}/valider", json={"version": r["version"]}))  # type: ignore[no-any-return]


def equilibre_kg(b: dict[str, Any]) -> float:
    """L'équation des kilos, montage compris : fin − (début + flux ± métiers)."""
    flux = (
        b["entrees_kg"] + b["ouvertures_kg"] - b["sorties_kg"] + b["retours_machine_kg"]
        - b["retours_fournisseur_kg"] + b["ajustements_kg"] + b["annulations_kg"]
    )  # fmt: skip
    return float(b["stock_fin_kg"] - (b["stock_debut_kg"] + flux + b["variation_metiers_kg"]))


def equilibre_mad(b: dict[str, Any]) -> float:
    """L'équation des dirhams : fin − (début + entrées − consommation + autres ± métiers)."""
    return float(
        b["valeur_fin_mad"]
        - (
            b["valeur_debut_mad"] + b["valeur_entrees_mad"] - b["consommation_mad"]
            + b["valeur_autres_mad"] + b["variation_metiers_mad"]
        )
    )  # fmt: skip


def test_bilan_mois_invalide_422(usine: Usine) -> None:
    """Hérité : test_defauts_e::test_bilan_mois_invalide_422 (E-03) — 13e mois, mois zéro, mois
    à venir, texte : 422 « Mois invalide », pour les données comme pour le document."""
    u = usine
    for mois in ("2026-13", "0000-00", "2026-11", "octobre", ""):
        for url in ("/api/bilan", "/api/documents/bilan"):
            r = u.achats.get(url, params={"mois": mois})
            assert r.status_code == 422, (url, mois)
            assert r.json()["detail"] == "Mois invalide : AAAA-MM, pas dans le futur."
    assert u.alimentation.get("/api/bilan", params={"mois": MOIS}).status_code == 403


def test_bilan_equilibre_en_valeur(usine: Usine) -> None:
    """Hérité : test_defauts_e::test_bilan_equilibre_en_valeur (E-03) — une entrée importée du
    mois, avec 300 MAD de droits : elle entre au coût de revient ; début + entrées − coût net
    des sorties + autres = fin, à 1 MAD près ; en kilos aussi, une ouverture, une sortie, un
    retour, un ajustement, une sortie annulée et du fil monté compris."""
    u = usine
    f = u.fournisseur("BILAN IMPORT")
    m = u.matiere("BILAN FIL", fournisseur_id=f, poids_bobine=Decimal(2))
    u.ouvrir(m, 200, 10, le=jour(-40))
    r = reception(u, f, m, 100, 20, "BIL-1")
    sans_frais = bilan(u)["valeur_entrees_mad"]
    rl = u.s.get(ReceptionLigne, r["lignes"][0]["id"])
    assert rl is not None
    d = Dossier(numero=ref.unique("ANC-BIL"), saisi_a_la_main=True, statut=StatutDossier.ouvert)
    u.s.add(d)
    u.s.flush()
    u.s.add(DossierLigne(dossier_id=d.id, reception_ligne_id=rl.id, matiere_id=m, lot_id=rl.lot_id,
                         quantite_kg=Decimal(100), valeur_devise=Decimal(2000)))  # fmt: skip
    dd = u.s.query(PosteFrais).filter_by(code="DD").one()
    u.s.add(DossierFrais(dossier_id=d.id, poste_id=dd.id, montant=Decimal(300)))
    u.s.flush()
    x = u.ouvrir(m, 50, 12)
    sortie = u.sortir(x, 30)
    u.sortir(x, 10)
    stock.contrepasser_mouvements(u.s, [sortie], u.auteur)
    u.ecrire(x, 2, type_=stock.TypeMouvement.RETOUR_MACHINE)
    u.ecrire(x, -1, type_=stock.TypeMouvement.AJUSTEMENT)
    u.metier(fils=((1, m, 0.25),))  # 0,25 m × 10 bobines × 2 kg = 5 kg sur les métiers
    b = bilan(u)
    assert b["valeur_entrees_mad"] - sans_frais == pytest.approx(300, abs=0.01)
    assert equilibre_mad(b) == pytest.approx(0, abs=1)
    assert b["ecart_valorisation_mad"] == pytest.approx(0, abs=1)
    assert equilibre_kg(b) == pytest.approx(0, abs=1e-6)
    assert (b["entrees_kg"], b["ouvertures_kg"], b["sorties_kg"]) == (100, 50, 40)
    assert b["annulations"] == {"SORTIE": 30} and b["retours_machine_kg"] == 2
    assert (b["metiers_debut_kg"], b["metiers_fin_kg"], b["variation_metiers_kg"]) == (5, 5, 0)
    assert b["stock_fin_kg"] == b["stock_fin_magasins_kg"] + 5
    assert b["valeur_fin_magasins_mad"] == pytest.approx(
        u.get(u.achats, "/api/valorisation")["total_magasin_mad"]
    )


def test_bilan_commandes_hors_annulees(usine: Usine) -> None:
    """Hérité : test_defauts_e::test_bilan_commandes_hors_annulees — un bon parti dans le mois
    compte ; annulé, il ne compte plus."""
    u = usine
    f = u.fournisseur()
    cid = u.commande(f, u.matiere(fournisseur_id=f), 10, le=jour(-1))
    assert bilan(u)["commandes"] == 1
    c = u.s.get(Commande, cid)
    assert c is not None
    c.statut, c.solde_origine = StatutCommande.annulee, OrigineSolde.manuel
    c.solde_le = horloge.maintenant()
    assert bilan(u)["commandes"] == 0


def test_le_bilan_compte_les_dirhams_sans_les_receptions_annulees(usine: Usine) -> None:
    """Hérité : test_valeur_et_dates::test_le_bilan_compte_les_dirhams_sans_les_receptions_annulees ;
    test_defauts_e::test_bilan_reception_annulee_hors_kilos — 100 kg à 25 : +2 500 MAD ; annulée,
    ni kilos, ni dirhams, ni annulation ; la fin vaut la Valorisation ; le document le dit."""  # noqa: E501
    u = usine
    f = u.fournisseur()
    m = u.matiere(fournisseur_id=f)
    u.ouvrir(m, 10, 10)
    avant = bilan(u)
    r = reception(u, f, m, 100, 25, "V2B-1")
    assert bilan(u)["valeur_entrees_mad"] - avant["valeur_entrees_mad"] == pytest.approx(2500)
    ok(u.achats.post(f"/api/receptions/{r['id']}/annuler",
                     json={"version": r["version"], "motif": "erreur de saisie"}))  # fmt: skip
    apres = bilan(u)
    for cle in ("valeur_entrees_mad", "entrees_kg", "annulations_kg", "stock_fin_kg"):
        assert apres[cle] == pytest.approx(avant[cle]), cle
    assert apres["valeur_fin_mad"] == pytest.approx(
        u.get(u.achats, "/api/valorisation")["total_mad"]
    )
    page = u.achats.get("/api/documents/bilan", params={"mois": MOIS})
    assert page.headers["content-disposition"] == "inline"
    assert "Stock d'ouverture saisi" in page.text and "hors réceptions annulées" in page.text
    assert "parfois d'un mois précédent" not in page.text


def test_le_bilan_detaille_les_annulations_en_kilos(usine: Usine) -> None:
    """Hérité : test_direction::test_recette_le_bilan_compte_les_annulations_a_part ;
    test_audit2_pilotage::test_le_bilan_detaille_les_annulations_en_kilos — une sortie annulée
    a sa ligne à part (+30 : les sorties restent 30, pas des sorties négatives), dite par type
    dans le document."""
    u = usine
    x = u.ouvrir(u.matiere(), 100, 10)
    stock.contrepasser_mouvements(u.s, [u.sortir(x, 30)], u.auteur)
    b = bilan(u)
    assert (b["sorties_kg"], b["annulations_kg"], b["annulations"]) == (30, 30, {"SORTIE": 30})
    page = u.achats.get("/api/documents/bilan", params={"mois": MOIS}).text
    assert "Annulations (contre-passations) datées du mois" in page
    assert "sorties vers les machines 30,0 kg" in page


def test_api_le_bilan_d_un_mois_passe_compte_ses_ruptures_a_la_fin_du_mois(usine: Usine) -> None:
    """Hérité : test_valorisation::test_api_le_bilan_d_un_mois_passe_compte_ses_ruptures_a_la_fin_du_mois
    — une rupture de septembre reste au bilan de septembre après 1 000 000 kg entrés en octobre."""  # noqa: E501
    u = usine
    m = u.matiere("RUPTURE SEPT")
    ref.qualite(recette={m: 100}, poids={"Poil": "1"}, base_mensuelle="1000", s=u.s)
    u.ouvrir(u.matiere(), 1, 1, le=jour(-60))
    avant = bilan(u, "2026-09")
    assert avant["ruptures"] >= 1 and avant["au"] == "2026-09-30"
    u.ouvrir(m, 1_000_000, 1)
    assert bilan(u, "2026-09")["ruptures"] == avant["ruptures"]
    assert bilan(u)["ruptures"] < avant["ruptures"]


def test_le_montage_d_avant_le_mois_entre_au_debut(usine: Usine) -> None:
    """Décision U8 : le fil monté est du stock à toute date — un montage fait aujourd'hui
    (historique) n'était pas au début du mois : la variation sur les métiers ferme l'équation."""
    u = usine
    m = u.matiere("BILAN MONTE", poids_bobine=Decimal(2))
    x = u.ouvrir(m, 100, 10, le=jour(-20))
    u.sortir(x, 20, le=jour(-20))
    metier = u.metier(fils=((1, m, 1),))
    ligne = {"etage": 1, "reference": "BILAN MONTE", "metres": 1.0, "pourcentage": 100.0}
    quand = datetime.combine(jour(), time(9), tzinfo=horloge.FUSEAU)
    u.s.add(MontageEvenement(metier_id=metier.id, etage=1, avant=[], apres=[ligne], quand=quand))
    u.s.flush()
    b = bilan(u)
    assert (b["metiers_debut_kg"], b["metiers_fin_kg"], b["variation_metiers_kg"]) == (0, 20, 20)
    assert b["variation_metiers_mad"] == pytest.approx(200)
    assert equilibre_kg(b) == pytest.approx(0, abs=1e-6)
    assert equilibre_mad(b) == pytest.approx(0, abs=1)


def test_le_prevu_d_un_ordre_est_fige_et_le_bilan_le_lit_comme_les_sorties(usine: Usine) -> None:
    """Hérité : test_plan_besoins::test_le_prevu_d_un_ordre_est_fige_et_le_bilan_le_lit_comme_les_sorties
    (moitié bilan, laissée par D6) — l'écart d'un ordre au bilan est celui de l'écran Sorties
    (`consommations` : prévu figé, perte de l'époque, retours déduits)."""  # noqa: E501
    u = usine
    a = atelier(u.s)
    qui = acteur(u.s, Role.alimentation)
    o = valide(u.s, qui, saisie(a.m.courant.id, [(a.lot("E-L1"), 12), (a.lot("E-T1"), 5)],
                                [(a.e1, 10)]))  # fmt: skip
    attendu = consommations(u.s)[o.numero]
    ecarts = {x["numero_of"]: x for x in bilan(u)["ecarts_ordres"]}
    lu = ecarts[o.numero]
    assert (lu["theorique"], lu["net"]) == pytest.approx((attendu.theorique, attendu.net))
    assert lu["ecart_relatif"] == pytest.approx(attendu.ecart_relatif)
    assert bilan(u)["ordres"] == 1 and bilan(u)["m2_total"] == 10
