"""Scénario de bout en bout : un mois d'usine joué par l'API, chaque rôle avec son compte (V2).

PLAN-DE-RECETTE-PRO § 8, critère A7. Le scénario part d'une **copie de l'année de parité**
(`gestion_mp_comparaison` copiée en lecture seule, puis reprise par R1), lance un **vrai serveur
PRO** sur un port libre au-dessus de 8100 et y joue, jour après jour de novembre 2026, chaque
geste avec le compte du bon rôle (direction, achats, alimentation, administrateur). Chaque
valeur attendue est calculée à la main dans le script **avant** le geste ; chaque refus attendu
aussi (rôle interdit, prix masqués pour l'alimentation, numéros sans trou…).

    cd backend
    .venv/bin/python essais/scenario_complet.py [--court] [--prefixe P] [--garder]
        [--modele BASE] [--sortie essais/resultat-scenario.txt]

- `--court` : base neuve migrée (semences seules) au lieu de la copie de l'année d'essai, sans
  sauvegarde ni restauration ; c'est la version que l'essai pytest lance.
- `--modele` : clone une base PRO déjà reprise (mise au point) au lieu de refaire la copie.
- `--garder` : ne supprime pas les bases à la fin.

Code de sortie : 0 toutes les étapes justes, 1 au moins un écart, 2 préparation impossible.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import time
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))

import scenario_bases as bases  # noqa: E402
import scenario_serveur as serveur  # noqa: E402
from scenario_etapes import ETAPES, ETAPES_COURTES  # noqa: E402
from scenario_monde import COMPTES, JOURS, Monde  # noqa: E402
from scenario_outils import Horloge, Verif  # noqa: E402
from scenario_resultat import ecrire  # noqa: E402

PREFIXE = "gestion_mp_pro_v2_scenario"


def _arguments(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Scénario de bout en bout (un mois d'usine)")
    p.add_argument("--court", action="store_true", help="base neuve, étapes courtes")
    p.add_argument("--prefixe", default=PREFIXE, help="préfixe des bases d'essai")
    p.add_argument("--modele", default="", help="base PRO reprise à cloner (mise au point)")
    p.add_argument("--garder", action="store_true", help="garder les bases à la fin")
    p.add_argument("--sortie", default="", help="fichier du résultat")
    return p.parse_args(argv)


def preparer(a: argparse.Namespace, pro: str, source: str) -> dict[str, object]:
    """La base du scénario : neuve (court), clonée d'un modèle, ou copie reprise de l'année."""
    infos: dict[str, object] = {}
    if a.court:
        bases.migrer(pro)
        infos["base"] = "neuve, migrée (semences seules)"
    elif a.modele:
        bases.supprimer(pro)
        bases.cloner(a.modele, pro)
        infos["base"] = f"clone de {a.modele} (reprise de l'année d'essai)"
    else:
        avant = bases.empreintes()
        bases.copier(bases.SOURCE, source)
        rapport = bases.reprendre(source, pro)
        apres = bases.empreintes()
        infos["base"] = f"copie de {bases.SOURCE} reprise par R1 ({len(rapport)} car. de rapport)"
        infos["sources_intactes"] = avant == apres
    identifiant, nom, _role, code = COMPTES["D"]
    bases.poser_direction(pro, identifiant, nom, code)
    return infos


def jouer(a: argparse.Namespace, pro: str, dossier: Path, verif: Verif) -> Monde:
    """Lance le serveur et joue les étapes ; le serveur est toujours arrêté en sortie."""
    from gestion_mp_pro.config import ENTETE_ANTI_FALSIFICATION

    horloge = Horloge(dossier / "horloge.txt")
    horloge.aller(JOURS["referentiels"])
    env = serveur.environnement_pro(pro, dossier)
    with serveur.lancer("pro", env, horloge.fichier, dossier / "pro.log") as adresse:
        monde = Monde(verif, horloge, adresse, ENTETE_ANTI_FALSIFICATION, court=a.court)
        monde.avant["dossier"] = dossier
        monde.avant["base"] = pro
        for numero, titre, etape in ETAPES_COURTES if a.court else ETAPES:
            with verif.etape(numero, titre):
                etape(monde)
    return monde


def main(argv: list[str] | None = None) -> int:
    """Prépare, joue, écrit le résultat, nettoie ; rend le code de sortie."""
    a = _arguments(argv)
    pro, source = bases.url(f"{a.prefixe}_essai"), bases.url(f"{a.prefixe}_source_essai")
    verif = Verif()
    monde: Monde | None = None
    infos: dict[str, object] = {}
    debut = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="scenario-v2-") as d:
        dossier = Path(d)
        try:
            infos = preparer(a, pro, source)
            monde = jouer(a, pro, dossier, verif)
        finally:
            if not a.garder:
                for adresse in (pro, source):
                    bases.supprimer(adresse)
        infos["duree_s"] = round(time.monotonic() - debut, 1)
        texte = ecrire(verif, monde, infos, court=a.court)
    sortie = Path(a.sortie) if a.sortie else None
    if sortie is not None:
        sortie.write_text(texte, encoding="utf-8")
    sys.stdout.write(texte)
    return 0 if not verif.echecs else 1


if __name__ == "__main__":
    sys.exit(main())
