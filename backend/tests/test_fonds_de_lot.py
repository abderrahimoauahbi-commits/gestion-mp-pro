"""Fonds de lot et rebut (lot FOND-DE-LOT ; décision de Mohamed du 15/10/2026, DECISIONS U22).

Service : le seuil (réglage `seuil_rebut`, 100 g par défaut, 0 = désactivé) ; la liste des lots
marque les fonds ; la proposition FIFO saute un fond de lot et le nomme ; « Mettre au rebut »
écrit un ajustement « Rebut » validé qui vide le lot dans son magasin ; refus au-dessus du seuil
hors direction (motif exigé de la direction) ; période close ; inventaire en cours ; quarantaine
hors de portée de l'atelier ; version périmée. API : l'alimentation met un fond de lot au rebut
au téléphone sans voir un prix ; le bilan compte le rebut dans ses ajustements ; la traçabilité
le montre. Chaque essai de service travaille dans une transaction annulée (`fabriques.stock.s`).
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import timedelta
from decimal import Decimal
from typing import Any

import pytest
from fabrique import *  # noqa: F403
from fabriques import referentiels as ref
from fabriques import stock as fabriques_stock
from fabriques.operations import acteur
from fabriques.ordres import Atelier, atelier, saisie, valide
from fabriques.stock import JOUR, entree, inventaire_ouvert, lot, magasin, matiere
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_prix_masques import fuites

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.db import fabrique
from gestion_mp_pro.modeles import Journal, Lot, Matiere, Mouvement, Parametre, Solde
from gestion_mp_pro.modeles.enums import ObjetJournal, Role, StatutDocument, TypeMagasin
from gestion_mp_pro.services import fonds_de_lot, lots, ordres, tracabilite
from gestion_mp_pro.services.operations import lecture, rebut

s = fabriques_stock.s
"""La session de l'essai, annulée à la fin (fixture du lot S4)."""
FOND = Decimal("0.056")
"""56 g : un fond de lot au seuil par défaut (100 g)."""


def _seuil(s: Session, valeur: str) -> None:
    """Pose le réglage dans la transaction de l'essai (le défaut semé est 0.1)."""
    p = s.get(Parametre, fonds_de_lot.CLE)
    assert p is not None
    p.valeur = valeur
    s.flush()


def _solde(s: Session, x: Lot, magasin_id: int) -> Decimal:
    return s.scalar(
        select(Solde.quantite).where(Solde.lot_id == x.id, Solde.magasin_id == magasin_id)
    ) or Decimal(0)


def _refus(fonction: Any, *args: Any, **kw: Any) -> Refus:
    """Le refus d'un geste ; ce qu'il avait commencé est défait (comme la route le ferait)."""
    session = next(x for x in args if isinstance(x, Session))
    point = session.begin_nested()
    with pytest.raises(Refus) as e:
        fonction(*args, **kw)
    point.rollback()
    return e.value


def _demande(s: Session, x: Lot, magasin_id: int, motif: str = "") -> rebut.DemandeRebut:
    return rebut.DemandeRebut(x.id, magasin_id, lots.versions(s, {x.id})[x.id], motif)


def _lot(s: Session, q: Decimal | float, *, g: Any = None, m: Matiere | None = None) -> Lot:
    """Un lot entré aujourd'hui avec `q` kg à 20 MAD/kg dans `g` (le magasin semé sinon)."""
    x = lot(s, m or matiere(s), entre_le=JOUR - timedelta(days=3))
    entree(s, x, q, JOUR - timedelta(days=3), g, prix=20)
    return x


def test_seuil_marque_et_regle(s: Session) -> None:
    """Défaut 100 g ; un reste > 0 et < seuil est un fond ; le seuil même n'en est pas un ; à 0,
    rien n'est un fond de lot ; la marque et le poids se lisent en grammes sous le kilo."""
    seuil = fonds_de_lot.seuil(s)
    assert seuil == Decimal("0.100")
    assert fonds_de_lot.est_fond(FOND, seuil) and fonds_de_lot.est_fond(Decimal("0.001"), seuil)
    assert not fonds_de_lot.est_fond(Decimal("0.100"), seuil)
    assert not fonds_de_lot.est_fond(Decimal(0), seuil)
    assert fonds_de_lot.marque(seuil) == "fond de lot (< 100 g)"
    assert fonds_de_lot.poids_lisible(FOND) == "56 g"
    assert fonds_de_lot.marque(Decimal(2)) == "fond de lot (< 2\u00a0kg)"
    _seuil(s, "0")
    assert fonds_de_lot.seuil(s) == 0 and not fonds_de_lot.est_fond(FOND, fonds_de_lot.seuil(s))


def test_la_liste_des_lots_marque_les_fonds_et_dit_la_version(s: Session) -> None:
    """Route 107 : un solde de 56 g est marqué (par magasin et sur le lot, avec son poids), un
    solde de 5 kg non ; un fond en quarantaine est marqué aussi ; la version est celle de la
    fiche (1 sans journal)."""
    m = matiere(s)
    fond, plein = _lot(s, FOND, m=m), _lot(s, 5, m=m)
    q = magasin(s, TypeMagasin.quarantaine)
    entree(s, plein, FOND, JOUR, q, prix=20)
    par_lot = {x.lot_id: x for x in lots.lister(s, lots.FiltresLots(matiere_id=m.id))}
    assert par_lot[fond.id].fond_de_lot and par_lot[fond.id].fond_de_lot_kg == FOND
    assert par_lot[fond.id].magasins[0].fond_de_lot and par_lot[fond.id].version == 1
    x = par_lot[plein.id]
    assert x.fond_de_lot and x.fond_de_lot_kg == FOND  # le solde en quarantaine seulement
    assert {g.fond_de_lot for g in x.magasins if g.type == "quarantaine"} == {True}
    assert {g.fond_de_lot for g in x.magasins if g.type != "quarantaine"} == {False}
    _seuil(s, "0")
    assert not any(x.fond_de_lot for x in lots.lister(s, lots.FiltresLots(matiere_id=m.id)))


def _poil_seul(s: Session, a: Atelier, q_vieux: Decimal | float) -> tuple[int, Lot, Lot]:
    """Une qualité de poil seul (1 kg/m²) : un vieux lot (`q_vieux`, avant-hier) et un neuf
    (400 kg, aujourd'hui), dans le magasin du décor."""
    poil = ref.matiere(s=s)
    q = ref.qualite(recette={poil: 100}, poids={"Poil": 1}, s=s)
    fiche = s.get_one(Matiere, poil)
    vieux = lot(s, fiche, "VIEUX", entre_le=JOUR - timedelta(days=2))
    entree(s, vieux, q_vieux, JOUR - timedelta(days=2), a.m.courant)
    neuf = lot(s, fiche, "NEUF", entre_le=JOUR)
    entree(s, neuf, 400, JOUR, a.m.courant)
    return q, vieux, neuf


def test_la_proposition_fifo_saute_un_fond_de_lot_et_le_nomme(s: Session) -> None:
    """STRESS-3-ANS A8 : le FIFO proposait d'abord un lot presque vide. Un fond de lot n'est plus
    dans `lots`, reste dans `disponibles` marqué, et la proposition le nomme ; à seuil 0, il est
    proposé comme avant ; un vrai reliquat (3,151 kg, au-dessus de 100 g) est proposé."""
    a = atelier(s)
    q, vieux, neuf = _poil_seul(s, a, FOND)
    demande = ordres.Demande(a.m.courant.id, (ordres.SaisieQualite(q, Decimal(100)),))
    p = ordres.proposer(s, demande)
    ligne = p.lignes[0]
    assert [x.lot for x in ligne.lots] == ["NEUF"] and ligne.manque == 0
    assert [(x.lot, x.fond_de_lot) for x in ligne.disponibles] == [("VIEUX", True), ("NEUF", False)]
    assert len(p.fonds_de_lot) == 1 and "VIEUX" in p.fonds_de_lot[0]
    assert "56 g" in p.fonds_de_lot[0] and "fond de lot (< 100 g)" in p.fonds_de_lot[0]
    _seuil(s, "0")
    p = ordres.proposer(s, demande)
    assert [x.lot for x in p.lignes[0].lots] == ["VIEUX", "NEUF"] and p.fonds_de_lot == []
    _seuil(s, "0.1")
    entree(s, vieux, Decimal("3.095"), JOUR - timedelta(days=2), a.m.courant)  # 3,151 kg
    p = ordres.proposer(s, demande)
    assert [x.lot for x in p.lignes[0].lots] == ["VIEUX", "NEUF"]
    assert p.lignes[0].lots[0].propose == Decimal("3.151")


def test_le_rebut_ecrit_un_ajustement_rebut_valide_et_vide_le_lot(s: Session) -> None:
    """Route 258 (achats) : un ajustement AJU-… validé, motif « Rebut », −56 g sur le lot dans
    son magasin, solde à 0, journal du lot « rebut fond de lot », version avancée ; la
    traçabilité du lot montre l'écriture ; un second rebut n'a plus rien à sortir."""
    x, g = _lot(s, FOND), magasin(s)
    qui = acteur(s, Role.achats)
    o = rebut.mettre_au_rebut(s, qui, _demande(s, x, g.id))
    assert o.statut == StatutDocument.validee and (o.numero or "").startswith("AJU-")
    assert o.motif_texte == "Rebut" and "56 g" in o.commentaire and "100 g" in o.commentaire
    assert _solde(s, x, g.id) == 0
    ecrit = s.scalars(select(Mouvement).where(Mouvement.operation_id == o.id)).one()
    assert ecrit.quantite == -FOND and ecrit.motif_texte == "Rebut" and ecrit.lot_id == x.id
    journal = s.scalars(
        select(Journal.action).where(Journal.objet == ObjetJournal.lot, Journal.objet_id == x.id)
    ).all()
    assert "rebut fond de lot" in journal and lots.versions(s, {x.id})[x.id] == 2
    lue = lecture.fiche(s, o.id, Role.achats)
    assert lue.motif == "Rebut" and lue.lignes[0].quantite == -FOND
    etapes = tracabilite.tracabilite(s, lot_id=x.id).mouvements
    assert any(e.type == "AJUSTEMENT" and Decimal(str(e.quantite)) == -FOND for e in etapes)
    refus = _refus(rebut.mettre_au_rebut, s, qui, _demande(s, x, g.id))
    assert refus.code == "stock_insuffisant" and "rien à mettre au rebut" in refus.detail
    assert not any(x.fond_de_lot for x in lots.lister(s, lots.FiltresLots(lot_id=x.id)))


def test_au_dessus_du_seuil_la_direction_seule_avec_un_motif(s: Session) -> None:
    """3,151 kg : « ce n'est pas un fond de lot » (409 `pas_un_fond_de_lot`) pour les achats et
    l'alimentation ; la direction sans motif → 422 ; avec un motif, l'ajustement est écrit et le
    commentaire garde le motif."""
    x, g = _lot(s, Decimal("3.151")), magasin(s)
    for role in (Role.achats, Role.alimentation):
        refus = _refus(rebut.mettre_au_rebut, s, acteur(s, role), _demande(s, x, g.id))
        assert refus.code == "pas_un_fond_de_lot" and refus.http == 409
        assert "Ce n'est pas un fond de lot" in refus.detail and "100 g" in refus.detail
    direction = acteur(s, Role.direction)
    refus = _refus(rebut.mettre_au_rebut, s, direction, _demande(s, x, g.id, "nul"))
    assert refus.code == "motif_requis" and refus.http == 422
    o = rebut.mettre_au_rebut(s, direction, _demande(s, x, g.id, "Fil moisi, inutilisable"))
    assert o.statut == StatutDocument.validee and "Fil moisi" in o.commentaire
    assert o.commentaire.startswith("Mis au rebut : 3,15\u00a0kg") and _solde(s, x, g.id) == 0


def test_seuil_desactive_direction_seule(s: Session) -> None:
    """Seuil 0 : plus aucun fond de lot ; 56 g ne se mettent au rebut que par la direction, avec
    un motif, et le refus dit que le seuil est désactivé."""
    _seuil(s, "0")
    x, g = _lot(s, FOND), magasin(s)
    refus = _refus(rebut.mettre_au_rebut, s, acteur(s, Role.achats), _demande(s, x, g.id))
    assert refus.code == "pas_un_fond_de_lot" and "désactivé" in refus.detail
    o = rebut.mettre_au_rebut(s, acteur(s, Role.direction), _demande(s, x, g.id, "Poussière"))
    assert o.statut == StatutDocument.validee


def test_quarantaine_pas_depuis_l_atelier(s: Session) -> None:
    """Un fond de lot en quarantaine : 403 pour l'alimentation (message de la décision), permis
    aux achats."""
    q = magasin(s, TypeMagasin.quarantaine)
    x = _lot(s, FOND, g=q)
    refus = _refus(rebut.mettre_au_rebut, s, acteur(s, Role.alimentation), _demande(s, x, q.id))
    assert refus.http == 403 and refus.detail == rebut.REFUS_QUARANTAINE
    o = rebut.mettre_au_rebut(s, acteur(s, Role.achats), _demande(s, x, q.id))
    assert o.statut == StatutDocument.validee and _solde(s, x, q.id) == 0


def test_alimentation_met_un_fond_de_lot_au_rebut_hors_quarantaine(s: Session) -> None:
    """L'alimentation ne fait pas d'ajustement (S82) sauf ce geste : un fond de lot hors
    quarantaine ; l'opération porte son nom."""
    x, g = _lot(s, FOND), magasin(s)
    qui = acteur(s, Role.alimentation)
    o = rebut.mettre_au_rebut(s, qui, _demande(s, x, g.id))
    assert o.statut == StatutDocument.validee and o.validee_par_id == qui.id


def test_periode_close_inventaire_en_cours_et_version_perimee(s: Session) -> None:
    """Les règles habituelles d'un ajustement : période close (409 `periode_close`), inventaire
    ouvert sur la matière dans ce magasin (409), version du lot périmée (409 `conflit_version`),
    lot ou magasin inconnu."""
    x, g = _lot(s, FOND), magasin(s)
    qui = acteur(s, Role.achats)
    refus = _refus(rebut.mettre_au_rebut, s, qui, rebut.DemandeRebut(x.id, g.id, 7))
    assert refus.code == "conflit_version" and x.numero in refus.detail
    refus = _refus(rebut.mettre_au_rebut, s, qui, rebut.DemandeRebut(x.id, 999_999, 1))
    assert refus.code == "valeur_inconnue"
    refus = _refus(rebut.mettre_au_rebut, s, qui, rebut.DemandeRebut(999_999, g.id, 1))
    assert refus.http == 404
    inventaire_ouvert(s, g, [s.get_one(Matiere, x.matiere_id)])
    refus = _refus(rebut.mettre_au_rebut, s, qui, _demande(s, x, g.id))
    assert refus.code == "inventaire_en_cours"
    s.rollback()
    x, g = _lot(s, FOND), magasin(s)
    p = s.get(Parametre, "date_cloture")
    assert p is not None
    p.valeur = JOUR.isoformat()
    s.flush()
    refus = _refus(rebut.mettre_au_rebut, s, acteur(s, Role.achats), _demande(s, x, g.id))
    assert refus.code == "periode_close"


def test_le_fil_sorti_vers_un_metier_n_est_pas_concerne(s: Session) -> None:
    """Un ordre sort tout un lot sauf 56 g : le reste en magasin est un fond de lot ; ce qui est
    parti aux machines n'est pas en stock et ne se met pas au rebut (rien en magasin ailleurs)."""
    a = atelier(s)
    poil = a.lot("E-L1")
    courant = a.m.courant
    reste = _solde(s, poil, courant.id) - FOND
    valide(s, acteur(s, Role.direction), saisie(courant.id, [(poil, reste)]))
    x = lots.lister(s, lots.FiltresLots(lot_id=poil.id))[0]
    assert x.fond_de_lot and x.fond_de_lot_kg == FOND and x.historique.sorti == reste


# --- API (données validées en base, clients par rôle) ---------------------------------------


@pytest.fixture
def base() -> Iterator[Session]:
    """Une session dont les écritures sont validées."""
    with fabrique()() as session:
        yield session


def _ok(r: Any, code: int = 200) -> Any:
    assert r.status_code == code, r.text
    return r.json() if r.content else None


def _fond_en_base(base: Session, q: Decimal = FOND) -> tuple[int, int, str]:
    """Un lot de `q` kg à 20 MAD/kg, validé en base : (lot_id, magasin_id, référence)."""
    m = matiere(base)
    x = _lot(base, q, m=m)
    g = magasin(base)
    base.commit()
    return x.id, g.id, m.reference


def _lot_api(client: TestClient, lot_id: int) -> dict[str, Any]:
    return _ok(client.get(f"/api/lots/{lot_id}"))  # type: ignore[no-any-return]


def test_api_alimentation_rebut_au_telephone_sans_prix(
    base: Session, alimentation: TestClient, direction: TestClient
) -> None:
    """Route 258 : la liste 107 marque le fond ; l'alimentation le met au rebut (201, opération
    validée) sans qu'aucune clé monétaire porte une valeur ; le lot quitte la liste en stock ;
    la fiche du lot (direction) montre l'écriture « Rebut » valorisée ; le bilan du mois compte
    le rebut dans ses ajustements."""
    avant = _ok(direction.get("/api/bilan", params={"mois": JOUR.strftime("%Y-%m")}))
    lot_id, magasin_id, reference = _fond_en_base(base)
    liste = _ok(alimentation.get("/api/lots", params={"q": reference}))
    assert [x["fond_de_lot"] for x in liste] == [True] and liste[0]["fond_de_lot_kg"] == 0.056
    assert liste[0]["magasins"][0]["fond_de_lot"] is True and liste[0]["version"] == 1
    assert fuites(liste) == []
    r = alimentation.post(
        f"/api/lots/{lot_id}/rebut", json={"magasin_id": magasin_id, "version": 1}
    )
    o = _ok(r, 201)
    assert o["statut"] == "validee" and o["numero"].startswith("AJU-") and o["motif"] == "Rebut"
    assert fuites(o) == []
    assert _ok(alimentation.get("/api/lots", params={"q": reference})) == []
    fiche = _lot_api(direction, lot_id)
    ecrit = next(m for m in fiche["mouvements"] if m["document_numero"] == o["numero"])
    assert ecrit["quantite"] == -0.056 and ecrit["motif"] == "Rebut"
    assert fiche["version"] == 2 and fiche["quantite"] == 0
    valorises = _ok(direction.get("/api/mouvements", params={"lot": lot_id, "avec_valeur": "true"}))
    rebut_valorise = next(m for m in valorises["elements"] if m["document_numero"] == o["numero"])
    assert rebut_valorise["cout_mad"] == 20 and round(rebut_valorise["valeur_mad"], 3) == -1.12
    apres = _ok(direction.get("/api/bilan", params={"mois": JOUR.strftime("%Y-%m")}))
    assert round(apres["ajustements_kg"] - avant["ajustements_kg"], 3) == -0.056


def test_api_refus_409_et_droits(
    base: Session, achats: TestClient, alimentation: TestClient, direction: TestClient
) -> None:
    """Version périmée → 409 `conflit_version` ; 3,151 kg → 409 `pas_un_fond_de_lot` pour les
    achats, 422 pour la direction sans motif, 201 avec ; la proposition 134 n'offre pas un fond
    de lot et le nomme ; un fond de lot en quarantaine → 403 pour l'alimentation."""
    lot_id, magasin_id, _ = _fond_en_base(base, Decimal("3.151"))
    r = achats.post(f"/api/lots/{lot_id}/rebut", json={"magasin_id": magasin_id, "version": 9})
    assert r.status_code == 409 and r.json()["code"] == "conflit_version"
    r = achats.post(f"/api/lots/{lot_id}/rebut", json={"magasin_id": magasin_id, "version": 1})
    assert r.status_code == 409 and r.json()["code"] == "pas_un_fond_de_lot"
    corps = {"magasin_id": magasin_id, "version": 1, "motif": ""}
    r = direction.post(f"/api/lots/{lot_id}/rebut", json=corps)
    assert r.status_code == 422 and r.json()["code"] == "motif_requis"
    corps["motif"] = "Fil taché, bon à jeter"
    assert _ok(direction.post(f"/api/lots/{lot_id}/rebut", json=corps), 201)["statut"] == "validee"
    q = magasin(base, TypeMagasin.quarantaine)
    x = _lot(base, FOND, g=q)
    base.commit()
    r = alimentation.post(f"/api/lots/{x.id}/rebut", json={"magasin_id": q.id, "version": 1})
    assert r.status_code == 403 and r.json()["detail"] == rebut.REFUS_QUARANTAINE
    assert _ok(achats.post(f"/api/lots/{x.id}/rebut", json={"magasin_id": q.id, "version": 1}), 201)
