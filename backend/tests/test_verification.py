"""La vérification indépendante des chiffres (lot V1, critère A5) fait ses preuves.

`essais/verification_chiffres.py` ne connaît PRO que par le SQL et l'API. Ici, il tourne sur
une petite usine d'essai (`fabriques.verification`) : sans faute, il ne trouve aucun écart ;
chaque faute connue (PLAN-DE-RECETTE § 6) injectée dans une réponse, dans le moteur ou dans la
base est vue par la famille qui la garde :

- CMUP × 1,1 dans la réponse de la Valorisation ;
- l'ancien moteur du coût moyen : G1 (annulation du jour rejouée trop tard), G2 (ré-entrée au
  catalogue), G3 (annulation au coût moyen du moment) ;
- une écriture SQL qui fait passer un lot sous zéro à une date passée ;
- une répartition de frais à la mauvaise clé ;
- un OTIF de fournisseur compté sur toutes les réceptions (et non sur les notées) ;
- un solde faussé.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from fabriques.pilotage import Usine, fixture_usine, jour  # noqa: F401
from fabriques.verification import AUJOURDHUI, AccesUsine, Faits, batir
from sqlalchemy import text

from gestion_mp_pro.calcul import importations, valorisation

ESSAIS = Path(__file__).resolve().parents[1] / "essais"
sys.path.insert(0, str(ESSAIS))
import verification_chiffres  # noqa: E402

SCRIPTS = sorted([ESSAIS / "verification_chiffres.py", *ESSAIS.glob("verif_*.py")])

CONSERVEE = "Valeur conservée : entrées − sorties = valeur en magasin, aux 13 dates"
DEUX_PAGES = "Deux pages, un chiffre : valeur du Cockpit = total de la Valorisation"
REJEU = "CMUP rejoué depuis le journal : coût de chaque écriture"
ANNULATION = "Une annulation rend le coût de ce qu'elle annule"
SOUS_ZERO = "Aucun lot sous zéro à une date passée"
REPARTITION = "Répartition des frais : chaque marchandise de dossier (clé du poste)"
NOTE = "Note de chaque fournisseur (moyennes des réceptions notées, retours, score)"
SOLDES = "Soldes égaux au journal, jamais négatifs"


class AccesFaux(AccesUsine):
    """L'accès dont certaines réponses sont faussées (`alterer(chemin, réponse)`)."""

    def __init__(self, usine: Usine, alterer: Callable[[str, Any], Any]) -> None:
        super().__init__(usine)
        self.alterer = alterer

    def get(self, chemin: str, **params: Any) -> Any:
        return self.alterer(chemin, super().get(chemin, **params))


def _verifier(acces: Any, dates: int = 2) -> Any:
    return verification_chiffres.verifier(acces, AUJOURDHUI, dates)


def test_le_script_n_importe_rien_de_pro() -> None:
    for fichier in SCRIPTS:
        arbre = ast.parse(fichier.read_text(encoding="utf-8"))
        modules = {a.name for n in ast.walk(arbre) if isinstance(n, ast.Import) for a in n.names}
        modules |= {n.module or "" for n in ast.walk(arbre) if isinstance(n, ast.ImportFrom)}
        assert not {m for m in modules if m.split(".")[0] == "gestion_mp_pro"}, fichier
    code = (
        "import sys; import verification_chiffres; "
        "assert not [m for m in sys.modules if m.startswith('gestion_mp_pro')]"
    )
    sortie = subprocess.run(  # noqa: S603
        [sys.executable, "-c", code], cwd=ESSAIS, capture_output=True, text=True, check=False
    )
    assert sortie.returncode == 0, sortie.stderr


def test_sans_faute_aucun_ecart(usine: Usine) -> None:
    batir(usine)
    r = _verifier(AccesUsine(usine), dates=13)
    assert r.nb_ecarts == 0, "\n".join(r.lignes())
    assert r.cas >= 150
    for nom in (CONSERVEE, DEUX_PAGES, REJEU, ANNULATION, SOUS_ZERO, REPARTITION, NOTE, SOLDES):
        assert r.famille(nom).cas > 0, (nom, "\n".join(r.lignes()))


def test_cmup_fois_1_1_dans_une_reponse(usine: Usine) -> None:
    batir(usine)
    champs = ("cmup_mad", "valeur_magasin_mad", "valeur_machine_mad", "valeur_mad")
    totaux = ("total_mad", "total_magasin_mad", "total_machine_mad")

    def gonfler(chemin: str, rendu: Any) -> Any:
        if chemin == "/valorisation":
            for x in rendu["lignes"]:
                x.update({c: x[c] * 1.1 for c in champs})
            rendu.update({t: rendu[t] * 1.1 for t in totaux})
        return rendu

    r = _verifier(AccesFaux(usine, gonfler))
    assert r.ecarts_de(CONSERVEE)
    assert r.ecarts_de(DEUX_PAGES)


def test_ancien_moteur_g1_annulation_rejouee_trop_tard(
    usine: Usine, monkeypatch: pytest.MonkeyPatch
) -> None:
    batir(usine)
    monkeypatch.setattr(valorisation, "_ordre", lambda m: (m.date, m.id or 0, 0, 0))
    assert _verifier(AccesUsine(usine)).ecarts_de(REJEU)


def test_ancien_moteur_g2_reentree_au_catalogue(
    usine: Usine, monkeypatch: pytest.MonkeyPatch
) -> None:
    batir(usine)

    def au_catalogue(self: Any, mouvement: Any, article: Any) -> float:
        return float(article.prix_kg * self._taux(article.devise))

    monkeypatch.setattr(valorisation._Rejeu, "cout_de_reentree", au_catalogue)
    assert _verifier(AccesUsine(usine)).ecarts_de(REJEU)


def test_ancien_moteur_g3_annulation_au_cout_moyen(
    usine: Usine, monkeypatch: pytest.MonkeyPatch
) -> None:
    batir(usine)
    origine = valorisation._Rejeu._cout

    def sans_annulation(self: Any, m: Any, article: Any, signee: float, moyen: float) -> float:
        if m.contrepasse_id is None:
            return float(origine(self, m, article, signee, moyen))
        if signee > 0:
            return float(self._cout_entrant(m, article, signee, moyen))
        return float(self._cout_sortant(m, moyen))

    monkeypatch.setattr(valorisation._Rejeu, "_cout", sans_annulation)
    r = _verifier(AccesUsine(usine))
    assert r.ecarts_de(ANNULATION)
    assert r.ecarts_de(REJEU)


def test_ecriture_sql_sous_zero(usine: Usine) -> None:
    faits: Faits = batir(usine)
    usine.s.execute(
        text(
            "INSERT INTO mouvement (date_effet, type, matiere_id, lot_id, magasin_id, quantite, "
            "document, auteur_id) VALUES (:jour, 'SORTIE', :m, :lot, :g, -5, 'reprise', :qui)"
        ),
        {
            "jour": jour(-11),
            "m": faits.matiere_a,
            "lot": faits.lot_a1,
            "g": usine.courant,
            "qui": usine.auteur,
        },
    )
    r = _verifier(AccesUsine(usine))
    assert any(f"lot {faits.lot_a1}" in e for e in r.ecarts_de(SOUS_ZERO))


def test_repartition_a_la_mauvaise_cle(usine: Usine, monkeypatch: pytest.MonkeyPatch) -> None:
    batir(usine)
    origine = importations._classer_charges

    def cle_inversee(dossier: Any, valeurs: Any) -> Any:
        directes, globales = origine(dossier, valeurs)
        faux: dict[tuple[str, str], float] = {}
        for (poste, cle), montant in globales.items():
            autre = (poste, "valeur" if cle == "poids" else "poids")
            faux[autre] = faux.get(autre, 0.0) + montant
        return directes, faux

    monkeypatch.setattr(importations, "_classer_charges", cle_inversee)
    assert _verifier(AccesUsine(usine)).ecarts_de(REPARTITION)


def test_otif_compte_sur_toutes_les_receptions(usine: Usine) -> None:
    batir(usine)

    def sur_toutes(chemin: str, rendu: Any) -> Any:
        if chemin == "/fournisseurs/performance":
            for f in rendu["lignes"]:
                siennes = [
                    x for x in rendu["receptions"] if x["fournisseur_id"] == f["fournisseur_id"]
                ]
                if siennes:
                    f["otif"] = sum(x["otif"] or 0 for x in siennes) / len(siennes)
        return rendu

    r = _verifier(AccesFaux(usine, sur_toutes))
    assert any("(otif)" in e for e in r.ecarts_de(NOTE))


def test_solde_fausse(usine: Usine) -> None:
    faits = batir(usine)
    usine.s.execute(
        text("UPDATE solde SET quantite = quantite + 5 WHERE lot_id = :lot"),
        {"lot": faits.lot_b1},
    )
    r = _verifier(AccesUsine(usine))
    assert any(f"lot {faits.lot_b1}" in e for e in r.ecarts_de(SOLDES))
