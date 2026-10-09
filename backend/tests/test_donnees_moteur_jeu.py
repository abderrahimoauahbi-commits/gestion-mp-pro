"""`charger_au` égal au moteur de Gestion MP sur un jeu figé (lot S4 ; LOTS S4, critère de fin).

Le jeu 01 de S3 (toutes les données réelles de l'année d'essai, 10 411 écritures, telles que le
chargeur de Gestion MP les a lues) est réécrit en base PRO (`fabriques/jeu_*.py`), relu par le
chargeur PRO, et :
1. les `Donnees` relues égalent celles du jeu, à l'arrondi des colonnes près (K1 : la base garde
   le gramme, le centime, le millionième) ;
2. le moteur PRO nourri par `charger_au` rend les sorties que le moteur de **Gestion MP** a
   rendues (fichier attendu de S3), à cette même tolérance près.
"""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Any

from fabriques.jeu_journal import batir_jeu
from fabriques.stock import s
from moteur import jeux_outils as jeux
from moteur.sorties_pro import sorties_du_moteur
from sqlalchemy.orm import Session

from gestion_mp_pro.services import donnees_moteur, horloge

__all__ = ["s"]

JEU = "01-tout-premier-jour"
TOLERANCE_ABSOLUE = 0.006
"""Un gramme et un demi-centime arrondis, cumulés sur quelques lignes (K1)."""
TOLERANCE_RELATIVE = 1e-6
TOLERANCE_DES_DOSSIERS = {
    "revient": 0.6, "revient_par_reception": 0.6, "tva_attendue": 0.1, "ecart_facture": 0.02,
    "controles": 0.15,
}  # fmt: skip
"""K1 sur les dossiers : la valeur en devise d'une marchandise est gardée au centime (Gestion
MP : 946 valeurs à plus de deux décimales), multipliée par le cours puis répartie avec les
frais ; l'écart reste de quelques centimes de dirham par ligne (au plus 0,55 MAD mesuré)."""


def proches(  # noqa: PLR0912 — un comparateur récursif
    a: Any, b: Any, chemin: str = "", sortie: list[str] | None = None, absolue: float = 0.0
) -> list[str]:
    """Les chemins où deux structures diffèrent au-delà de l'arrondi des colonnes."""
    sortie = [] if sortie is None else sortie
    absolue = absolue or TOLERANCE_ABSOLUE
    if len(sortie) >= 30:
        return sortie
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b), key=str):
            if k not in a or k not in b:
                sortie.append(f"{chemin}/{k} : d'un seul côté")
            else:
                proches(a[k], b[k], f"{chemin}/{k}", sortie, absolue)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            sortie.append(f"{chemin} : {len(a)} éléments ≠ {len(b)}")
        for i, (x, y) in enumerate(zip(a, b, strict=False)):
            proches(x, y, f"{chemin}/{i}", sortie, absolue)
    elif isinstance(a, int | float) and isinstance(b, int | float) and not isinstance(a, bool):
        if abs(a - b) > max(absolue, TOLERANCE_RELATIVE * max(abs(a), abs(b))):
            sortie.append(f"{chemin} : jeu {a!r} ≠ PRO {b!r}")
    elif a != b:
        sortie.append(f"{chemin} : jeu {a!r} ≠ PRO {b!r}")
    return sortie


def _comme_la_base(jeu: dict[str, Any]) -> dict[str, Any]:
    """Ce que la base PRO ne peut pas garder tel quel : pas de prix sur une sortie, un retour des
    machines ou un transfert (`ck_mouvement_prix_entree`) ; un ordre validé a sa date de validation
    (midi, s'il n'en avait pas) ; l'ordre des recettes et des lignes d'une version de recette
    n'est pas un ordre métier (comparé trié)."""
    for m in jeu["mouvements"]:
        if m["type"] not in ("STOCK_INITIAL", "ENTREE_RECEPTION", "RETOUR_FOURNISSEUR",
                             "AJUSTEMENT_INVENTAIRE"):  # fmt: skip
            m["prix_unite"] = m["total_devise"] = 0.0
    for a in [*jeu["articles"], *jeu["_articles"].values()]:
        if not a["contenance_commande"]:
            a["unite_commande"] = ""  # sans contenance, l'unité ne sert pas (`conditionnement`)
    _une_devise_par_reception(jeu)
    for o in jeu["ordres"]:
        if o["valide_le"] is None:
            o["valide_le"] = datetime.combine(date.fromisoformat(o["date"]), time(12)).isoformat()
    return _trier(jeu)


def _une_devise_par_reception(jeu: dict[str, Any]) -> None:
    """I35 : une devise par réception. Un camion de Gestion MP payé en deux devises (LOMAT :
    USD et EUR) garde en PRO la devise de sa première ligne payée : ses prix payés la prennent
    (le coût des entrées, lui, suit le journal et ne change pas)."""
    prix = {(p["date_bc"], p["reference"], p["numero_bc"], round(p["quantite"], 3)): p
            for p in jeu["historique_prix"]}  # fmt: skip
    for r in jeu["receptions"]:
        payes = [
            prix[cle] for ln in r["lignes"]
            if (cle := (r["date_reception"], ln["reference"], ln["numero_bc"] or r["numero_bc"],
                        round(ln["quantite_pesee"], 3))) in prix
        ]  # fmt: skip
        for p in payes:
            p["devise"] = payes[0]["devise"]


def _trier(d: dict[str, Any]) -> dict[str, Any]:
    d["recettes"] = sorted(d["recettes"], key=str)
    for r in d["receptions"]:
        if r["statut"] != "Validée":
            r["numero"] = "(brouillon)"  # un brouillon n'a pas de numéro en PRO (M65)
    for versions in d["versions_recette"].values():
        for v in versions:
            v["lignes"] = sorted(v["lignes"], key=str)
    return d


def test_le_chargeur_relit_un_jeu_reel_et_charger_au_rend_les_sorties_de_gestion_mp(
    s: Session,
) -> None:
    entete, complet = jeux.relire_jeu(JEU)
    jour, aujourdhui = (date.fromisoformat(entete[k]) for k in ("jour", "aujourdhui"))
    batir_jeu(s, complet)
    donnees_moteur.invalider()
    with horloge.figee(aujourdhui):
        lu = donnees_moteur.charger(s)
        ecarts = proches(_comme_la_base(jeux.propre(complet)), _trier(jeux.propre(lu)))
        assert ecarts == []
        obtenu = jeux.comme_gestion_mp(jeux.propre(sorties_du_moteur(lu, jour, aujourdhui)))
    attendu = jeux.attendu(JEU)["sorties"]
    for sorties in (attendu, obtenu):
        sorties["controles"] = {x["code"]: x for x in sorties["controles"]}
        # Ordre des recettes : celui de la base de Gestion MP (sans ORDER BY), pas un ordre métier.
        sorties["nomenclature"] = sorted(sorties["nomenclature"], key=str)
    differences = {
        section: e
        for section in sorted(attendu)
        if (e := proches(attendu[section], obtenu[section],
                         absolue=TOLERANCE_DES_DOSSIERS.get(section, 0.0)))
    }  # fmt: skip
    assert differences == {}


def test_le_comparateur_voit_un_ecart_au_dela_de_l_arrondi() -> None:
    """La tolérance est celle de l'arrondi des colonnes, pas davantage."""
    assert proches({"x": 100.0}, {"x": 100.005}) == []
    assert proches({"x": 100.0}, {"x": 100.01}) != []
    assert proches([1, 2], [1]) != []
    assert proches({"a": "b"}, {"a": "c"}) != []
    assert proches({"x": 1.0}, {"x": 1.5}, absolue=0.6) == []
