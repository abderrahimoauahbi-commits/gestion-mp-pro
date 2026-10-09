"""Les contrôles par l'API, un essai par contrôle (lot D8 ; LOTS § 2 : C01–C19 ici, la suite dans
`test_controles_api_suite.py`).

Chaque essai pose, dans une usine isolée (`fabriques.pilotage.usine`), la donnée qui fait sonner
son contrôle, le lit par `GET /api/controles/{code}` (détail complet, cherché, avec les ids des
fiches) et par la liste `GET /api/controles` (verdict, gravité, quoi faire, lien), puis vérifie
qu'il se tait quand la donnée est corrigée ou absente. Les contrôles « garantis » (la base ou la
saisie les rend impossibles) sont dans la suite.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import Any

from fabrique import *  # noqa: F403
from fabriques import referentiels as ref
from fabriques.pilotage import Usine, fixture_usine, jour, ok  # noqa: F401
from fabriques.stock import matiere as matiere_sans_fournisseur
from sqlalchemy import text

from gestion_mp_pro.modeles import Matiere, Parametre
from gestion_mp_pro.modeles.enums import TypeMouvement


def detail(u: Usine, code: str, **params: Any) -> dict[str, Any]:
    """Le détail d'un contrôle (route 235)."""
    return u.get(u.achats, f"/api/controles/{code}", **params)  # type: ignore[no-any-return]


def verdict(u: Usine, code: str, **params: Any) -> dict[str, Any]:
    """Le contrôle tel que la liste le rend (route 212)."""
    liste = u.get(u.direction, "/api/controles", **params)["controles"]
    return next(c for c in liste if c["code"] == code)  # type: ignore[no-any-return]


def lignes(u: Usine, code: str, **params: Any) -> list[dict[str, Any]]:
    """Toutes les lignes d'un contrôle."""
    return detail(u, code, **params)["elements"]  # type: ignore[no-any-return]


def reglage(u: Usine, cle: str, valeur: str) -> None:
    """Un réglage changé dans la transaction de l'essai."""
    p = u.s.get(Parametre, cle)
    assert p is not None
    p.valeur = valeur
    u.s.flush()


def test_chaque_controle_dit_quoi_faire_et_ou(usine: Usine) -> None:
    """Hérité : test_direction::test_chaque_controle_dit_quoi_faire (38 contrôles, `quoi_faire`,
    lien vers un écran, colonnes libellées) ;
    test_defauts_e::test_colonnes_controles_toutes_libellees."""
    u = usine
    m = u.matiere()
    u.ouvrir(m, 10, 5)
    r = u.get(u.achats, "/api/controles")
    assert len(r["controles"]) == 38
    assert [c["code"] for c in r["controles"]] == [f"C{n:02d}" for n in range(1, 39)]
    for c in r["controles"]:
        assert c["quoi_faire"] and c["lien"].startswith("/"), c["code"]
        assert c["gravite"] in {"bloquant", "avertissement", "information"}
        cles = {x["cle"] for x in c["colonnes"]}
        for ligne in c["lignes"]:
            assert set(ligne) - cles <= {
                "matiere_id", "lot_id", "ordre_id", "metier_id", "commande_id", "dossier_id",
                "reception_id", "qualite_id", "fournisseur_id",
            }, c["code"]  # fmt: skip
    note = r["synthese"]
    assert note["total"] + note["garantis"] == 38
    assert note["anomalies"] == sum(1 for c in r["controles"] if not c["conforme"])


def test_c01_recette_hors_cent(usine: Usine) -> None:
    """C01 : une recette à 60 % sur le poil sonne, avec l'id de la qualité ; à 100 %, non."""
    u = usine
    m = u.matiere()
    qid = ref.qualite("Q-C01", recette={m: 60}, poids={"Poil": "1"}, s=u.s)
    x = lignes(u, "C01")
    assert [(y["qualite"], y["qualite_id"]) for y in x] == [("Q-C01", qid)]
    assert "60 %" in x[0]["roles"]
    c = verdict(u, "C01")
    assert (c["gravite"], c["lien"], c["anomalies"]) == ("bloquant", "/qualites", 1)
    u.s.execute(text("UPDATE recette SET pourcentage = 100 WHERE qualite_id = :q"), {"q": qid})
    assert lignes(u, "C01") == []


def test_c02_sortie_sans_ordre(usine: Usine) -> None:
    """C02 : une sortie vers les machines sans ordre (stock repris) sonne ; avec son ordre, non."""
    u = usine
    m = u.matiere("C02-FIL")
    x = u.ouvrir(m, 100, 5)
    u.sortir(x, 10, ordre_id=u.ordre("OF-2026-0101"))
    assert lignes(u, "C02") == []
    assert verdict(u, "C02")["garanti"]
    u.sortir(x, 5)
    assert [(y["reference"], y["matiere_id"]) for y in lignes(u, "C02")] == [("C02-FIL", m)]


def test_c03_retour_sans_motif(usine: Usine) -> None:
    """C03 : un retour des machines sans motif sonne (motif « — »)."""
    u = usine
    x = u.ouvrir(u.matiere("C03-FIL"), 100, 5)
    u.sortir(x, 30)
    assert lignes(u, "C03") == []
    u.ecrire(x, 10, type_=TypeMouvement.RETOUR_MACHINE)
    y = lignes(u, "C03")
    assert [(z["reference"], z["motif"]) for z in y] == [("C03-FIL", "—")]


def test_c04_mouvement_sans_auteur(usine: Usine) -> None:
    """C04 : une écriture sans auteur (reprise) sonne ; la saisie le garantit sinon."""
    u = usine
    x = u.ouvrir(u.matiere("C04-FIL"), 100, 5)
    assert verdict(u, "C04")["garanti"]
    u.ecrire(x, 5, auteur=False)
    assert [y["reference"] for y in lignes(u, "C04")] == ["C04-FIL"]


def test_c05_matiere_sans_fournisseur(usine: Usine) -> None:
    """C05 : une matière en service sans fournisseur sonne ; désactivée, non (E-07)."""
    u = usine
    m = matiere_sans_fournisseur(u.s, "C05-FIL")
    assert [(y["reference"], y["matiere_id"]) for y in lignes(u, "C05")] == [("C05-FIL", m.id)]
    m.actif = False
    assert lignes(u, "C05") == []


def test_c06_commande_en_retard(usine: Usine) -> None:
    """C06 : un bon parti il y a 30 jours, promis il y a 20, rien reçu : en retard (même
    échéance que l'écran Commandes)."""
    u = usine
    f = u.fournisseur("C06 FILATURE", delai_jours=10)
    m = u.matiere(fournisseur_id=f)
    cid = u.commande(f, m, 100, le=jour(-30), promise=jour(-20), numero="BC-2026-0601")
    x = lignes(u, "C06")
    assert [(y["numero"], y["commande_id"], y["retard_jours"]) for y in x] == [
        ("BC-2026-0601", cid, 20)
    ]
    assert verdict(u, "C06")["lien"] == "/commandes?filtre=retard"


def test_c07_matiere_jamais_utilisee_et_liste_coupee_a_200(usine: Usine) -> None:
    """C07 : 205 matières jamais utilisées ; la liste en rend 200 en le disant, le détail les
    rend toutes, page par page (A2) ; une matière qui a bougé n'y est plus."""
    u = usine
    ids = [u.matiere(f"C07-{n:03d}", fournisseur_id=u.fournisseur()) for n in range(205)]
    c = verdict(u, "C07")
    assert (c["anomalies"], len(c["lignes"]), c["lignes_total"], c["tronque"]) == (
        205, 200, 205, True,
    )  # fmt: skip
    vus, apres = [], None
    while True:
        page = detail(u, "C07", limite=100, **({"apres": apres} if apres else {}))
        vus += page["elements"]
        apres = page["suivant"]
        if apres is None:
            break
    assert len(vus) == 205 and page["total"] == 205
    assert len(detail(u, "C07", q="c07 004")["elements"]) == 1
    u.ouvrir(ids[0], 1, 1)
    assert "C07-000" not in {y["reference"] for y in lignes(u, "C07")}


def test_c08_ecart_de_pesee_en_fraction(usine: Usine) -> None:
    """C08 : 90 kg pesés pour 100 au BL sonnent ; l'écart est une **fraction** (P8-3)."""
    u = usine
    f = u.fournisseur("C08 FILATURE")
    m = u.matiere("C08-FIL", fournisseur_id=f)
    r = ok(u.achats.post("/api/receptions", json={
        "date": jour().isoformat(), "fournisseur_id": f, "lignes": [
            {"matiere_id": m, "lot_numero": "C08-1", "quantite_bl": 100, "quantite_pesee": 90,
             "magasin_id": u.courant, "prix": 10}]}), 201)[0]  # fmt: skip
    ok(u.achats.post(f"/api/receptions/{r['id']}/valider", json={"version": r["version"]}))
    x = lignes(u, "C08")
    assert len(x) == 1 and x[0]["ecart"] == -0.1 and x[0]["reception_id"] == r["id"]
    unite = {k["cle"]: k["unite"] for k in detail(u, "C08")["colonnes"]}
    assert unite["ecart"] == "%"


def test_c12_soldes_confrontes_au_journal(usine: Usine) -> None:
    """Hérité : test_valorisation::test_api_c12_confronte_les_soldes_au_journal — un solde
    faussé de +5 kg sonne (lot, tenu 105, attendu 100), aussi à une date passée."""
    u = usine
    x = u.ouvrir(u.matiere("C12-FIL"), 100, 10, le=jour(-20))
    assert lignes(u, "C12") == []
    u.s.execute(text("UPDATE solde SET quantite = quantite + 5 WHERE lot_id = :l"), {"l": x.id})
    y = lignes(u, "C12")
    assert [(z["lot"], z["lot_id"], z["stock"], z["attendu"]) for z in y] == [
        (x.numero, x.id, 105, 100)
    ]
    assert lignes(u, "C12", date=jour(-10).isoformat())
    assert verdict(u, "C12")["gravite"] == "bloquant"


def _consommee(u: Usine, reference: str, **champs: Any) -> int:
    """Une matière d'une recette planifiée à 1 000 m² par mois, 1 kg/m² : elle se consomme."""
    m = u.matiere(reference, **champs)
    ref.qualite(recette={m: 100}, poids={"Poil": "1"}, base_mensuelle="1000", s=u.s)
    return m


def test_c13_et_c17_rupture_projetee_mono_source(usine: Usine) -> None:
    """C13 : sans stock ni commande, le projeté passe sous zéro pendant le délai ; C17 : la
    matière en alerte n'a pas de second fournisseur. Désactivée : C13 se tait (E-07)."""
    u = usine
    m = _consommee(u, "C13-FIL")
    x = [y for y in lignes(u, "C13") if y["reference"] == "C13-FIL"]
    assert len(x) == 1 and x[0]["manque"] > 0 and x[0]["matiere_id"] == m
    assert "C13-FIL" in {y["reference"] for y in lignes(u, "C17")}
    fiche = u.s.get(Matiere, m)
    assert fiche is not None
    fiche.actif = False
    assert "C13-FIL" not in {y["reference"] for y in lignes(u, "C13")}


def test_c14_mouvement_date_apres_aujourd_hui(usine: Usine, horloge_fixe: Any) -> None:
    """Hérité : test_valeur_et_dates::test_c12_et_c14_voient_une_ecriture_datee_apres_aujourd_hui
    (C14) — une écriture datée de demain sonne, aussi à une date passée (toutes les données)."""
    u = usine
    m = u.matiere("C14-FIL")
    x = u.ouvrir(m, 100, 10)
    from gestion_mp_pro.services import horloge

    horloge.fixer(horloge_fixe + timedelta(days=5))
    u.ecrire(x, 5, le=jour(5))
    horloge.fixer(horloge_fixe)
    assert [y["reference"] for y in lignes(u, "C14")] == ["C14-FIL"]
    assert [y["reference"] for y in lignes(u, "C14", date=jour(-3).isoformat())] == ["C14-FIL"]


def test_c15_recette_sans_prix_ou_desactivee(usine: Usine) -> None:
    """C15 : une matière sans prix dans une recette sonne ; désactivée, elle le dit (E-07)."""
    u = usine
    m = u.matiere("C15-FIL", prix="0")
    ref.qualite("Q-C15", recette={m: 100}, poids={"Poil": "1"}, s=u.s)
    assert [(y["reference"], y["motif"]) for y in lignes(u, "C15")] == [
        ("C15-FIL", "sans prix d'achat")
    ]
    fiche = u.s.get(Matiere, m)
    assert fiche is not None
    fiche.prix, fiche.actif = Decimal(5), False
    assert lignes(u, "C15")[0]["motif"] == "matière désactivée encore dans la recette"


def test_c18_une_matiere_recue_recemment_ne_dort_pas(usine: Usine) -> None:
    """Hérité : test_valeur_et_dates::test_une_matiere_recue_recemment_ne_dort_pas — neuve :
    0 jour, pas dormante ; reçue il y a 200 jours : dormante, C18 la dit (stock 10)."""
    u = usine
    u.ouvrir(u.matiere("C18 NEUVE"), 10, 10)
    u.ouvrir(u.matiere("C18 VIEILLE"), 10, 10, le=jour(-200))
    stock = {x["reference"]: x for x in u.get(u.achats, "/api/stock")["lignes"]}
    assert not stock["C18 NEUVE"]["dormant"] and stock["C18 NEUVE"]["jours_sans_mouvement"] == 0
    assert stock["C18 VIEILLE"]["dormant"]
    assert stock["C18 VIEILLE"]["jours_sans_mouvement"] == 200
    c18 = {x["reference"]: x for x in lignes(u, "C18")}
    assert "C18 NEUVE" not in c18 and c18["C18 VIEILLE"]["stock"] == 10


def test_c19_fournisseur_en_plusieurs_devises(usine: Usine) -> None:
    """C19 : un fournisseur dont deux matières en service sont en USD et en EUR sonne ; une
    matière désactivée ne compte pas (E-07)."""
    u = usine
    f = u.fournisseur("C19 FILATURE", devise="USD")
    u.matiere(fournisseur_id=f, devise="USD")
    m = u.matiere(fournisseur_id=f, devise="EUR")
    x = lignes(u, "C19")
    assert [(y["fournisseur"], y["fournisseur_id"]) for y in x] == [("C19 FILATURE", f)]
    fiche = u.s.get(Matiere, m)
    assert fiche is not None
    fiche.actif = False
    assert lignes(u, "C19") == []
