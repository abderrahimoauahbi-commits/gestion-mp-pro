"""Compteurs de numéros et séquences d'identifiants, recalés après la reprise (§ 10.3).

- `compteur` (série, année) = le plus grand numéro repris de cette série et de cette année,
  numéros retirés aux brouillons compris (ils ne seront pas redonnés), et jamais moins que le
  compteur de Gestion MP. `LOT` : seuls les lots internes (`LOT-AAAA-NNNN`, incohérence 33).
  `DOS` : `annee` + `rang` des dossiers.
- Séquences : chaque identité est mise sur le plus grand identifiant présent.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from sqlalchemy import Integer, text

from gestion_mp_pro.modeles import metadata
from gestion_mp_pro.modeles.enums import SerieNumero
from gestion_mp_pro.reprise import ecriture
from gestion_mp_pro.reprise.contexte import Contexte
from gestion_mp_pro.reprise.outils import Lignes

NUMERO = re.compile(r"([A-Z]{2,3})-([0-9]{4})-([0-9]+)")
DOCUMENTS = ("commande", "reception", "ordre", "operation", "inventaire", "reclamation", "lot")
SERIES = frozenset(s.value for s in SerieNumero)


def _noter(dernier: dict[tuple[str, int], int], numero: str | None) -> None:
    """Prend en compte un numéro `SERIE-AAAA-NNNN`."""
    forme = NUMERO.fullmatch(numero or "")
    if forme and forme.group(1) in SERIES:
        cle = (forme.group(1), int(forme.group(2)))
        dernier[cle] = max(dernier[cle], int(forme.group(3)))


def compteurs(ctx: Contexte, lignes: Lignes) -> list[dict[str, Any]]:
    """Les lignes de `compteur` après la reprise de l'activité."""
    dernier: dict[tuple[str, int], int] = defaultdict(int)
    for table in DOCUMENTS:
        for v in lignes.get(table, []):
            if table != "lot" or v["interne"]:
                _noter(dernier, v["numero"])
        for numero in ctx.numeros_retires.get(table, []):
            _noter(dernier, numero)
    for d in lignes.get("dossier", []):
        if d["rang"] is not None:
            cle = (SerieNumero.DOS.value, int(d["annee"]))
            dernier[cle] = max(dernier[cle], int(d["rang"]))
    for c in ctx.photo.lignes("compteur"):
        if c["serie"] in SERIES and 2000 <= c["annee"] <= 2100:  # noqa: PLR2004
            cle = (c["serie"], int(c["annee"]))
            dernier[cle] = max(dernier[cle], int(c["dernier"]))
        else:
            ctx.signaler("compteur", f"{c['serie']}/{c['annee']}", "série ou année inconnue")
    return [{"serie": s, "annee": a, "dernier": n} for (s, a), n in sorted(dernier.items())]


def recaler_les_sequences(ctx: Contexte) -> list[str]:
    """Met chaque séquence d'identité sur le plus grand identifiant ; rend les tables recalées."""
    recalees = []
    for nom, t in sorted(metadata.tables.items()):
        if "id" not in t.c or not isinstance(t.c.id.type, Integer):
            continue
        sequence = ctx.c.execute(
            text("SELECT pg_get_serial_sequence(:t, 'id')"), {"t": nom}
        ).scalar()
        if sequence:
            ecriture.recaler_sequence(ctx, nom)
            recalees.append(nom)
    return recalees
