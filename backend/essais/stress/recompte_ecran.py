"""Les chiffres de l'écran recomptés en SQL, par un autre chemin (épreuve d'écran, phase B).

Pour la base parcourue, les totaux que les écrans affichent sont relus par l'API du serveur
jetable (session de direction) et recomptés directement dans la base : stock et valorisation
(kilos en magasin, matières en stock), plan et réalisé (m² réalisés par qualité, chaque année
des dix), échéancier (factures non réglées), listes paginées (totaux des mouvements, du journal,
des bons, des réceptions, des ordres contre `count(*)`), cockpit (cohérent avec la valorisation).
Un écart désigne un défaut de PRO ; rien n'est écrit.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from charge_serveur import Poste
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

KG = 0.01
M2 = 0.01


def _sql(adresse: str, requete: str, **p: Any) -> Any:
    moteur = create_engine(adresse, poolclass=NullPool)
    with moteur.connect() as c:
        valeur = c.execute(text(requete), p).scalar()
    moteur.dispose()
    return valeur


def _juger(lignes: list[dict[str, Any]], quoi: str, ecran: Any, sql: Any, tol: float = 0) -> None:
    ecran_f, sql_f = float(ecran or 0), float(sql or 0)
    ok = abs(ecran_f - sql_f) <= tol
    lignes.append({"quoi": quoi, "ecran": ecran_f, "sql": sql_f, "ok": ok})


def _stock(p: Poste, adresse: str, lignes: list[dict[str, Any]]) -> None:
    v = p.get("/api/valorisation")
    _juger(lignes, "Valorisation : kg en magasin = Σ soldes", v["total_kg_magasin"],
           _sql(adresse, "SELECT coalesce(sum(quantite), 0) FROM solde"), KG)  # fmt: skip
    _juger(lignes, "Valorisation : matières en stock = matières à solde > 0", v["nb_en_stock"],
           _sql(adresse, "SELECT count(DISTINCT l.matiere_id) FROM solde s JOIN lot l "
                "ON l.id = s.lot_id WHERE s.quantite > 0"))  # fmt: skip
    stock = p.get("/api/stock")
    elements = stock["elements"] if isinstance(stock, dict) and "elements" in stock else stock
    if isinstance(stock, dict) and "lignes" in stock:
        elements = stock["lignes"]
    total = sum(float(x.get("stock_net") or 0) for x in elements)
    _juger(lignes, "Stock par matière : Σ stock (kg) = valorisation (kg)", total,
           v["total_kg"], KG)  # fmt: skip
    c = p.get("/api/cockpit")
    valeur = c.get("stock", {}).get("valeur_magasins_mad")
    if valeur is not None:
        _juger(
            lignes,
            "Cockpit : valeur en magasins = valorisation (MAD)",
            valeur,
            v["total_magasin_mad"],
            1,
        )


def _realise(p: Poste, adresse: str, lignes: list[dict[str, Any]], jour: date) -> None:
    """Plan et réalisé : les m² réalisés des douze mois (le mois en cours jusqu'au jour de
    référence), pour chaque année des dix."""
    for recul in range(10):
        fin = date(jour.year - recul, jour.month, jour.day)
        r = p.get(f"/api/production/realise?date={fin.isoformat()}")
        mois = r.get("mois") or []
        if not mois:
            break
        premier, dernier = mois[0], mois[-1]
        total_ecran = sum(float(q.get("total_realise") or 0) for q in r.get("lignes", []))
        total_sql = _sql(
            adresse,
            "SELECT coalesce(sum(oq.m2), 0) FROM ordre_qualite oq JOIN ordre o ON o.id = "
            "oq.ordre_id WHERE o.statut = 'valide' AND to_char(o.date, 'YYYY-MM') >= :a "
            "AND o.date <= :b",
            a=str(premier)[:7],
            b=min(date.fromisoformat(str(dernier)), fin),
        )
        _juger(lignes, f"Plan et réalisé {premier}→{dernier} : Σ m² réalisés", total_ecran,
               total_sql, M2 * max(1, len(r.get("lignes", []))))  # fmt: skip


def _listes(p: Poste, adresse: str, lignes: list[dict[str, Any]]) -> None:
    """Les totaux des listes paginées contre `count(*)`."""
    cas = (
        ("/api/mouvements?limite=1", "Mouvements : total", "SELECT count(*) FROM mouvement"),
        ("/api/journal?limite=1", "Journal : total", "SELECT count(*) FROM journal"),
        (
            "/api/receptions?statut=validee&limite=1",
            "Réceptions validées : total",
            "SELECT count(*) FROM reception WHERE statut = 'validee'",
        ),  # fmt: skip
        (
            "/api/ordres?statut=valide&limite=1",
            "Ordres validés : total",
            "SELECT count(*) FROM ordre WHERE statut = 'valide'",
        ),  # fmt: skip
        ("/api/operations?limite=1", "Opérations : total", "SELECT count(*) FROM operation"),
        (
            "/api/dossiers?statut=clos&limite=1",
            "Dossiers clos : total",
            "SELECT count(*) FROM dossier WHERE statut = 'clos'",
        ),  # fmt: skip
    )
    for route, quoi, requete in cas:
        page = p.get(route)
        _juger(lignes, quoi, page.get("total"), _sql(adresse, requete))
    apercu = p.get("/api/commandes/apercu")
    requete = "SELECT count(*) FROM commande WHERE statut = :s"
    for statut in ("brouillon", "envoyee", "confirmee"):
        if statut in apercu:
            quoi = f"Commandes « {statut} » : compte de l'onglet"
            _juger(lignes, quoi, apercu[statut], _sql(adresse, requete, s=statut))


def _echeancier(p: Poste, adresse: str, lignes: list[dict[str, Any]]) -> None:
    e = p.get("/api/echeancier")
    factures = [x for x in e["lignes"] if x.get("objet") == "facture"]
    non_reglees = _sql(adresse, "SELECT count(*) FROM facture WHERE payee_le IS NULL")
    _juger(lignes, "Échéancier : factures non réglées = factures sans règlement", len(factures),
           non_reglees)  # fmt: skip
    montants = [float(x.get("montant_mad") or 0) for x in e["lignes"]]
    echus = [float(x.get("montant_mad") or 0) for x in e["lignes"] if x.get("en_retard")]
    _juger(lignes, "Échéancier : total MAD = Σ des lignes", e["total_mad"], sum(montants), 1)
    _juger(lignes, "Échéancier : échu = Σ des lignes échues", e["echu_mad"], sum(echus), 1)


def recompter(poste: Poste, adresse: str, jour: date) -> list[dict[str, Any]]:
    """Tous les recomptes ; rend les lignes (quoi, écran, sql, ok)."""
    lignes: list[dict[str, Any]] = []
    for etape in (_stock, _listes, _echeancier):
        try:
            etape(poste, adresse, lignes)
        except Exception as exc:  # noqa: BLE001 — un écran qui ne répond pas est consigné, pas fatal
            lignes.append({"quoi": f"{etape.__name__} : {exc!s:.200}", "ecran": None,
                           "sql": None, "ok": False})  # fmt: skip
    try:
        _realise(poste, adresse, lignes, jour)
    except Exception as exc:  # noqa: BLE001
        lignes.append({"quoi": f"réalisé : {exc!s:.200}", "ecran": None, "sql": None, "ok": False})
    return lignes
