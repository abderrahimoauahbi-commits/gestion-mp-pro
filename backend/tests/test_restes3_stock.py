"""Restes du stock (RESTES3 : lignes S3, S4 de RESTES.md), sur une usine isolée (`usine`).

- S3 : `statut`, `statut_couverture`, `action` du moteur en codes, sans émoji ;
- S4 : `/stock?date=` compte le fil monté de ce soir-là (le chiffre de la Valorisation) ;
  `LigneStock` porte les ids du rôle et du fournisseur, `EtatStock` ceux des magasins ;
  `Tracabilite` et `EtapeTracee` portent leurs ids (liens de l'écran) ; le journal d'un lot
  n'a pas de devise pour l'alimentation (an. 27) ;
- preuve héritée `test_valorisation::test_api_les_lots_comptent_comme_les_soldes`.
"""

from __future__ import annotations

from datetime import datetime, time
from decimal import Decimal
from typing import Any

from fabriques.pilotage import Usine, fixture_usine, jour  # noqa: F401
from fabriques.referentiels import qualite

from gestion_mp_pro.modeles import MontageEvenement
from gestion_mp_pro.modeles.enums import TypeMagasin, TypeMouvement
from gestion_mp_pro.services import horloge, stock

CODES = {"RUPTURE", "CRITIQUE", "URGENT", "ATTENTION", "OK", "NON_CONSOMMEE"}


def _ligne(u: Usine, reference: str, **params: Any) -> dict[str, Any]:
    lignes = u.get(u.achats, "/api/stock", **params)["lignes"]
    return next(x for x in lignes if x["reference"] == reference)  # type: ignore[no-any-return]


def test_les_statuts_du_moteur_sont_des_codes(usine: Usine) -> None:
    """S3 : codes sans émoji ; l'action d'achat aussi ; l'alimentation n'a pas l'action."""
    u = usine
    rouge, bleu = u.matiere("ROUGE CODE"), u.matiere("BLEU CODE")
    qualite(recette={rouge: 100}, poids={"Poil": "1"}, base_mensuelle="1000", s=u.s)
    u.ouvrir(bleu, 10, 10)
    r, b = _ligne(u, "ROUGE CODE"), _ligne(u, "BLEU CODE")
    assert (r["statut"], b["statut"]) == ("RUPTURE", "NON_CONSOMMEE")
    assert {r["statut_couverture"], b["statut_couverture"]} <= CODES
    assert (r["action"], b["action"]) == ("CREER_BC", "AUCUNE")
    plan = u.get(u.achats, "/api/plan-achat")
    (p,) = [x for x in plan["lignes"] if x["reference"] == "ROUGE CODE"]
    assert p["statut"] == "RUPTURE" and p["relance"].startswith("RUPTURE — ROUGE CODE (")
    alertes = u.get(u.direction, "/api/cockpit")["alertes"]
    assert {x["statut_couverture"] for x in alertes} <= CODES
    lue = u.get(u.alimentation, "/api/stock")["lignes"]
    assert next(x for x in lue if x["reference"] == "ROUGE CODE")["action"] is None


def test_le_stock_d_un_soir_passe_compte_le_fil_monte_de_ce_soir_la(usine: Usine) -> None:
    """S4 (reste de D8) : `/stock?date=` dit le même fil monté que la Valorisation ; un montage
    fait aujourd'hui ne compte pas hier, l'étage d'hier revient."""
    u = usine
    m = u.matiere("FIL DU SOIR", poids_bobine=Decimal(2))
    x = u.ouvrir(m, 100, 10, le=jour(-3))
    u.sortir(x, 40, le=jour(-3))
    metier = u.metier(fils=((1, m, 2),))
    ligne = {"etage": 1, "matiere_id": m, "reference": "FIL DU SOIR", "metres": 1.0,
             "pourcentage": 100.0, "commentaire": "", "kg": 20.0}  # fmt: skip
    u.s.add(MontageEvenement(
        metier_id=metier.id, etage=1, avant=[ligne], apres=[{**ligne, "metres": 2.0, "kg": 40.0}],
        quand=datetime.combine(jour(), time(9), tzinfo=horloge.FUSEAU),
    ))  # fmt: skip
    u.s.flush()
    hier = jour(-1).isoformat()
    assert _ligne(u, "FIL DU SOIR")["stock_machine"] == 40
    passe = _ligne(u, "FIL DU SOIR", date=hier)
    valorise = next(
        v for v in u.get(u.achats, "/api/valorisation", date=hier)["lignes"]
        if v["reference"] == "FIL DU SOIR"
    )  # fmt: skip
    assert passe["stock_machine"] == valorise["stock_machine"] == 20
    fiche = u.get(u.achats, f"/api/stock/{m}", date=hier)
    assert fiche["ligne"]["stock_machine"] == 20
    assert [f["poids"] for f in fiche["sur_les_metiers"]] == [20]


def test_une_ligne_de_stock_porte_les_ids_de_ses_liens(usine: Usine) -> None:
    """S4 (F2) : rôle et fournisseur par id ; les magasins de `par_magasin` (par code) aussi."""
    u = usine
    f = u.fournisseur("Filature des liens")
    m = u.matiere("FIL LIENS", fournisseur_id=f)
    u.ouvrir(m, 5, 10)
    e = u.get(u.achats, "/api/stock")
    ligne = next(x for x in e["lignes"] if x["reference"] == "FIL LIENS")
    poil = u.s.execute(stock_role("Poil")).scalar_one()
    assert (ligne["matiere_id"], ligne["fournisseur_id"], ligne["role_id"]) == (m, f, poil)
    assert set(e["magasin_ids"]) == set(e["magasins"]) and u.courant in e["magasin_ids"].values()


def stock_role(code: str) -> Any:
    """La requête de l'id d'un rôle semé."""
    from sqlalchemy import select

    from gestion_mp_pro.modeles import RoleNomenclature

    return select(RoleNomenclature.id).where(RoleNomenclature.code == code)


def test_la_tracabilite_porte_ses_ids(usine: Usine) -> None:
    """S4 (F2) : lot, matière, ordre et document de chaque étape par id (liens de l'écran)."""
    u = usine
    m = u.matiere("FIL TRACE")
    x = u.ouvrir(m, 50, 10, le=jour(-2))
    o = u.ordre("OF-TRACE", le=jour(-1))
    piece = stock.Piece(stock.DocumentMouvement.ordre, o, "OF-TRACE")
    stock.ecrire(
        u.s, type=TypeMouvement.SORTIE, lot=x, magasin_id=u.courant, quantite=Decimal(-20),
        jour=jour(-1), piece=piece, auteur_id=u.auteur, liens=stock.Liens(ordre_id=o),
    )  # fmt: skip
    t = u.get(u.achats, "/api/tracabilite", lot=x.id)
    assert (t["lot_id"], t["matiere_id"], t["ordre_id"]) == (x.id, m, None)
    sortie = next(e for e in t["mouvements"] if e["type"] == "SORTIE")
    assert (sortie["matiere_id"], sortie["ordre_id"], sortie["lot_id"]) == (m, o, x.id)
    assert (sortie["document_type"], sortie["document_id"]) == ("ordre", o)
    entree = next(e for e in t["mouvements"] if e["type"] == "OUVERTURE")
    assert (entree["document_type"], entree["document_id"]) == ("reprise", None)
    par_ordre = u.get(u.achats, "/api/tracabilite", ordre=o)
    assert (par_ordre["ordre_id"], par_ordre["ordre"]) == (o, "OF-TRACE")


def test_le_journal_d_un_lot_n_a_pas_de_devise_pour_l_alimentation(usine: Usine) -> None:
    """S4 (F3, an. 27) : `GET /lots/{id}` et `/mouvements` sans devise pour l'alimentation."""
    u = usine
    m = u.matiere("FIL SANS DEVISE")
    x = u.ouvrir(m, 30, 12)
    lu = u.get(u.alimentation, f"/api/lots/{x.id}")
    assert lu["mouvements"] and {e["devise"] for e in lu["mouvements"]} == {None}
    assert {e["prix"] for e in lu["mouvements"]} == {None}
    assert {e["devise"] for e in u.get(u.achats, f"/api/lots/{x.id}")["mouvements"]} == {"MAD"}
    page = u.get(u.alimentation, "/api/mouvements", lot=x.id)
    assert {e["devise"] for e in page["elements"]} == {None}


def test_api_les_lots_comptent_comme_les_soldes(usine: Usine) -> None:
    """Hérité : test_valorisation::test_api_les_lots_comptent_comme_les_soldes — 100 entrés
    hier, 50 aujourd'hui annulés, 30 mis en quarantaine : la liste des lots dit entré 100,
    sorti 0, stock 100 comme les soldes ; proposés à la sortie : 70 (quarantaine exclue)."""
    u = usine
    m = u.matiere("VALO LOTS")
    x = u.ouvrir(m, 100, 10, le=jour(-1))
    entree = u.ecrire(x, 50, prix=10)
    stock.contrepasser_mouvements(u.s, [entree], u.auteur)
    quarantaine = u.quarantaine
    u.ecrire(x, -30, type_=TypeMouvement.TRANSFERT)
    u.ecrire(x, 30, type_=TypeMouvement.TRANSFERT, magasin_id=quarantaine)
    (lot,) = u.get(u.achats, "/api/lots", matiere=m)
    assert (lot["historique"]["entre"], lot["historique"]["sorti"]) == (100, 0)
    assert lot["quantite"] == 100 and lot["quarantaine"] == 30
    soldes = {g["type"]: g["quantite"] for g in lot["magasins"]}
    assert soldes == {TypeMagasin.stock_courant: 70, TypeMagasin.quarantaine: 30}
    proposes = u.get(u.achats, "/api/lots/disponibles", matiere=m)
    assert [(p["lot"], p["quantite"]) for p in proposes] == [(x.numero, 70)]
