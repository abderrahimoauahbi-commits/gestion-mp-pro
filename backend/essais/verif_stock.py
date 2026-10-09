"""Stock, soldes, lots et données brutes, recomptés en SQL (lot V1).

- Données brutes (route 7) = la base, table par table, ligne par ligne ; à une date, le même
  nombre de lignes datées.
- Stock de chaque matière à chaque date : Σ du journal jusqu'au soir de la date, magasins
  (quarantaine comprise) ; quarantaine à part ; par magasin ; disponible = net − quarantaine.
- Soldes = journal, jamais négatifs ; contrôle des soldes (route 113) d'accord.
- Aucun lot sous zéro à aucune date passée (cumul du soir, l'ordre dans la journée ne compte
  pas : C37).
- Chaque lot à chaque date : Σ journal, quarantaine, disponible.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from verif_socle import KG, POUSSIERE, Acces, Releve, somme_par

DATEES = {
    "mouvement": "date_effet",
    "commande": "date_commande",
    "reception": "date",
    "ordre": "date",
    "operation": "date",
    "inventaire": "date",
    "facture": "date",
    "indicateur_jour": "jour",
}
"""Les tables que la route 7 borne à une date (même liste que sa documentation)."""


def _instant(v: str) -> Any:
    """Un texte qui est un instant ISO devient des secondes ; sinon il reste tel quel."""
    try:
        return datetime.fromisoformat(v).timestamp() if len(v) >= 19 and v[10] == "T" else v
    except ValueError:
        return v


def _propre(v: Any) -> Any:
    """Une valeur comparable : instants en secondes, dates en ISO, nombres en float."""
    if isinstance(v, str):
        return _instant(v)
    if isinstance(v, datetime):
        return v.timestamp()
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, int | float) and not isinstance(v, bool):
        return round(float(v), 6)
    return v if isinstance(v, bool) or v is None else str(v)


def donnees_brutes(a: Acces, r: Releve, dates: list[date]) -> list[str]:
    """La route 7 rend la base telle quelle ; rend les tables lues."""
    nom = "Données brutes (route 7) = la base"
    tables = [
        t
        for (t,) in a.sql(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        )
    ]
    lues = []
    for table in sorted(tables):
        try:
            rendu = a.get(f"/donnees/{table}")
        except RuntimeError:
            continue  # table hors de la liste fermée (comptes, journal, sessions…)
        lues.append(table)
        cols = rendu["colonnes"]
        base = a.sql(f'SELECT {", ".join(cols)} FROM "{table}"')  # noqa: S608 (noms du catalogue)
        attendu = sorted((tuple(_propre(v) for v in x) for x in base), key=repr)
        vu = sorted((tuple(_propre(x[c]) for c in cols) for x in rendu["lignes"]), key=repr)
        diff = [x for x, y in zip(vu, attendu, strict=False) if x != y]
        r.juger(
            nom,
            table,
            len(vu) == len(attendu) and not diff,
            f"{len(vu)} ligne(s) rendue(s), {len(attendu)} en base ; 1re différente {diff[:1]}",
        )
        if table in DATEES:
            for d in dates:
                n = len(a.get(f"/donnees/{table}", date=d.isoformat())["lignes"])
                (m,) = a.sql(
                    f'SELECT count(*) FROM "{table}" WHERE {DATEES[table]} <= %s',  # noqa: S608
                    (d,),
                )[0]
                r.juger(nom, f"{table} au {d}", n == m, f"{n} ligne(s) rendue(s), {m} en base")
    return lues


def stock_par_matiere(a: Acces, r: Releve, dates: list[date]) -> None:
    """Stock net, quarantaine, disponible et par magasin de chaque matière, à chaque date."""
    nom = "Stock de chaque matière (Σ journal, quarantaine à part), aux 13 dates"
    noms = dict(a.sql("SELECT id, code FROM magasin"))
    for d in dates:
        lignes = a.sql(
            "SELECT m.matiere_id, m.magasin_id, g.type = 'quarantaine', SUM(m.quantite) "
            "FROM mouvement m JOIN magasin g ON g.id = m.magasin_id WHERE m.date_effet <= %s "
            "GROUP BY 1, 2, 3",
            (d,),
        )
        net = somme_par(lignes)
        quarantaine = somme_par([x for x in lignes if x[2]])
        par_magasin = somme_par(lignes, cle=lambda x: (x[0], noms[x[1]]))
        ecran = {x["matiere_id"]: x for x in a.get("/stock", date=d.isoformat())["lignes"]}
        for mid in sorted(set(net) | set(ecran)):
            x = ecran.get(mid)
            sujet = f"matière {mid} au {d}"
            if x is None:
                r.juger(nom, sujet, abs(net[mid]) <= POUSSIERE, "absente de l'écran Stock")
                continue
            r.comparer(nom, sujet + " (net)", x["stock_net"], net.get(mid, 0.0), KG)
            r.comparer(
                nom, sujet + " (quarantaine)", x["stock_quarantaine"], quarantaine.get(mid, 0.0), KG
            )
            r.comparer(
                nom,
                sujet + " (disponible)",
                x["stock_disponible"],
                net.get(mid, 0.0) - quarantaine.get(mid, 0.0),
                KG,
            )
            for magasin, q in (x.get("par_magasin") or {}).items():
                attendu = par_magasin.get((mid, magasin), 0.0)
                if abs(q) > POUSSIERE or abs(attendu) > POUSSIERE:  # un magasin vide : rien à dire
                    r.comparer(nom, f"{sujet} ({magasin})", q, attendu, KG)


def soldes(a: Acces, r: Releve) -> None:
    """Chaque solde = Σ de son journal, aucun négatif ; le contrôle des soldes d'accord."""
    nom = "Soldes égaux au journal, jamais négatifs"
    lignes = a.sql(
        "SELECT COALESCE(s.lot_id, j.lot_id), COALESCE(s.magasin_id, j.magasin_id), "
        "COALESCE(s.quantite, 0), COALESCE(j.q, 0) FROM solde s FULL JOIN "
        "(SELECT lot_id, magasin_id, SUM(quantite) AS q FROM mouvement GROUP BY 1, 2) j "
        "ON j.lot_id = s.lot_id AND j.magasin_id = s.magasin_id"
    )
    faux = 0
    for lot, magasin, q, journal in lignes:
        juste = abs(q - journal) <= POUSSIERE
        faux += not juste
        r.juger(nom, f"lot {lot}, magasin {magasin}", juste, f"solde {q}, journal {journal}")
        r.juger(nom, f"lot {lot}, magasin {magasin} positif", q >= -POUSSIERE, f"solde {q}")
    ecran = a.get("/controles/soldes")
    r.juger(
        nom,
        "contrôle des soldes (route 113) : écarts",
        len(ecran["ecarts"]) == faux,
        f"écran {len(ecran['ecarts'])}, recompté {faux}",
    )
    negatifs = sum(1 for x in lignes if x[2] < -POUSSIERE)
    r.juger(
        nom,
        "contrôle des soldes : négatifs",
        ecran["negatifs"] == negatifs,
        f"écran {ecran['negatifs']}, recompté {negatifs}",
    )


def sous_zero_passe(a: Acces) -> list[tuple[Any, ...]]:
    """(matière, lot, magasin, premier jour, creux) des lots passés sous zéro un soir."""
    return a.sql(
        "WITH jours AS (SELECT lot_id, magasin_id, date_effet, SUM(quantite) AS q "
        "  FROM mouvement GROUP BY 1, 2, 3), "
        "cumul AS (SELECT lot_id, magasin_id, date_effet, SUM(q) OVER (PARTITION BY lot_id, "
        "  magasin_id ORDER BY date_effet) AS reste FROM jours) "
        "SELECT l.matiere_id, c.lot_id, c.magasin_id, MIN(c.date_effet), MIN(c.reste) "
        "FROM cumul c JOIN lot l ON l.id = c.lot_id WHERE c.reste < %s GROUP BY 1, 2, 3",
        (-POUSSIERE,),
    )


def lots_sous_zero(a: Acces, r: Releve) -> None:
    """Aucun lot sous zéro à une date passée ; C37 en dit autant."""
    nom = "Aucun lot sous zéro à une date passée"
    faux = sous_zero_passe(a)
    (n,) = a.sql("SELECT count(DISTINCT (lot_id, magasin_id)) FROM mouvement")[0]
    r.famille(nom).cas += max(int(n) - len(faux), 0)
    for mat, lot, magasin, jour, creux in faux:
        r.juger(
            nom,
            f"matière {mat} · lot {lot} · magasin {magasin}",
            False,
            f"{creux:.3f} kg le soir du {jour}",
        )


def _presents(a: Acces, d: date) -> list[tuple[Any, ...]]:
    """(lot, quarantaine ?, kg) que chaque lot pouvait donner au soir de `d` : le moins qu'il a
    porté ce soir-là ou un soir suivant (ce qui en est sorti depuis est déjà parti), rien s'il
    est entré après (route 107 à une date passée)."""
    return a.sql(
        "WITH jours AS (SELECT lot_id, magasin_id, date_effet, SUM(quantite) AS q "
        "  FROM mouvement GROUP BY 1, 2, 3), "
        "cumul AS (SELECT lot_id, magasin_id, date_effet, SUM(q) OVER (PARTITION BY lot_id, "
        "  magasin_id ORDER BY date_effet) AS reste FROM jours), "
        "au_soir AS (SELECT s.lot_id, s.magasin_id, COALESCE((SELECT c.reste FROM cumul c "
        "  WHERE c.lot_id = s.lot_id AND c.magasin_id = s.magasin_id AND c.date_effet <= %(d)s "
        "  ORDER BY c.date_effet DESC LIMIT 1), 0) AS q FROM solde s), "
        "ensuite AS (SELECT lot_id, magasin_id, MIN(reste) AS q FROM cumul "
        "  WHERE date_effet > %(d)s GROUP BY 1, 2) "
        "SELECT x.lot_id, g.type = 'quarantaine', CASE WHEN l.entre_le > %(d)s THEN 0 "
        "  ELSE GREATEST(0, LEAST(x.q, COALESCE(e.q, x.q))) END "
        "FROM au_soir x JOIN lot l ON l.id = x.lot_id JOIN magasin g ON g.id = x.magasin_id "
        "LEFT JOIN ensuite e ON e.lot_id = x.lot_id AND e.magasin_id = x.magasin_id",
        {"d": d},
    )


def lots(a: Acces, r: Releve, dates: list[date]) -> None:
    """Chaque lot, à chaque date : ce qu'il pouvait donner (aujourd'hui : son solde),
    quarantaine, disponible (route 107)."""
    nom = "Chaque lot (route 107) = son journal, aux 13 dates"
    histoire = histoires(a)
    for d in dates:
        lignes = _presents(a, d)
        total = somme_par(lignes)
        quarantaine = somme_par([x for x in lignes if x[1]])
        ecran = {x["lot_id"]: x for x in a.get("/lots", date=d.isoformat(), non_nuls="false")}
        for lot in sorted(set(total) | set(ecran)):
            x = ecran.get(lot)
            attendu = total.get(lot, 0.0)
            if x is None:
                r.juger(nom, f"lot {lot} au {d}", abs(attendu) <= POUSSIERE, "absent de l'écran")
                continue
            r.comparer(nom, f"lot {lot} au {d}", x["quantite"], attendu, KG)
            r.comparer(
                nom,
                f"lot {lot} au {d} (quarantaine)",
                x["quarantaine"],
                quarantaine.get(lot, 0.0),
                KG,
            )
            if d == dates[-1]:
                _histoire(r, nom, x, histoire.get(lot))
            r.comparer(
                nom,
                f"lot {lot} au {d} (disponible)",
                x["disponible"],
                attendu - quarantaine.get(lot, 0.0),
                KG,
            )


def histoires(a: Acces) -> dict[int, tuple[float, float, Any]]:
    """(entré, sorti, dernier mouvement) de chaque lot (CALCULS B § 6.2) : une annulation et
    ce qu'elle annule ne comptent ni à l'aller ni au retour, un transfert ne fait que déplacer,
    un retour des machines réduit le sorti."""
    return {
        lot: (float(entre), float(sorti), dernier)
        for lot, entre, sorti, dernier in a.sql(
            "WITH annules AS (SELECT contrepasse_id AS id FROM mouvement "
            "  WHERE contrepasse_id IS NOT NULL), "
            "comptes AS (SELECT * FROM mouvement m WHERE m.contrepasse_id IS NULL "
            "  AND m.type <> 'TRANSFERT' AND m.id NOT IN (SELECT id FROM annules)) "
            "SELECT l.lot_id, "
            "COALESCE((SELECT SUM(quantite) FROM comptes c WHERE c.lot_id = l.lot_id "
            "  AND c.type <> 'RETOUR_MACHINE' AND c.quantite > 0), 0), "
            "COALESCE((SELECT -SUM(quantite) FROM comptes c WHERE c.lot_id = l.lot_id "
            "  AND (c.type = 'RETOUR_MACHINE' OR c.quantite < 0)), 0), "
            "MAX(l.date_effet) FROM mouvement l GROUP BY l.lot_id"
        )
    }


def _histoire(r: Releve, nom: str, x: dict[str, Any], attendu: Any) -> None:
    """L'histoire d'un lot : entré, sorti, dernier mouvement ; entré − sorti = son stock."""
    entre, sorti, dernier = attendu or (0.0, 0.0, None)
    h = x["historique"]
    lot = x["lot_id"]
    r.comparer(nom, f"lot {lot} (entré)", h["entre"], entre, KG)
    r.comparer(nom, f"lot {lot} (sorti)", h["sorti"], sorti, KG)
    r.comparer(
        nom, f"lot {lot} (entré − sorti = reste)", h["entre"] - h["sorti"], x["quantite"], KG
    )
    vu = h["dernier_mouvement"]
    r.juger(
        nom,
        f"lot {lot} (dernier mouvement)",
        vu == (dernier.isoformat() if dernier else None),
        f"écran {vu}, base {dernier}",
    )
