"""Outils de la parité unitaire : relire un jeu figé en `Donnees` PRO, calculer les mêmes
sorties que `essais/gestion_mp_calcul.py` avec le moteur PRO, les comparer.

Le format des jeux est celui de `essais/gestion_mp_calcul.py` (relu ici d'après les
annotations des dataclasses PRO, qui portent les mêmes champs que celles de Gestion MP).
"""

from __future__ import annotations

import dataclasses
import json
import lzma
import types
import typing
from datetime import date, datetime
from functools import cache
from pathlib import Path
from typing import Any

from gestion_mp_pro.calcul.constantes import (
    ACTION_AUCUNE,
    ACTION_CREER_BC,
    LIBELLES_GESTION_MP,
    LIBELLES_STATUT,
)
from gestion_mp_pro.calcul.modele import Donnees

JEUX = Path(__file__).parent / "jeux"


def noms_des_jeux() -> list[str]:
    """Les jeux figés, dans l'ordre (01 … 20)."""
    return sorted(p.name.removesuffix(".json.xz") for p in JEUX.glob("[0-9][0-9]-*[!u].json.xz"))


def lire(chemin: Path) -> Any:
    """Un fichier JSON compressé (xz)."""
    with lzma.open(chemin, "rt", encoding="utf-8") as f:
        return json.load(f)


@cache
def _annotations(cls: type) -> dict[str, Any]:
    return typing.get_type_hints(cls)


def _tuple(v: list[Any], *elements: Any) -> tuple[Any, ...]:
    return tuple(depuis_json(e, a) for e, a in zip(v, elements, strict=True))


def _dict(v: Any, cle: Any = Any, valeur: Any = Any) -> dict[Any, Any]:
    if typing.get_origin(cle) is tuple:
        n = len(typing.get_args(cle))
        return {_tuple(r[:n], *typing.get_args(cle)): depuis_json(r[n], valeur) for r in v}
    return {(int(k) if cle is int else k): depuis_json(e, valeur) for k, e in v.items()}


def _liste(v: list[Any], element: Any = Any) -> list[Any]:
    return [depuis_json(e, element) for e in v]


_LECTEURS: dict[Any, Any] = {list: _liste, tuple: _tuple, dict: _dict}


def depuis_json(v: Any, annotation: Any) -> Any:
    """Une valeur JSON rendue au type de l'annotation (nombres tels quels)."""
    if v is None:
        return None
    if typing.get_origin(annotation) in (typing.Union, types.UnionType):
        utiles = [a for a in typing.get_args(annotation) if a is not type(None)]
        return depuis_json(v, utiles[0]) if len(utiles) == 1 else v
    if annotation in (date, datetime):
        return annotation.fromisoformat(v)
    if dataclasses.is_dataclass(annotation):
        return relire_dataclass(annotation, v)  # type: ignore[arg-type]
    lecteur = _LECTEURS.get(typing.get_origin(annotation) or annotation)
    return lecteur(v, *typing.get_args(annotation)) if lecteur else v


def relire_dataclass(cls: type, v: dict[str, Any]) -> Any:
    """Une dataclass PRO reconstruite champ par champ ; les champs que PRO n'a plus (le
    réglage `methode`) sont ignorés, les champs hors constructeur aussi."""
    hints = _annotations(cls)
    champs = [f for f in dataclasses.fields(cls) if f.init and f.name in v]  # type: ignore[arg-type]
    return cls(**{f.name: depuis_json(v[f.name], hints[f.name]) for f in champs})


def relire_jeu(nom: str) -> tuple[dict[str, Any], Donnees]:
    """L'en-tête d'un jeu et ses `Donnees` PRO."""
    jeu = lire(JEUX / f"{nom}.json.xz")
    donnees = relire_dataclass(Donnees, jeu.pop("donnees"))
    return jeu, donnees


def attendu(nom: str) -> dict[str, Any]:
    """Les sorties du moteur de Gestion MP pour ce jeu."""
    return lire(JEUX / f"{nom}.attendu.json.xz")  # type: ignore[no-any-return]


def _texte_cle(k: Any) -> str:
    return " | ".join(map(str, map(propre, k))) if isinstance(k, tuple) else str(propre(k))


def propre(x: Any) -> Any:
    """La même mise à plat que `essais/gestion_mp_calcul.propre` (sans arrondi)."""
    if dataclasses.is_dataclass(x) and not isinstance(x, type):
        x = {f.name: getattr(x, f.name) for f in dataclasses.fields(x)}
    elif not isinstance(x, dict | list | tuple | set | frozenset | date) and hasattr(x, "__dict__"):
        x = vars(x)
    if isinstance(x, dict):
        return {_texte_cle(k): propre(v) for k, v in x.items()}
    if isinstance(x, list | tuple | set | frozenset):
        valeurs = [propre(v) for v in x]
        return sorted(valeurs, key=str) if isinstance(x, set | frozenset) else valeurs
    if isinstance(x, date):
        return x.isoformat()
    if x is None or isinstance(x, str | int | float):
        return x
    raise TypeError(f"Sortie de type inattendu : {type(x).__name__}")


CHAMPS_DE_STATUT = ("statut", "statut_couverture")
"""Les champs où PRO rend un code de statut et Gestion MP son libellé à émoji (RESTES3, S3)."""


def comme_gestion_mp(x: Any) -> Any:
    """Les sorties PRO mises à plat (`propre`), codes ramenés à la forme de Gestion MP : statut
    « CRITIQUE » → « 🔴 CRITIQUE », action « CREER_BC » → « 📝 Créer BC - <fournisseur> »,
    « AUCUNE » → « — », relance du plan d'achat « CRITIQUE — … » → « 🔴 CRITIQUE — … ». Même
    valeur logique, autre forme (seule différence voulue)."""
    if isinstance(x, list):
        return [comme_gestion_mp(v) for v in x]
    if not isinstance(x, dict):
        return x
    rendu = {k: comme_gestion_mp(v) for k, v in x.items()}
    for cle in CHAMPS_DE_STATUT:
        if isinstance(rendu.get(cle), str) and rendu[cle] in LIBELLES_GESTION_MP:
            rendu[cle] = LIBELLES_GESTION_MP[rendu[cle]]
    relance = rendu.get("relance")
    for code, libelle in LIBELLES_STATUT.items():
        if isinstance(relance, str) and relance.startswith(f"{libelle} — "):
            rendu["relance"] = LIBELLES_GESTION_MP[code] + relance.removeprefix(libelle)
    if rendu.get("action") == ACTION_CREER_BC:
        rendu["action"] = f"📝 Créer BC - {rendu.get('fournisseur', '')}"
    elif rendu.get("action") == ACTION_AUCUNE:
        rendu["action"] = "—"
    return rendu


def differences(
    attendu_: Any, obtenu: Any, chemin: str = "", sortie: list[str] | None = None
) -> list[str]:
    """Les chemins où deux sorties diffèrent (égalité exacte des nombres)."""
    sortie = [] if sortie is None else sortie
    if len(sortie) >= 20:
        return sortie
    if isinstance(attendu_, dict) and isinstance(obtenu, dict):
        for k in sorted(set(attendu_) | set(obtenu)):
            if k not in obtenu or k not in attendu_:
                sortie.append(f"{chemin}/{k} : présent d'un seul côté")
            else:
                differences(attendu_[k], obtenu[k], f"{chemin}/{k}", sortie)
    elif isinstance(attendu_, list) and isinstance(obtenu, list) and len(attendu_) == len(obtenu):
        for i, (a, o) in enumerate(zip(attendu_, obtenu, strict=True)):
            differences(a, o, f"{chemin}/{i}", sortie)
    elif attendu_ != obtenu or isinstance(attendu_, bool) != isinstance(obtenu, bool):
        sortie.append(f"{chemin} : Gestion MP {attendu_!r} ≠ PRO {obtenu!r}")
    return sortie
