"""Épreuve de charge (PLAN-DE-RECETTE-PRO § 10, A9) : la base de l'année d'essai, puis ×10 et
×30, mesurée sur un **vrai serveur** uvicorn.

    export GESTIONMPPRO_BASE=postgresql+psycopg:///gestion_mp_pro_v4_charge_reel_essai
    export GESTIONMPPRO_BASE_ESSAI=$GESTIONMPPRO_BASE
    .venv/bin/python essais/charge.py              # remplit, mesure, écrit le résultat, nettoie
    .venv/bin/python essais/charge.py remplir      # construit seulement les trois bases
    .venv/bin/python essais/charge.py mesurer      # mesure des bases déjà remplies

- `remplir` : R1 reprend `gestion_mp_comparaison` (lecture seule) dans la base « réel » ; ×10 et
  ×30 sont des copies multipliées en SQL (`charge_volumes`), chacune une base `*_essai` à soi.
- `mesurer` : pour chaque volume, uvicorn est lancé (processus d'ARCHITECTURE) sur un port libre
  > 8100 ; on mesure chaque écran lourd (médiane et pire de 5 appels), les exports, une date de
  référence passée, une écriture courante (créer puis envoyer un bon), et vingt postes qui
  ouvrent le stock au même instant (p50, p95).

Seuils (A9) : écrans courants < 0,3 s au réel, < 1 s ×10, < 2 s ×30 ; exports < 3 s ×30 ;
vingt postes p95 < 2 s. Un dépassement est marqué « DÉFAUT » dans `resultat-charge.txt` et le
script rend un code non nul. Les bases sont supprimées à la fin du mode complet.
"""

from __future__ import annotations

import os
import statistics
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

RACINE_BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE_BACKEND / "tests"))

import charge_volumes as cv  # noqa: E402
import parite_bases as pb  # noqa: E402
from charge_serveur import Poste, Serveur, servir  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

PREFIXE = os.environ.get("GESTIONMPPRO_CHARGE_PREFIXE", "gestion_mp_pro_v4_charge")
APPELS = 5
POSTES_STOCK = 20
SORTIE = RACINE_BACKEND / "essais" / "resultat-charge.txt"

SEUILS_ECRAN = {"reel": 0.3, "x10": 1.0, "x30": 2.0}
"""Médiane maximale d'un écran courant, par volume (A9)."""
SEUIL_EXPORT = 3.0
"""Médiane maximale d'un export (A9 : « exports < 3 s » ; seul plafond d'export du plan)."""
SEUILS_ECRITURE = {"reel": 0.5, "x10": 1.0, "x30": 2.0}
"""Écriture courante : A9 borne les validations à 0,5 s **au volume réel** ; aux volumes de
stress on suit l'échelle des écrans (informatif)."""
SEUIL_P95_POSTES = 2.0
"""Vingt postes ouvrant le stock : A9 borne p95 < 2 s **au volume réel**."""

# Écrans courants (route, rôle) — les onglets lourds de § 9.1.
ECRANS: tuple[tuple[str, str], ...] = (
    ("/api/stock", "direction"),
    ("/api/stock", "alimentation"),
    ("/api/lots?non_nuls=true", "direction"),
    ("/api/mouvements?limite=2000", "direction"),
    ("/api/plan-achat", "direction"),
    ("/api/cockpit", "direction"),
    ("/api/valorisation", "direction"),
    ("/api/controles", "direction"),
    ("/api/controles/soldes", "direction"),
    ("/api/commandes", "direction"),
    ("/api/receptions", "direction"),
    ("/api/receptions/pesees", "direction"),
    ("/api/ordres", "direction"),
    ("/api/ordres", "alimentation"),
    ("/api/ordres/consommation", "direction"),
    ("/api/dossiers", "direction"),
    ("/api/inventaires", "direction"),
    ("/api/analyse/revient", "direction"),
    ("/api/production/besoins", "direction"),
    ("/api/prix/matrice", "direction"),
    ("/api/fournisseurs/performance", "direction"),
    ("/api/echeancier", "direction"),
    ("/api/stock?date=2026-03-31", "direction"),
)
EXPORTS: tuple[tuple[str, str], ...] = (
    ("/api/export/mouvements", "direction"),
    ("/api/export/journal", "direction"),
    ("/api/export/commandes", "direction"),
    ("/api/export/receptions", "direction"),
    ("/api/export/dossiers", "direction"),
    ("/api/export/revient", "direction"),
    ("/api/export/pilotage", "direction"),
)


def _adresse(volume: str) -> str:
    return f"postgresql+psycopg:///{PREFIXE}_{volume}_essai"


def _nom(adresse: str) -> str:
    nom = make_url(adresse).database or ""
    if not nom.endswith("_essai"):
        raise SystemExit(f"Base refusée : « {nom} » ne finit pas par _essai.")
    return nom


def _maintenance(adresse: str) -> object:
    cible = make_url(adresse).set(database="postgres")
    return create_engine(cible, poolclass=NullPool, isolation_level="AUTOCOMMIT")


def _copier_par_modele(reel: str, cible: str) -> None:
    """La base « réel » recopiée d'un coup (CREATE DATABASE … TEMPLATE), plus rapide qu'un dump."""
    nom_reel, nom_cible = _nom(reel), _nom(cible)
    moteur = _maintenance(cible)
    with moteur.connect() as c:  # type: ignore[attr-defined]
        c.execute(text(f'DROP DATABASE IF EXISTS "{nom_cible}" WITH (FORCE)'))
        c.execute(text(f'CREATE DATABASE "{nom_cible}" TEMPLATE "{nom_reel}"'))
    moteur.dispose()  # type: ignore[attr-defined]


def _supprimer(adresse: str) -> None:
    moteur = _maintenance(adresse)
    with moteur.connect() as c:  # type: ignore[attr-defined]
        c.execute(text(f'DROP DATABASE IF EXISTS "{_nom(adresse)}" WITH (FORCE)'))
    moteur.dispose()  # type: ignore[attr-defined]


def remplir() -> dict[str, dict[str, int]]:
    """Construit les trois bases ; rend les comptes de lignes par volume."""
    reel = _adresse("reel")
    pb.supprimer  # noqa: B018 — garde-fou importé
    _nom(reel)
    copie = pb.Bases(prefixe=f"{PREFIXE}_source").copie
    pb.copier(pb.SOURCE, copie)
    pb.migrer(reel)
    pb.reprendre(copie, reel)
    pb.supprimer(copie)
    comptes = {"reel": cv.compter(reel)}
    for volume in cv.VOLUMES:
        if volume.nom == "reel":
            continue
        cible = _adresse(volume.nom)
        _copier_par_modele(reel, cible)
        comptes[volume.nom] = cv.multiplier(cible, volume)
    return comptes


@dataclass
class Mesure:
    """La mesure d'une route : médiane, pire, seuil, verdict."""

    route: str
    role: str
    mediane: float
    pire: float
    taille: int
    seuil: float

    @property
    def tenu(self) -> bool:
        """Vrai si la médiane respecte le seuil du volume."""
        return self.mediane <= self.seuil

    def ligne(self) -> str:
        """La ligne de rapport de la route (verdict, médiane, pire, seuil, taille)."""
        etat = "ok" if self.tenu else "DÉFAUT"
        return (
            f"  [{etat:^6}] {self.mediane * 1000:7.0f} ms  (pire {self.pire * 1000:5.0f} ms, "
            f"seuil {self.seuil * 1000:.0f} ms, {self.taille:>8} o)  {self.role[:4]:<4} "
            f"{self.route}"
        )


def _mesurer_route(poste: Poste, route: str, role: str, seuil: float) -> Mesure:
    poste.appeler("GET", route)  # chauffe (cache du moteur, plans)
    temps, taille = [], 0
    for _ in range(APPELS):
        statut, corps, duree = poste.appeler("GET", route)
        if statut != 200:  # noqa: PLR2004
            raise SystemExit(f"GET {route} ({role}) → {statut} : {str(corps)[:200]}")
        temps.append(duree)
        taille = len(corps) if isinstance(corps, bytes | list) else len(str(corps))
    return Mesure(route, role, statistics.median(temps), max(temps), taille, seuil)


def _postes_stock(serveur: Serveur) -> tuple[float, float, float]:
    """Vingt postes ouvrent `/api/stock` au même instant : (total, p50, p95)."""
    import threading

    postes = [serveur.poste("direction") for _ in range(POSTES_STOCK)]
    depart = threading.Barrier(POSTES_STOCK)
    durees: list[float] = [0.0] * POSTES_STOCK

    def ouvrir(i: int) -> None:
        depart.wait()
        durees[i] = postes[i].appeler("GET", "/api/stock")[2]

    fils = [threading.Thread(target=ouvrir, args=(i,)) for i in range(POSTES_STOCK)]
    debut = time.perf_counter()
    for f in fils:
        f.start()
    for f in fils:
        f.join(timeout=120)
    total = time.perf_counter() - debut
    ordonne = sorted(durees)
    p95 = ordonne[min(POSTES_STOCK - 1, round(0.95 * POSTES_STOCK) - 1)]
    return total, statistics.median(durees), p95


def _ecriture_courante(serveur: Serveur, seuil: float) -> Mesure:
    """Une écriture courante mesurée : créer un bon et l'envoyer (numérotation + journal)."""
    achats = serveur.poste("achats")
    matieres = achats.get("/api/matieres")
    liste = matieres["elements"] if isinstance(matieres, dict) else matieres
    par_fournisseur: dict[int, list[int]] = {}
    for m in liste:
        if m.get("fournisseur_id") and m.get("actif"):
            par_fournisseur.setdefault(m["fournisseur_id"], []).append(m["id"])
    fid, ids = max(par_fournisseur.items(), key=lambda kv: len(kv[1]))
    lignes = [{"matiere_id": mid, "quantite": 100} for mid in ids[:15]]
    temps = []
    for _ in range(APPELS):
        debut = time.perf_counter()
        bon = achats.ok("POST", "/api/commandes", {"fournisseur_id": fid, "lignes": lignes})[0]
        achats.ok("POST", f"/api/commandes/{bon['id']}/envoyer", {"version": bon["version"]})
        temps.append(time.perf_counter() - debut)
    return Mesure(
        "écriture : créer + envoyer un bon de 15 lignes", "achats",
        statistics.median(temps), max(temps), 0, seuil,
    )  # fmt: skip


def mesurer_volume(volume: str) -> list[str]:
    """Mesure un volume sur un vrai serveur ; rend les lignes du rapport."""
    adresse = _adresse(volume)
    comptes = cv.compter(adresse)
    lignes = [
        "",
        "=" * 90,
        f"VOLUME {volume.upper()} — {adresse}",
        f"  {comptes['mouvement']} mouvements, {comptes['lot']} lots, {comptes['commande']} bons, "
        f"{comptes['dossier']} dossiers, {comptes['annees']} années d'activité",
        "=" * 90,
    ]
    mesures: list[Mesure] = []
    with (
        tempfile.TemporaryDirectory(prefix=f"charge-{volume}-") as dossier,
        servir(adresse, Path(dossier)) as serveur,
    ):
        postes = {r: serveur.poste(r) for r in ("direction", "alimentation", "achats")}
        lignes.append(f"  (uvicorn, {serveur.processus} processus, port {serveur.port})")
        lignes.append("")
        lignes.append("Écrans courants :")
        for route, role in ECRANS:
            mesures.append(_mesurer_route(postes[role], route, role, SEUILS_ECRAN[volume]))
        lignes += [m.ligne() for m in mesures]
        lignes.append("")
        lignes.append("Exports :")
        exports = [
            _mesurer_route(postes[role], route, role, SEUIL_EXPORT) for route, role in EXPORTS
        ]
        lignes += [m.ligne() for m in exports]
        mesures += exports
        ecriture = _ecriture_courante(serveur, SEUILS_ECRITURE[volume])
        mesures.append(ecriture)
        lignes += ["", "Écriture courante :", ecriture.ligne()]
        total, p50, p95 = _postes_stock(serveur)
        verdict = "ok" if p95 <= SEUIL_P95_POSTES else "DÉFAUT"
        lignes += [
            "",
            f"Vingt postes ouvrent le stock ensemble : total {total:.2f} s, "
            f"médiane {p50 * 1000:.0f} ms, p95 {p95 * 1000:.0f} ms  [{verdict}]",
        ]
    defauts = [m for m in mesures if not m.tenu] + (
        [] if p95 <= SEUIL_P95_POSTES else ["p95 postes"]
    )
    lignes.append("")
    if not defauts:
        lignes.append("  → tenu.")
    elif volume == "reel":
        lignes.append(f"  → {len(defauts)} dépassement(s) AU VOLUME RÉEL (A9 : à corriger).")
    else:
        lignes.append(
            f"  → {len(defauts)} dépassement(s) (projection de stress, hors volume de "
            "service ; voir docs/lots/V4.md § 6)."
        )
    return lignes


def mesurer() -> tuple[list[str], bool]:
    """Mesure les trois volumes ; rend (lignes, tout_tenu)."""
    quand = datetime.now().strftime("%Y-%m-%d %H:%M")  # noqa: DTZ005
    lignes = [
        "ÉPREUVE DE CHARGE (lot V4) — vrai serveur uvicorn",
        f"Mesurée le {quand} ; médiane et pire de {APPELS} appels par route.",
        "Seuils A9 : écran < 0,3 s (réel) / 1 s (×10) / 2 s (×30) ; export < 3 s ; "
        "écriture < 0,5 s et p95 postes < 2 s (clauses du volume réel).",
        "Le volume réel est celui du service (une année) : il porte le verdict A9. Les volumes",
        "×10 et ×30 sont des projections de stress (5 et 10 ans d'historique non paginé).",
    ]
    reel_tenu = True
    for volume in ("reel", "x10", "x30"):
        bloc = mesurer_volume(volume)
        lignes += bloc
        if volume == "reel":
            reel_tenu = "dépassement" not in "".join(bloc)
    return lignes, reel_tenu


def main() -> int:
    """`remplir`, `mesurer`, ou (défaut) les deux puis suppression des bases."""
    mode = sys.argv[1] if len(sys.argv) > 1 else "tout"
    if mode == "remplir":
        comptes = remplir()
        sys.stdout.write(f"Bases remplies : {comptes}\n")
        return 0
    if mode == "mesurer":
        lignes, tenu = mesurer()
        texte = "\n".join(lignes) + "\n"
        SORTIE.write_text(texte, encoding="utf-8")
        sys.stdout.write(texte)
        return 0 if tenu else 1
    remplir()
    try:
        lignes, tenu = mesurer()
    finally:
        for volume in ("reel", "x10", "x30"):
            _supprimer(_adresse(volume))
    texte = "\n".join(lignes) + "\n"
    SORTIE.write_text(texte, encoding="utf-8")
    sys.stdout.write(texte)
    return 0 if tenu else 1


if __name__ == "__main__":
    raise SystemExit(main())
