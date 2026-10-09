"""Parité de calcul PRO = Gestion MP sur l'année d'essai (PLAN-DE-RECETTE-PRO § 7, critère A6).

    .venv/bin/python essais/parite_gestion_mp.py [--sortie FICHIER] [--passes statique,api,…]
                                                 [--garder]

1. **Les mêmes données** (§ 7.1) : `gestion_mp_comparaison` copiée (lecture seule), reprise
   dans une base PRO neuve (R1) ; empreintes de `gestion_mp` et de `gestion_mp_comparaison`
   relevées avant et après ; le rapport commence par le contrôle d'import de la reprise.
2. **Statique** (§ 7.2) : les `Donnees` des deux chargeurs comparées (chaque différence est une
   traduction déclarée, reconnue par sa règle) ; les deux moteurs à 19 dates (13 + 6) ; le
   moteur PRO doit rendre **exactement** ce que le moteur de Gestion MP rend sur les mêmes
   données ; chaque écart de PRO contre Gestion MP est expliqué par la première traduction
   dont le recalcul par Gestion MP redonne la valeur de PRO.
3. **API** (§ 7.3) : les deux serveurs lancés (ports > 8100) ; 155 paires de routes (pilotage à
   19 dates, bilans de 13 mois, documents) traduites champ à champ ; écarts expliqués par le
   rejeu des routes de Gestion MP sur les données traduites, la chaîne en base, K9, puis les
   règles directes ; écrans de l'alimentation.
4. **Dynamique** (§ 7.4, réduite) : une semaine d'usine jouée geste par geste dans les deux.
5. **K7** : la correction « fil monté à toute date » prouvée sur une copie montée.
6. **Réciproque** (§ 7.7) : un champ de Gestion MP absent de PRO, ni renommé ni déplacé avec sa
   raison, est un écart à corriger.

Code de sortie 0 seulement si « à corriger : 0 ». Les bases d'essai sont supprimées à la fin
(sauf `--garder`) ; aucun serveur ne reste ouvert.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime
from pathlib import Path

ESSAIS = Path(__file__).resolve().parent
sys.path.insert(0, str(ESSAIS))

import gestion_mp_calcul as calcul  # noqa: E402
import parite_api_alimentation as alim  # noqa: E402
import parite_api_passe as api  # noqa: E402
import parite_bases as pb  # noqa: E402
import parite_donnees as pd  # noqa: E402
import parite_dynamique as dyn  # noqa: E402
import parite_k7 as k7  # noqa: E402
import parite_rapport as rp  # noqa: E402
import parite_serveurs as srv  # noqa: E402
import parite_statique as st  # noqa: E402

PASSES = ("statique", "api", "dynamique", "k7")
MOIS = [f"{a}-{m:02d}" for a, m in [(2025, 10), (2025, 11), (2025, 12)]] + [
    f"2026-{m:02d}" for m in range(1, 11)
]


def entete(r: rp.Rapport, prep: pb.Preparation, bases: pb.Bases) -> None:
    """Versions, bases, empreintes, et le contrôle d'import de la reprise (§ 7.1)."""
    pro = subprocess.run(["git", "-C", str(ESSAIS), "rev-parse", "--short", "HEAD"],  # noqa: S607, S603
                         capture_output=True, text=True, check=False).stdout.strip()  # fmt: skip
    r("PARITÉ DE CALCUL GESTION MP PRO = GESTION MP — ANNÉE D'ESSAI (critère A6)")
    r(f"le {datetime.now().astimezone():%Y-%m-%d %H:%M} · Gestion MP {srv.pb_commit()} · "
      f"PRO {pro}")  # fmt: skip
    r(f"source : {pb.SOURCE} (copie : {bases.copie.rsplit('/', 1)[-1]}) → PRO "
      f"{bases.pro.rsplit('/', 1)[-1]}")  # fmt: skip
    for nom in prep.avant:
        egal = "identique" if prep.avant[nom] == prep.apres[nom] else "CHANGÉE"
        r(f"empreinte {nom} : {prep.avant[nom][:16]}… avant, après : {egal}")
    if not prep.source_intacte:
        r.a_corriger += 1
    r.titre("Contrôle d'import (reprise R1)")
    for ligne in prep.rapport.splitlines():
        r(f"  {ligne}")


def statique(r: rp.Rapport, bases: pb.Bases, dossier: Path) -> dict[str, Path]:
    """Données comparées, chaîne des traductions, moteurs aux 19 dates, K7 des services."""
    d0 = st.donnees_gestion_mp(bases.copie, dossier)["donnees"]
    complet = st.donnees_pro(bases.pro)
    dpro = pd.sans_index(json.loads(calcul.texte_json(complet)))
    ecarts = pd.ecarts(d0, dpro, pd.lire_contexte(bases.copie))
    chaine = pd.chaine(d0, ecarts)
    jeux = st.ecrire_jeux(dossier, d0, chaine)
    r.titre("Données des deux moteurs (chargeur de PRO contre dépôt de Gestion MP)")
    for classe, motifs in pd.resume(ecarts).items():
        r(f"  {classe:<10} " + ", ".join(f"{m} : {n}" for m, n in sorted(motifs.items())))
    if chaine[-1][1] != dpro:
        r("  LA CHAÎNE DES TRADUCTIONS NE REDONNE PAS LES DONNÉES DE PRO")
        r.a_corriger += 1
    r.a_corriger += sum(1 for e in ecarts if e.classe is None)
    st.calculer_gestion_mp(jeux, dossier, st.DATES)
    jours = []
    for j in st.DATES:
        res = st.comparer_jour(dossier, complet, j, [c for c, _ in chaine])
        st.verifier_k7(bases.pro, complet, res)
        jours.append(res)
    _statique_rapport(r, jours)
    return {p.stem: p for p in jeux}


def _statique_rapport(r: rp.Rapport, jours: list[st.Jour]) -> None:
    r.titre(f"Statique : les deux moteurs à {len(jours)} dates")
    r(f"  dates : {', '.join(j.jour for j in jours)}")
    moteur = [(j.jour, "/".join(c), g, p) for j in jours for c, g, p in j.moteur]
    r(f"  moteur PRO = moteur de Gestion MP sur les mêmes données (égalité exacte) : "
      f"{len(moteur)} écart(s)")  # fmt: skip
    r.a_corriger += len(moteur)
    rp.detail_a_corriger(r, moteur)
    r(f"  codes du stock de PRO ramenés aux libellés de Gestion MP (forme RESTES3) : "
      f"{sum(j.codes for j in jours)} valeurs")  # fmt: skip
    comparees: Counter[str] = Counter()
    for j in jours:
        comparees.update(j.comparees)
    ecarts = [(e.chemin[0], e.classe, e.gmp, e.pro) for j in jours for e in j.ecarts]
    rp.tableau(r, "  PRO contre Gestion MP", ecarts, dict(comparees))
    rp.detail_a_corriger(r, [(e.chemin[0], "/".join(e.chemin[1:]), e.gmp, e.pro)
                             for j in jours for e in j.ecarts if e.classe is None])  # fmt: skip
    vus = sum(len(j.k7_vus) for j in jours)
    attendus = sum(j.k7_attendus for j in jours)
    r(f"  K7 (services de PRO, fil monté du soir, contre le moteur seul) : {attendus} fil(s) "
      f"monté(s) dans l'année d'essai, {vus} écart(s) ; attendu : 0 et 0")  # fmt: skip
    r.a_corriger += vus if attendus == 0 else 0


def passe_api(r: rp.Rapport, bases: pb.Bases, dossier: Path, jeux: dict[str, Path]) -> None:
    """Les deux serveurs, les routes, l'alimentation ; arrêtés en sortie."""
    with srv.demarrer(bases, dossier) as s:
        res = api.passe(s, bases, jeux, dossier / "api", list(st.DATES), MOIS)
        a = alim.passe(s, res.resultats)
    r.titre(f"Par l'API : {len(res.resultats)} paires de routes (direction)")
    r(f"  rejeu des routes de Gestion MP sur ses données (D0) = réponses du serveur : "
      f"{'oui' if not res.infideles else res.infideles}")  # fmt: skip
    r.a_corriger += len(res.infideles)
    r("  chaîne en base (ce que chaque traduction a changé dans la copie de Gestion MP) :")
    for classe, comptes in res.comptes.items():
        r(f"    {classe:<4} " + ", ".join(f"{k} {n}" for k, n in comptes.items()))
    _routes(r, res.resultats)
    r.titre("Par l'API : écrans de l'alimentation")
    r(f"  prix ou montants vus chez Gestion MP : {len(a.prix_gestion_mp)}, chez PRO : "
      f"{len(a.prix_pro)} ; réglages et cours (K6) : {a.k6}")  # fmt: skip
    r.a_corriger += len(a.prix_gestion_mp) + len(a.prix_pro)
    _routes(r, a.resultats)


def _groupe(nom: str) -> str:
    return nom.split(" (", maxsplit=1)[0].split(" 20", maxsplit=1)[0]


def _routes(r: rp.Rapport, resultats: list[api.Resultat]) -> None:
    comparees: Counter[str] = Counter()
    for x in resultats:
        comparees[_groupe(x.route)] += x.comparees
    ecarts = [(_groupe(x.route), e.classe, e.gmp, e.pro) for x in resultats for e in x.ecarts]
    rp.tableau(r, "  routes", ecarts, dict(comparees))
    rp.detail_a_corriger(r, [(f"{x.route} {e.cle}", e.champ, e.gmp, e.pro)
                             for x in resultats for e in x.ecarts if e.classe is None])  # fmt: skip
    traduites: Counter[str] = Counter()
    deplaces: dict[str, str] = {}
    ajoutes: set[str] = set()
    for x in resultats:
        traduites.update(x.traduites)
        deplaces |= {
            f"{_groupe(c.split('.')[0])}.{c.split('.', 1)[1]}": v for c, v in x.deplaces.items()
        }
        ajoutes |= x.ajoutes
    r(f"  valeurs traduites (formes déclarées) : {sum(traduites.values())} "
      f"({', '.join(f'{k} {n}' for k, n in traduites.most_common(12))}…)")  # fmt: skip
    r(f"  champs ajoutés par PRO (excusés) : {len(ajoutes)}")
    r(f"  réciproque — champs de Gestion MP rendus ailleurs par PRO ({len(deplaces)}) :")
    for champ, raison in sorted(deplaces.items()):
        r(f"    {champ} : {raison}")


def passe_dynamique(r: rp.Rapport, bases: pb.Bases, dossier: Path) -> None:
    """Les gestes, sur des copies fraîches des deux bases."""
    d = pb.Bases(prefixe=f"{bases.prefixe}dyn")
    try:
        pb.copier(bases.copie.rsplit("/", 1)[-1], d.copie)
        pb.copier(bases.pro.rsplit("/", 1)[-1], d.pro)
        with srv.demarrer(d, dossier) as s:
            j = dyn.passe(s)
    finally:
        pb.nettoyer(d)
    r.titre(f"Dynamique : {len(j.gestes)} gestes joués dans les deux logiciels")
    for g in j.gestes:
        numero = (g.reponse_gmp or {}).get("numero") if isinstance(g.reponse_gmp, dict) else ""
        r(f"  {g.nom:<48} Gestion MP {g.statut_gmp} · PRO {g.statut_pro}"
          + (f" · n° {numero}" if numero else ""))  # fmt: skip
    comparees = {x.route: x.comparees for x in j.resultats}
    rp.tableau(r, "  ce que chaque geste a fait", [(x.route, e.classe, e.gmp, e.pro)
               for x in j.resultats for e in x.ecarts], comparees)  # fmt: skip
    rp.detail_a_corriger(r, [(f"{x.route} {e.cle}", e.champ, e.gmp, e.pro)
                             for x in j.resultats for e in x.ecarts
                             if e.classe is None])  # fmt: skip


def passe_k7(r: rp.Rapport, bases: pb.Bases, dossier: Path) -> None:
    """La preuve de K7 sur une copie montée."""
    p = k7.prouver(bases, dossier, list(st.FINS_DE_MOIS))
    r.titre("K7 : fil monté à toute date (copie montée)")
    r(f"  fil monté aujourd'hui : {p.machine_aujourdhui_mad:,.2f} MAD ; {len(p.dates)} dates ; "
      f"{p.comparees} valeurs comparées ; écarts expliqués par K7 : {p.expliques} ; "
      f"à corriger : {len(p.a_corriger)}")  # fmt: skip
    r.par_classe["K7"] += p.expliques
    r.a_corriger += len(p.a_corriger) + (1 if p.machine_aujourdhui_mad <= 0 else 0)
    rp.detail_a_corriger(r, [(d, "/".join(c), g, x) for d, c, g, x in p.a_corriger])


def main(arguments: list[str] | None = None) -> int:
    """Toutes les passes ; rend le code de sortie (0 : à corriger 0)."""
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--sortie", default=str(ESSAIS / "resultat-parite.txt"))
    a.add_argument("--passes", default=",".join(PASSES))
    a.add_argument("--garder", action="store_true", help="ne pas supprimer les bases d'essai")
    o = a.parse_args(arguments)
    passes = set(o.passes.split(","))
    bases, r = pb.Bases(), rp.Rapport()
    with tempfile.TemporaryDirectory(prefix="parite-") as tmp:
        dossier = Path(tmp)
        try:
            prep = pb.preparer(bases)
            entete(r, prep, bases)
            jeux = statique(r, bases, dossier) if passes & {"statique", "api"} else {}
            if "api" in passes:
                passe_api(r, bases, dossier, jeux)
            if "dynamique" in passes:
                passe_dynamique(r, bases, dossier)
            if "k7" in passes:
                passe_k7(r, bases, dossier)
        finally:
            if not o.garder:
                pb.nettoyer(bases)
    rp.corrections(r)
    r.titre("Verdict")
    r(f"  À CORRIGER : {r.a_corriger}")
    r(
        f"  expliqués : {sum(n for k, n in r.par_classe.items() if k != 'à corriger')} "
        f"({', '.join(f'{k} {n}' for k, n in sorted(r.par_classe.items()) if k != 'à corriger')})"
    )
    Path(o.sortie).write_text("\n".join(r.lignes) + "\n", encoding="utf-8")
    sys.stdout.write(f"Parité : à corriger {r.a_corriger} — rapport {o.sortie}\n")
    return 0 if r.a_corriger == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
