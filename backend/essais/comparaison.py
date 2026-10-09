"""Comparaison chiffre par chiffre avec Gestion MP en service (lot C1 ; ARCHITECTURE § 14.3).

Réutilise la parité de R2 (`parite_*`), appliquée à la base de Gestion MP **choisie** (la
production `gestion_mp` telle qu'elle est, ou l'année d'essai `gestion_mp_comparaison`), à
plusieurs dates :

- **moteurs** : les deux moteurs sur la même copie reprise, sans HTTP (`parite_statique`) ;
- **api** : deux serveurs lancés par l'outil sur des copies (Gestion MP sur une copie de la
  source, PRO sur la base reprise de cette copie), interrogés par leurs routes GET
  (`parite_api_passe`), un compte direction et un compte alimentation de chacun.

Les sections comparées (stocks magasins/métiers/quarantaine, valorisation, CMUP, besoins, plan
d'achat, contrôles, cockpit, coût de revient des dossiers…) sont celles de la parité ; chaque
écart est expliqué par une règle de R2 (K1…K9) qui recalcule son ampleur, sinon il est « à
corriger ». Un `saboteur` (essai de sensibilité) perturbe les sorties de PRO pour prouver que
le comparateur **voit** une faute.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import comparaison_bases as cb
import gestion_mp_calcul as calcul
import parite_api_passe as api
import parite_bases as pb
import parite_chaine_base as pcb
import parite_donnees as pd
import parite_serveurs as srv
import parite_statique as st


def _contexte_scinde(bases: pb.Bases, dossier: Path) -> pd.Contexte:
    """K8b : le dépôt de Gestion MP relu sur une copie où les réceptions bi-devises sont
    scindées (comme `parite_gestion_mp.donnees_scindees`)."""
    adresse = pb.url(f"{bases.prefixe}_scindee_essai")
    try:
        pb.copier(bases.copie.rsplit("/", 1)[-1], adresse)
        comptes = pcb.traduire(adresse, "K8b")
        (dossier / "scindee").mkdir(parents=True, exist_ok=True)
        d0s = st.donnees_gestion_mp(adresse, dossier / "scindee")["donnees"]
    finally:
        pb.supprimer(adresse)
    return pd.lire_contexte(d0s, comptes["reception.scindee"])


Saboteur = Callable[[dict[str, Any]], list[str]]
"""Perturbe les sorties de PRO (moteurs) ; rend la liste des fautes réellement injectées."""


@dataclass
class Resultat:
    """Le résultat d'une comparaison sur une source, à un mode."""

    source: str
    mode: str
    dates: list[str]
    prep: cb.Preparation
    sections: dict[str, Counter[str]] = field(default_factory=dict)
    details: list[tuple[str, str, Any, Any]] = field(default_factory=list)
    comparees: int = 0
    a_corriger: int = 0
    fautes: list[str] = field(default_factory=list)
    versions: dict[str, str] = field(default_factory=dict)

    @property
    def expliquees(self) -> Counter[str]:
        """Les écarts expliqués, par classe (hors « à corriger »)."""
        total: Counter[str] = Counter()
        for compte in self.sections.values():
            for classe, n in compte.items():
                if classe not in ("comparées", "à corriger", "moteur à corriger"):
                    total[classe] += n
        return total


def _filtrer(sections: dict[str, Counter[str]], garder: set[str] | None) -> dict[str, Counter[str]]:
    """Ne garde que les sections demandées (par préfixe), toutes si `garder` est vide."""
    if not garder:
        return sections
    return {s: c for s, c in sections.items() if any(s.startswith(g) for g in garder)}


def _totaux(r: Resultat) -> None:
    """Remplit `comparees` et `a_corriger` depuis les sections (après filtrage)."""
    for compte in r.sections.values():
        r.comparees += compte.get("comparées", 0)
        r.a_corriger += compte.get("à corriger", 0) + compte.get("moteur à corriger", 0)


def comparer_moteurs(  # noqa: PLR0917
    source: str,
    bases: pb.Bases,
    dates: list[str],
    dossier: Path,
    prep: cb.Preparation,
    garder: set[str] | None = None,
    saboteur: Saboteur | None = None,
) -> Resultat:
    """Les deux moteurs sur la copie reprise, à chaque date (`parite_statique`)."""
    r = Resultat(source, "moteurs", dates, prep, versions={"gestion_mp": srv.pb_commit()})
    d0 = st.donnees_gestion_mp(bases.copie, dossier)["donnees"]
    complet = st.donnees_pro(bases.pro)
    dpro = pd.sans_index(json.loads(calcul.texte_json(complet)))
    ecarts = pd.ecarts(d0, dpro, _contexte_scinde(bases, dossier))
    chaine = pd.chaine(d0, ecarts)
    jeux = st.ecrire_jeux(dossier, d0, chaine)
    st.calculer_gestion_mp(jeux, dossier, tuple(dates))
    original = st.sorties_pro
    if saboteur is not None:
        st.sorties_pro = _avec_saboteur(original, saboteur, r)
    try:
        jours = [st.comparer_jour(dossier, complet, j, [c for c, _ in chaine]) for j in dates]
    finally:
        st.sorties_pro = original
    r.sections = _filtrer(st.resume(jours), garder)
    r.details = _details_moteurs(jours, r.sections)
    _totaux(r)
    return r


def _avec_saboteur(original: Any, saboteur: Saboteur, r: Resultat) -> Any:
    """Enveloppe `sorties_pro` : perturbe la sortie de PRO une fois (sur la 1re date utile)."""

    def sabote(complet: Any, jour: date) -> Any:
        sortie = original(complet, jour)
        if not r.fautes:
            r.fautes = saboteur(sortie)
        return sortie

    return sabote


def _details_moteurs(
    jours: list[st.Jour], sections: dict[str, Counter[str]]
) -> list[tuple[str, str, Any, Any]]:
    """Les écarts à corriger, en clair (section présente dans le filtre)."""
    details: list[tuple[str, str, Any, Any]] = []
    for jour in jours:
        for e in jour.ecarts:
            if e.classe is None and e.chemin[0] in sections:
                details.append(
                    (f"{jour.jour} · {e.chemin[0]}", "/".join(map(str, e.chemin[1:])), e.gmp, e.pro)
                )
        for chemin, g, p in jour.moteur:
            if chemin[0] in sections:
                details.append(
                    (f"{jour.jour} · {chemin[0]} (moteur)", "/".join(map(str, chemin[1:])), g, p)
                )
    return details


def comparer_api(  # noqa: PLR0917
    bases: pb.Bases,
    dates: list[str],
    mois: list[str],
    dossier: Path,
    prep: cb.Preparation,
    garder: set[str] | None = None,
) -> Resultat:
    """Les deux serveurs lancés sur les copies, routes GET comparées (`parite_api_passe`)."""
    r = Resultat(prep.source, "api", dates, prep)
    d0 = st.donnees_gestion_mp(bases.copie, dossier)["donnees"]
    complet = st.donnees_pro(bases.pro)
    dpro = pd.sans_index(json.loads(calcul.texte_json(complet)))
    ecarts = pd.ecarts(d0, dpro, _contexte_scinde(bases, dossier))
    jeux = {p.stem: p for p in st.ecrire_jeux(dossier, d0, pd.chaine(d0, ecarts))}
    with srv.demarrer(bases, dossier) as s:
        r.versions = dict(s.versions)
        passe = api.passe(s, bases, jeux, dossier / "api", dates, mois)
    r.sections = _filtrer(_resume_api(passe.resultats), garder)
    r.details = [
        (f"{x.route} {e.cle}", e.champ, e.gmp, e.pro)
        for x in passe.resultats
        for e in x.ecarts
        if e.classe is None and _groupe(x.route) in r.sections
    ]
    _totaux(r)
    return r


def _groupe(nom: str) -> str:
    """Le nom de section d'une route (sans la date ni les parenthèses)."""
    return nom.split(" (", maxsplit=1)[0].split(" 20", maxsplit=1)[0]


def _resume_api(resultats: list[api.Resultat]) -> dict[str, Counter[str]]:
    """Par section (route sans date) : comparées, écarts par classe, à corriger."""
    sortie: dict[str, Counter[str]] = {}
    for x in resultats:
        c = sortie.setdefault(_groupe(x.route), Counter())
        c["comparées"] += x.comparees
        for e in x.ecarts:
            c[e.classe or "à corriger"] += 1
    return sortie


def saboteur_essai(sorties: dict[str, Any]) -> list[str]:
    """Quatre fautes dans les sorties de PRO (essai de sensibilité du comparateur) : CMUP × 1,1,
    un contrôle muet, un stock décalé d'1 kg, un coût de revient faux. Rend celles qui ont pu
    être posées (une section vide — base de production sans activité — n'en pose aucune)."""
    faites: list[str] = []
    cmup = sorties.get("cmup_par_reference")
    if isinstance(cmup, dict) and cmup:
        cle = sorted(cmup)[0]
        if isinstance(cmup[cle], (int, float)) and cmup[cle]:
            cmup[cle] = cmup[cle] * 1.1
            faites.append(f"CMUP de « {cle} » × 1,1")
    stock = sorties.get("stock")
    if isinstance(stock, list) and stock:
        stock[0]["stock_net"] = (stock[0].get("stock_net") or 0) + 1
        faites.append(f"stock de « {stock[0].get('reference')} » décalé d'1 kg")
    for controle in sorties.get("controles") or []:
        if controle.get("anomalies"):
            controle["anomalies"] = 0
            controle["detail"] = []
            faites.append(f"contrôle {controle.get('code')} rendu muet")
            break
    faites += _sabote_revient(sorties)
    return faites


def _sabote_revient(sorties: dict[str, Any]) -> list[str]:
    """Un coût de revient de dossier faux (première ligne du premier mois avec des dossiers)."""
    revient = sorties.get("revient")
    if not isinstance(revient, dict):
        return []
    for mois, lignes in sorted(revient.items()):
        if isinstance(lignes, list) and lignes and isinstance(lignes[0], dict):
            for champ in ("revient_mad", "revient_unite", "valeur_mad"):
                if champ in lignes[0]:
                    lignes[0][champ] = (lignes[0][champ] or 0) + 1000
                    return [f"coût de revient d'un dossier de {mois} faux (+1000)"]
    return []
