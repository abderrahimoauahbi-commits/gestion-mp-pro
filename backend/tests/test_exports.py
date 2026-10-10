"""Classeurs Excel (lot D9) : conventions communes (`exports/classeur.py`) et export du journal
des actions (route 52) avec les filtres de l'écran.
"""

from __future__ import annotations

import itertools
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

import pytest
from fabrique import *  # noqa: F403
from fabriques.documents import classeur as relire
from fastapi.testclient import TestClient
from sqlalchemy import insert

from gestion_mp_pro.db import fabrique
from gestion_mp_pro.exports.classeur import (
    FORMATS,
    TYPE_XLSX,
    Colonne,
    Feuille,
    cellule,
    classeur,
    exporte_le,
    filtres,
    nom_de_fichier,
    titre,
)
from gestion_mp_pro.modeles import Journal, Utilisateur
from gestion_mp_pro.services import horloge

JOUR = date(2026, 10, 8)
_RANG = itertools.count(1)


class Couleur(StrEnum):
    """Une énumération écrite par sa valeur."""

    rouge = "rouge"


LIGNES = [
    {
        "quand": datetime(2026, 10, 8, 9, 30, 15, 123, tzinfo=UTC),
        "jour": date(2026, 10, 1),
        "kg": Decimal("1234.567"),
        "texte": '=HYPERLINK("http://x")',
        "prix": Decimal("2.55"),
        "actif": True,
        "couleur": Couleur.rouge,
    },
    {
        "quand": None,
        "jour": None,
        "kg": 0,
        "texte": "+33 6\x07 12",
        "prix": None,
        "actif": False,
        "couleur": "-moins",
    },
]
COLONNES = (
    Colonne("Quand", lambda x: x["quand"], "horodatage"),
    Colonne("Jour", lambda x: x["jour"], "date"),
    Colonne("Quantité (kg)", lambda x: x["kg"], "kg"),
    Colonne("Remarque", lambda x: x["texte"]),
    Colonne("Prix / kg", lambda x: x["prix"], "prix", monetaire=True),
    Colonne("Actif", lambda x: x["actif"]),
    Colonne("Couleur", lambda x: x["couleur"]),
)


def _feuille(voit_prix: bool = True, entete: tuple[str, ...] = ()) -> Any:
    contenu = classeur([Feuille("Essai", COLONNES, LIGNES, entete)], voit_prix)
    return relire(contenu)["Essai"]


def test_les_conventions_communes() -> None:
    """En-tête gras sur fond gris, figé et filtrable ; formats de chaque grandeur ; largeurs."""
    ws = _feuille()
    entete = [c.value for c in ws[1]]
    assert entete == [c.titre for c in COLONNES]
    assert all(c.font.bold and c.fill.fgColor.rgb.endswith("E8ECF3") for c in ws[1])
    assert ws.freeze_panes == "B2" and ws.auto_filter.ref == "A1:G3"
    assert ws["A2"].number_format == FORMATS["horodatage"] == "DD/MM/YYYY HH:MM"
    assert ws["B2"].number_format == "DD/MM/YYYY" and ws["C2"].number_format == "#,##0.##"
    assert ws["C2"].value == 1234.567 and ws["C3"].value == 0  # la cellule reste numérique
    assert ws["E2"].number_format == "#,##0.00##" and ws["E2"].value == 2.55
    assert ws.column_dimensions["A"].width == 17 and ws.column_dimensions["D"].width >= 10
    assert (ws["F2"].value, ws["F3"].value, ws["G2"].value) == ("oui", None, "rouge")


def test_de_vraies_dates_a_l_heure_de_l_usine() -> None:
    """Une date est une date Excel (triable), un instant est mis à l'heure de l'usine, sans
    fuseau ni microsecondes ; une case vide reste vide."""
    ws = _feuille()
    assert ws["B2"].is_date and ws["B2"].value == datetime(2026, 10, 1)  # noqa: DTZ001
    attendu = LIGNES[0]["quand"].astimezone(horloge.FUSEAU).replace(tzinfo=None, microsecond=0)
    assert ws["A2"].is_date and ws["A2"].value == attendu
    assert ws["A3"].value is None and ws["B3"].value is None


def test_un_texte_ne_s_execute_jamais() -> None:
    """`=`, `+`, `-`, `@` restent du texte ; les caractères de contrôle sont retirés."""
    ws = _feuille()
    assert ws["D2"].data_type == "s" and ws["D2"].value == '=HYPERLINK("http://x")'
    assert ws["D3"].data_type == "s" and ws["D3"].value == "+33 6 12"
    assert ws["G3"].data_type == "s" and ws["G3"].value == "-moins"
    assert cellule("@SOMME") == "@SOMME"
    ws2 = relire(classeur([Feuille("X", [Colonne("A", lambda x: x)], ["@SOMME(A1)"])], True))
    assert ws2["X"]["A2"].data_type == "s"


def test_aucune_colonne_de_prix_pour_qui_ne_les_voit_pas() -> None:
    """Barrière 4 : la colonne monétaire disparaît ; titre monétaire non déclaré : une faute."""
    ws = _feuille(voit_prix=False)
    entete = [c.value for c in ws[1]]
    assert "Prix / kg" not in entete and len(entete) == len(COLONNES) - 1
    assert all(2.55 not in ligne for ligne in ws.iter_rows(values_only=True))
    oublie = [Colonne("Valeur (MAD)", lambda x: 1)]
    with pytest.raises(ValueError, match="Valeur"):
        classeur([Feuille("X", oublie, [1])], voit_prix=False)
    assert classeur([Feuille("X", oublie, [1])], voit_prix=True)[:2] == b"PK"


def test_titre_filtres_et_onglets() -> None:
    """Titre daté, filtres posés (les vides ne s'écrivent pas) au-dessus de l'en-tête ; noms
    d'onglets permis et uniques ; une feuille vide n'a pas de filtre."""
    lignes = (titre("Essai", JOUR), filtres([("par", "Karim"), ("action", ""), ("du", JOUR)]))
    ws = _feuille(entete=lignes)
    assert ws["A1"].value == "Essai au 08/10/2026" and ws["A1"].font.bold
    assert ws["A2"].value == "Filtres — par : Karim · du : 08/10/2026"
    assert ws["A3"].value is None and ws["A4"].value == "Quand"
    assert ws.freeze_panes == "B5" and ws.auto_filter.ref == "A4:G6"
    assert filtres([("par", None), ("mots", "")]) == ""
    assert exporte_le("Matières", JOUR) == "Matières — exporté le 08/10/2026"
    wb = relire(
        classeur([Feuille("Stock: a/b", COLONNES, []), Feuille("stock? a*b", COLONNES, [])], True)
    )
    assert wb.sheetnames == ["Stock  a b", "stock  a b (2)"]
    assert wb.worksheets[0].auto_filter.ref is None
    assert nom_de_fichier("journal des actions/é", JOUR) == "journal-des-actions-2026-10-08.xlsx"


# ── Route 52 : le journal des actions ─────────────────────────────────────────────────────────


def _ecrire(action: str, n: int, **champs: Any) -> list[int]:
    """`n` lignes du journal (les plus anciennes d'abord), écrites telles qu'en base."""
    with fabrique()() as s, s.begin():
        return [
            s.execute(
                insert(Journal)
                .values(action=action, objet="matiere", objet_id=1000 + i, detail=f"n{i}", **champs)
                .returning(Journal.id)
            ).scalar_one()
            for i in range(n)
        ]


def _lignes(contenu: bytes) -> tuple[list[object], list[tuple[object, ...]]]:
    ws = relire(contenu)["Journal des actions"]
    rangees = list(ws.iter_rows(values_only=True))
    debut = next(i for i, r in enumerate(rangees) if r[0] == "Quand")
    return [r[0] for r in rangees[:debut]], rangees[debut:]


def test_le_journal_s_exporte_avec_les_filtres_de_l_ecran(
    direction: TestClient, achats: TestClient, alimentation: TestClient, anonyme: TestClient
) -> None:
    """Hérité : test_direction::test_le_journal_des_actions_se_filtre_et_s_exporte (export) —
    les lignes du classeur sont celles de l'écran (route 49), dans le même ordre, mêmes filtres ;
    les filtres sont écrits au-dessus ; achats, alimentation 403 ; anonyme 401."""
    action = f"essai export {next(_RANG)}"
    with fabrique()() as s:
        karim = s.query(Utilisateur).filter_by(identifiant="achats").one()
    _ecrire(action, 3, utilisateur_id=karim.id, utilisateur_nom=karim.nom, role="achats")
    _ecrire(action, 2, utilisateur_nom="Système")
    filtre = {"action": action, "utilisateur": karim.id, "du": "2026-10-01", "q": "n"}
    ecran = direction.get("/api/journal", params=filtre).json()["elements"]
    r = direction.get("/api/export/journal", params=filtre)
    assert r.status_code == 200 and r.headers["content-type"] == TYPE_XLSX
    assert r.headers["content-disposition"] == (
        'attachment; filename="journal-des-actions-2026-10-08.xlsx"'
    )
    titres, (entete, *lignes) = _lignes(r.content)
    assert titres[:2] == [
        "Journal des actions au 08/10/2026",
        f"Filtres — par : {karim.nom} · action : {action} · du : 01/10/2026 · mots : n",
    ]
    assert entete[:8] == ("Quand", "Par", "Rôle", "Action", "Sur", "Fiche n°", "Numéro", "Détail")
    assert [(x[5], x[7]) for x in lignes] == [(e["objet_id"], e["detail"]) for e in ecran]
    assert len(lignes) == 3 and {x[1] for x in lignes} == {karim.nom}
    assert lignes[0][2] == "Responsable achats" and isinstance(lignes[0][0], datetime)
    tout = _lignes(direction.get("/api/export/journal", params={"action": action}).content)[1]
    assert len(tout) == 6 and tout[1][1] == "Système"
    vide = _lignes(direction.get("/api/export/journal", params={"au": "2001-01-01"}).content)
    assert vide[1][1:] == []
    assert achats.get("/api/export/journal").status_code == 403
    assert alimentation.get("/api/export/journal").status_code == 403
    assert anonyme.get("/api/export/journal").status_code == 401
    refus = direction.get("/api/export/journal", params={"du": "2026-10-08", "au": "2026-10-01"})
    assert (refus.status_code, refus.json()["code"]) == (422, "date_invalide")


def test_l_administrateur_n_y_lit_aucun_prix(
    direction: TestClient, administrateur: TestClient
) -> None:
    """Les changements (avant / après) sont lisibles ; l'administrateur n'y lit pas les prix
    (comme dans la réponse JSON du journal, décision S2 n° 9)."""
    action = f"essai prix {next(_RANG)}"
    _ecrire(action, 1, avant={"prix": 2.5, "statut": "envoyée"}, apres={"prix": 3.25})
    vu_d = _lignes(direction.get("/api/export/journal", params={"action": action}).content)[1]
    vu_t = _lignes(administrateur.get("/api/export/journal", params={"action": action}).content)[1]
    assert vu_d[1][8:] == ("prix : 2,5 · statut : envoyée", "prix : 3,25")
    assert vu_t[1][8:] == ("prix : — · statut : envoyée", "prix : —")
