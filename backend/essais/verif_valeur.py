"""La valeur du stock, jugée par des invariants et non par une copie du moteur (lot V1).

Reprend les invariants du vérificateur de Gestion MP (VERIFICATION § 1, 7a–7e) et les étend :

- le journal valorisé (route 105, `avec_valeur`) est la base : mêmes lignes, dates, quantités,
  prix, devises, **cours figés** ;
- la valeur se conserve : Σ des valeurs du journal jusqu'au soir d'une date = valeur en magasin
  de la Valorisation à cette date (à 1 MAD près), aux 13 dates ;
- aucune écriture à coût nul sans raison ; une annulation rend le coût de ce qu'elle annule ;
- ordre de grandeur : chaque lot qui reste, à son coût d'entrée (rapport dans [0,5 ; 2]) ;
- la Valorisation se tient : valeur = CMUP × stock (magasins, métiers), totaux = Σ lignes,
  écart au catalogue = valeur − stock × prix du catalogue au kilo × cours du jour ;
- deux pages, un chiffre : la valeur du Cockpit = le total de la Valorisation, à chaque date.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

import verif_cmup
from verif_couts import cout_d_entree_des_lots, couts_d_entree
from verif_socle import KG, MAD, POUSSIERE, Acces, Releve, cours_de, ecart

UN_MAD = 1.0
GRANDEUR = (0.5, 2.0)


def journal_valorise(a: Acces) -> list[dict[str, Any]]:
    """Tout le journal, tel que l'écran le valorise (par pages de 5 000)."""
    lignes: list[dict[str, Any]] = []
    apres = None
    while True:
        page = a.get("/mouvements", avec_valeur="true", limite=5000, apres=apres)
        lignes += page["elements"]
        apres = page["suivant"]
        if not apres:
            return lignes


def taux_du_jour(a: Acces) -> dict[str, float]:
    """Le cours du jour de chaque devise (table `devise`)."""
    return {code: float(c) for code, c in a.sql("SELECT code, cours FROM devise")}


def verifier(a: Acces, r: Releve, dates: list[date]) -> None:
    """Toutes les vérifications de la valeur."""
    journal = journal_valorise(a)
    _journal_egal_a_la_base(a, r, journal)
    taux = taux_du_jour(a)
    valos = {d: a.get("/valorisation", date=d.isoformat()) for d in dates}
    for d, valo in valos.items():
        _valeur_conservee(r, journal, valo, d)
        _valorisation_se_tient(a, r, valo, d, taux)
        _cockpit(a, r, valo, d)
    _cout_nul(a, r, journal)
    _annulations(r, journal)
    _ordre_de_grandeur(a, r, valos[dates[-1]], taux)
    _entrees_a_leur_cout(a, r, journal, taux)
    verif_cmup.verifier(a, r, journal=journal, valo=valos[dates[-1]], taux=taux, jour=dates[-1])


def _journal_egal_a_la_base(a: Acces, r: Releve, journal: list[dict[str, Any]]) -> None:
    """Le journal valorisé est celui de la base : ligne par ligne, cours figé compris."""
    nom = "Journal valorisé = la base (dates, quantités, prix, cours figé)"
    base = {
        x[0]: x
        for x in a.sql(
            "SELECT id, date_effet, type, lot_id, magasin_id, quantite, prix, devise, cours, "
            "contrepasse_id FROM mouvement"
        )
    }
    r.juger(
        nom,
        "nombre de lignes",
        len(base) == len(journal),
        f"écran {len(journal)}, base {len(base)}",
    )
    for x in journal:
        b = base.get(x["id"])
        if b is None:
            r.juger(nom, f"mouvement {x['id']}", False, "absent de la base")
            continue
        vu = (x["date"], x["type"], x["lot_id"], x["magasin_id"], x["devise"], x["contrepasse_id"])
        attendu = (b[1].isoformat(), b[2], b[3], b[4], b[7], b[9])
        juste = (
            vu == attendu
            and not ecart(x["quantite"], b[5], KG)
            and not ecart(x["prix"] or 0.0, b[6], 1e-9)
            and not ecart(x["cours"] or 0.0, b[8] or 0.0, 1e-9)
        )
        r.juger(nom, f"mouvement {x['id']}", juste, f"écran {x}, base {b}")


def _valeur_conservee(
    r: Releve, journal: list[dict[str, Any]], valo: dict[str, Any], d: date
) -> None:
    """Σ des valeurs du journal jusqu'au soir de `d` = valeur en magasin à `d`, par matière."""
    nom = "Valeur conservée : entrées − sorties = valeur en magasin, aux 13 dates"
    flux: dict[int, float] = defaultdict(float)
    jour = d.isoformat()
    for x in journal:
        if x["date"] <= jour:
            flux[x["matiere_id"]] += x["valeur_mad"] or 0.0
    ecran = {x["matiere_id"]: x for x in valo["lignes"]}
    for mid in sorted(set(flux) | set(ecran)):
        stock = (ecran.get(mid) or {}).get("valeur_magasin_mad", 0.0)
        r.juger(
            nom,
            f"matière {mid} au {d}",
            abs(flux.get(mid, 0.0) - stock) <= UN_MAD,
            f"entré − sorti {flux.get(mid, 0.0):.2f} MAD, valeur en magasin {stock:.2f} MAD",
        )


def _valorisation_se_tient(
    a: Acces, r: Releve, valo: dict[str, Any], d: date, taux: dict[str, float]
) -> None:
    """Valeur = CMUP × stock ; totaux = Σ ; écart au catalogue ; stock = journal."""
    nom = "Valorisation : valeur = CMUP × stock, totaux = Σ lignes, écart au catalogue"
    catalogue = {
        mid: (prix / densite if unite == "ml" and densite else prix, devise)
        for mid, prix, unite, densite, devise in a.sql(
            "SELECT id, prix, unite_prix, densite, devise FROM matiere"
        )
    }
    stock = dict(
        a.sql(
            "SELECT matiere_id, SUM(quantite) FROM mouvement WHERE date_effet <= %s GROUP BY 1",
            (d,),
        )
    )
    for x in valo["lignes"]:
        s = f"matière {x['matiere_id']} au {d}"
        r.comparer(
            nom, s + " (stock en magasin)", x["stock_magasin"], stock.get(x["matiere_id"], 0.0), KG
        )
        r.comparer(
            nom, s + " (magasin)", x["valeur_magasin_mad"], x["cmup_mad"] * x["stock_magasin"]
        )
        r.comparer(
            nom, s + " (métiers)", x["valeur_machine_mad"], x["cmup_mad"] * x["stock_machine"]
        )
        r.comparer(
            nom, s + " (total)", x["valeur_mad"], x["valeur_magasin_mad"] + x["valeur_machine_mad"]
        )
        prix, devise = catalogue[x["matiere_id"]]
        r.comparer(
            nom,
            s + " (écart au catalogue)",
            x["ecart_mad"],
            x["valeur_mad"] - x["stock"] * prix * cours_de(devise, None, taux),
        )
    for total, champ in (
        ("total_mad", "valeur_mad"),
        ("total_magasin_mad", "valeur_magasin_mad"),
        ("total_machine_mad", "valeur_machine_mad"),
        ("ecart_mad", "ecart_mad"),
    ):
        r.comparer(nom, f"{total} au {d}", valo[total], sum(x[champ] for x in valo["lignes"]))
    for total, champ in (
        ("total_kg", "stock"),
        ("total_kg_magasin", "stock_magasin"),
        ("total_kg_machine", "stock_machine"),
    ):
        r.comparer(nom, f"{total} au {d}", valo[total], sum(x[champ] for x in valo["lignes"]), KG)


def _cockpit(a: Acces, r: Releve, valo: dict[str, Any], d: date) -> None:
    """La valeur du Cockpit est le total de la Valorisation (E-06), à chaque date."""
    nom = "Deux pages, un chiffre : valeur du Cockpit = total de la Valorisation"
    c = a.get("/cockpit", date=d.isoformat())["stock"]
    r.comparer(nom, f"valeur au {d}", c["valeur_mad"], valo["total_mad"])
    r.comparer(
        nom, f"valeur des magasins au {d}", c["valeur_magasins_mad"], valo["total_magasin_mad"]
    )
    r.comparer(
        nom, f"valeur sur les métiers au {d}", c["valeur_machine_mad"], valo["total_machine_mad"]
    )
    r.comparer(nom, f"kilos sur les métiers au {d}", c["kg_machine"], valo["total_kg_machine"], KG)


def _cout_nul(a: Acces, r: Releve, journal: list[dict[str, Any]]) -> None:
    """Aucune écriture à coût nul, sauf pour une matière sans prix ou entrée à prix nul."""
    nom = "Aucune écriture à coût nul sans raison"
    avec_prix = {
        mid
        for (mid,) in a.sql(
            "SELECT id FROM matiere m WHERE prix > 0 AND NOT EXISTS (SELECT 1 FROM mouvement x "
            "WHERE x.matiere_id = m.id AND x.type IN ('OUVERTURE', 'RECEPTION') AND x.quantite > 0 "
            "AND x.prix = 0)"
        )
    }
    for x in journal:
        if x["matiere_id"] in avec_prix and x["type"] != "TRANSFERT":
            r.juger(
                nom,
                f"mouvement {x['id']} ({x['document_numero'] or x['document']})",
                abs(x["cout_mad"] or 0.0) > 1e-9,
                f"{x['quantite']:.3f} kg à 0 MAD",
            )


def _annulations(r: Releve, journal: list[dict[str, Any]]) -> None:
    """Une annulation rend exactement le coût de ce qu'elle annule."""
    nom = "Une annulation rend le coût de ce qu'elle annule"
    cout = {x["id"]: x["cout_mad"] or 0.0 for x in journal}
    for x in journal:
        original = x["contrepasse_id"]
        if original in cout and x["type"] != "TRANSFERT":
            r.juger(
                nom,
                f"mouvement {x['id']} (annule {original})",
                abs((x["cout_mad"] or 0.0) - cout[original]) <= 1e-6,
                f"annulation à {x['cout_mad']}, original à {cout[original]}",
            )


def _ordre_de_grandeur(a: Acces, r: Releve, valo: dict[str, Any], taux: dict[str, float]) -> None:
    """Second modèle : chaque lot qui reste, à son coût d'entrée ; rapport dans [0,5 ; 2]."""
    nom = "Ordre de grandeur : chaque lot à son coût d'entrée"
    cout_lot = cout_d_entree_des_lots(a, taux)
    # Une matière entrée à coût nul (voulu : V2) mêle des lots à 0 au coût moyen : le second
    # modèle ne dit plus rien de son ordre de grandeur.
    a_zero = {
        mid
        for (mid,) in a.sql(
            "SELECT DISTINCT matiere_id FROM mouvement WHERE type IN ('OUVERTURE', 'RECEPTION') "
            "AND quantite > 0 AND prix = 0"
        )
    }
    modele: dict[int, float] = defaultdict(float)
    inconnu: set[int] = set()
    for mid, lot, reste in a.sql(
        "SELECT l.matiere_id, s.lot_id, SUM(s.quantite) FROM solde s JOIN lot l ON l.id = s.lot_id "
        "GROUP BY 1, 2 HAVING SUM(s.quantite) > %s",
        (POUSSIERE,),
    ):
        if lot in cout_lot:
            modele[mid] += reste * cout_lot[lot]
        else:
            inconnu.add(mid)
    ecran = {x["matiere_id"]: x["valeur_magasin_mad"] for x in valo["lignes"]}
    for mid, valeur in sorted(modele.items()):
        if mid in inconnu or mid in a_zero:
            continue
        stock = ecran.get(mid, 0.0)
        rapport = stock / valeur if valeur else (1.0 if abs(stock) <= 100 else 0.0)
        juste = abs(stock - valeur) <= 100 or GRANDEUR[0] <= rapport <= GRANDEUR[1]
        r.juger(
            nom,
            f"matière {mid}",
            juste,
            f"valeur du stock {stock:.2f} MAD, lots à leur coût d'entrée {valeur:.2f} MAD",
        )


def _entrees_a_leur_cout(
    a: Acces, r: Releve, journal: list[dict[str, Any]], taux: dict[str, float]
) -> None:
    """Chaque achat (ouverture, réception) entre à son coût d'entrée : coût de revient de son
    dossier s'il en a un, sinon prix × cours figé (à défaut, cours du jour)."""
    nom = "Chaque entrée à son coût d'entrée (dossier, sinon prix × cours figé)"
    attendus = couts_d_entree(a, taux)
    for x in journal:
        if x["id"] in attendus:
            r.comparer(
                nom,
                f"mouvement {x['id']} ({x['document_numero'] or x['document']})",
                x["cout_mad"],
                attendus[x["id"]],
                MAD / 100,
            )
