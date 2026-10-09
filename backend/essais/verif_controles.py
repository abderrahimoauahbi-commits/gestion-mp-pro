"""Les contrôles C01–C38 recomptés là où c'est simple, en SQL (lot V1).

Chaque nombre d'anomalies de l'écran Contrôles (route 212, aujourd'hui) est comparé à un
recomptage dans la base, avec la règle de la documentation (CONTROLES § 3) :

- C02 sortie sans ordre et C04 mouvement sans auteur (journal à la date ; un transfert, ses
  deux jambes, compte une fois) ; C05 matière sans fournisseur ; C07
  matière jamais utilisée ; C12 solde ≠ journal ; C14 mouvement daté du futur ; C19 fournisseur
  à plusieurs devises au catalogue ; C27 lot dont il est sorti plus qu'il n'est entré ; C28
  dossier ouvert arrivé depuis plus de 30 jours sans frais hors TVA ; C31 ordre servi à
  plusieurs dates ; C34 dossier avec des frais mais sans marchandise ; C37 lot sous zéro un
  soir passé ;
- les contrôles garantis par la base (C09, C10, C11, C16, C21, C26) n'ont aucune anomalie ;
- la synthèse : total, conformes, anomalies, score = conformes ÷ total.
C01 est jugé avec les recettes (`verif_production`), C29 et C36 avec les dossiers.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from verif_socle import RELATIF, Acces, Releve, ecart
from verif_stock import sous_zero_passe

NOM = "Contrôles C01–C38 recomptés en SQL (nombre d'anomalies)"
GARANTIS = ("C09", "C10", "C11", "C16", "C21", "C26")
UNE_PAR_TRANSFERT = (
    "count(DISTINCT CASE WHEN type = 'TRANSFERT' THEN -COALESCE(paire_id, id) ELSE id END)"
)
"""Les deux jambes d'un transfert font un seul mouvement du moteur (CALCULS A § 4.7)."""


def _requetes() -> dict[str, str]:
    """Le recomptage SQL de chaque contrôle simple (une valeur : le nombre d'anomalies)."""
    return {
        "C02": "SELECT count(*) FROM mouvement WHERE type = 'SORTIE' AND ordre_id IS NULL "
        "AND date_effet <= %(jour)s",
        "C04": f"SELECT {UNE_PAR_TRANSFERT} FROM mouvement WHERE auteur_id IS NULL "  # noqa: S608
        "AND date_effet <= %(jour)s",
        "C05": "SELECT count(*) FROM matiere WHERE fournisseur_id IS NULL",
        "C07": "SELECT count(*) FROM matiere m WHERE NOT EXISTS (SELECT 1 FROM recette r WHERE "
        "r.matiere_id = m.id) AND NOT EXISTS (SELECT 1 FROM mouvement x WHERE x.matiere_id = m.id "
        "AND x.date_effet <= %(jour)s)",
        "C12": "SELECT count(*) FROM solde s FULL JOIN (SELECT lot_id, magasin_id, SUM(quantite) "
        "AS q FROM mouvement GROUP BY 1, 2) j ON j.lot_id = s.lot_id AND j.magasin_id = "
        "s.magasin_id WHERE abs(COALESCE(s.quantite, 0) - COALESCE(j.q, 0)) > 0.0005",
        "C14": f"SELECT {UNE_PAR_TRANSFERT} FROM mouvement WHERE date_effet > %(jour)s",  # noqa: S608
        "C19": "SELECT count(*) FROM (SELECT fournisseur_id FROM matiere WHERE fournisseur_id IS "
        "NOT NULL GROUP BY 1 HAVING count(DISTINCT devise) > 1) x",
        "C27": "SELECT count(*) FROM (SELECT lot_id FROM mouvement GROUP BY 1 "
        "HAVING SUM(quantite) < -1e-9) x",
        "C28": "SELECT count(*) FROM dossier d WHERE d.statut = 'ouvert' AND d.date_arrivee IS "
        "NOT NULL AND %(jour)s - d.date_arrivee > 30 AND EXISTS (SELECT 1 FROM dossier_ligne l "
        "WHERE l.dossier_id = d.id) AND NOT EXISTS (SELECT 1 FROM dossier_frais f JOIN "
        "poste_frais p ON p.id = f.poste_id WHERE f.dossier_id = d.id AND NOT p.recuperable)",
        "C31": "SELECT count(*) FROM (SELECT ordre_id FROM mouvement WHERE type = 'SORTIE' AND "
        "ordre_id IS NOT NULL AND quantite < 0 GROUP BY 1 HAVING count(DISTINCT date_effet) > 1) x",
        "C34": "SELECT count(*) FROM dossier d WHERE d.statut <> 'annule' AND EXISTS (SELECT 1 "
        "FROM dossier_frais f WHERE f.dossier_id = d.id) AND NOT EXISTS (SELECT 1 FROM "
        "dossier_ligne l WHERE l.dossier_id = d.id)",
    }


def verifier(a: Acces, r: Releve, dates: list[date]) -> None:
    """Le nombre d'anomalies de chaque contrôle simple, recompté ; la synthèse."""
    rendu = a.get("/controles")
    controles: dict[str, dict[str, Any]] = {c["code"]: c for c in rendu["controles"]}
    jour = dates[-1]
    for code, requete in _requetes().items():
        ((n,),) = a.sql(requete, {"jour": jour})
        _juger(r, controles, code, int(n))
    _juger(r, controles, "C37", len(sous_zero_passe(a)))
    for code in GARANTIS:
        _juger(r, controles, code, 0)
    s = rendu["synthese"]
    liste = rendu["controles"]
    r.juger(
        NOM,
        "synthèse : total",
        s["total"] + s["garantis"] == len(liste) or s["total"] == len(liste),
        f"total {s['total']}, garantis {s['garantis']}, {len(liste)}",
    )
    r.juger(
        NOM,
        "synthèse : anomalies",
        s["anomalies"] == sum(1 for c in liste if c["anomalies"] and not c["garanti"]),
        f"écran {s['anomalies']}",
    )
    if s["total"]:
        r.juger(
            NOM, "synthèse : score", not ecart(s["score"], s["conformes"] / s["total"], RELATIF)
        )


def _juger(r: Releve, controles: dict[str, dict[str, Any]], code: str, attendu: int) -> None:
    """Un contrôle : son nombre d'anomalies contre le recomptage."""
    c = controles.get(code)
    if not r.juger(NOM, code, c is not None, "absent de l'écran Contrôles"):
        return
    assert c is not None
    r.juger(
        NOM,
        code,
        c["anomalies"] == attendu,
        f"écran {c['anomalies']} anomalie(s), recompté {attendu}",
    )
