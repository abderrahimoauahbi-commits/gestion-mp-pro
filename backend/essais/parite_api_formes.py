"""Parité par l'API : les traductions de forme déclarées entre les réponses des deux serveurs.

PRO a changé la forme de plusieurs réponses (API-PRO, notes des lots § 4, RESTES « docs ») :
chaque différence de forme est **traduite** ici, champ par champ, par une fonction qui
vérifie ce qu'elle traduit ; elle n'est jamais excusée en bloc. Une valeur que la traduction
ne reconnaît pas reste telle quelle et l'écart se voit.

| Forme | Gestion MP | PRO | Raison |
|---|---|---|---|
| instant | heure de l'usine, sans fuseau, à la minute | ISO 8601 et décalage | ARCHITECTURE § 9.3 |
| nul | `0.0`, `""` pour « rien » (cours, personnes) | `null` | MODELE-DONNEES § 10.3 |
| personne de la reprise | « ERP Fil », « système »… | `null` ou `""` | R1 n° 9 |
| code sans émoji | « ⚪ Attendu », « 🟢 Stratégique » | `attendu`, « Stratégique » | P8-23 |
| renvoi | `["BC-2026-0024"]` | `[{"id": 102, "numero": "BC-2026-0024"}]` | API-PRO § 0 |
| statut | « Confirmée », `validee`… | codes de la base | table `STATUTS` |
| conseil de recette | « Franges (0 %) » | « … créer la matière Franges » (C01) | audit n° 2 |
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

USINE = ZoneInfo("Africa/Casablanca")
PERSONNES_DE_LA_REPRISE = {"ERP Fil", "système", "installation", "reprise ERP Fil", ""}
EMOJI = re.compile(r"^[^\w«(]+\s*")

Forme = Callable[[Any, Any], tuple[Any, Any]]


def instant(g: Any, p: Any) -> tuple[Any, Any]:
    """Un instant : PRO (avec décalage) ramené à l'heure de l'usine, à la précision de GMP."""
    if not isinstance(p, str) or not isinstance(g, str):
        return g, p
    try:
        lu = datetime.fromisoformat(p.replace("Z", "+00:00"))
    except ValueError:
        return g, p
    local = lu.astimezone(USINE).replace(tzinfo=None) if lu.tzinfo else lu
    return g, local.isoformat()[: len(g)]


def nul(g: Any, p: Any) -> tuple[Any, Any]:
    """« Rien » : `0`, `0.0`, `""` de Gestion MP valent `null` de PRO (et l'inverse)."""
    if p is None and g in (0, 0.0, ""):
        return None, None
    if g is None and p in (0, 0.0, ""):
        return None, None
    return g, p


def personne(g: Any, p: Any) -> tuple[Any, Any]:
    """Une personne : les noms de la reprise ne désignent personne dans PRO (R1 n° 9)."""
    if p in (None, "") and g in PERSONNES_DE_LA_REPRISE:
        return None, None
    return g, p


def sans_emoji(g: Any, p: Any) -> tuple[Any, Any]:
    """Un classement sans émoji (P8-23) : « 🟢 Stratégique » = « Stratégique »."""
    if isinstance(g, str) and isinstance(p, str) and EMOJI.sub("", g) == p:
        return p, p
    return g, p


def code(g: Any, p: Any) -> tuple[Any, Any]:
    """Un libellé codé (P8-23) : « 🟠 Partiel retard » = `partiel_retard` (sans émoji ni
    accent, en minuscules, blancs → « _ »)."""
    if not isinstance(g, str) or not isinstance(p, str):
        return g, p
    texte = unicodedata.normalize("NFKD", EMOJI.sub("", g)).encode("ascii", "ignore").decode()
    return (p if texte.strip().lower().replace(" ", "_") == p else g), p


def presence(g: Any, p: Any) -> tuple[Any, Any]:
    """Un oui/non de Gestion MP rendu par PRO comme l'objet lui-même (ou `null`)."""
    return (g, p is not None) if isinstance(g, bool) else (g, p)


def ids(g: Any, p: Any) -> tuple[Any, Any]:
    """Des identifiants : une liste d'ids = les `id` des objets de PRO."""
    if isinstance(g, list) and isinstance(p, list) and all(isinstance(x, dict) for x in p):
        return g, [x.get("id") for x in p]
    return g, p


def references(g: Any, p: Any) -> tuple[Any, Any]:
    """Des matières : une liste de références = les `reference` des objets {id, reference}."""
    if isinstance(g, list) and isinstance(p, list) and all(isinstance(x, dict) for x in p):
        return g, [x.get("reference") for x in p]
    return g, p


TYPES_DE_MAGASIN = {"Stock courant": "stock_courant", "Quarantaine": "quarantaine"}


def type_magasin(g: Any, p: Any) -> tuple[Any, Any]:
    """Le type d'un magasin : libellé de Gestion MP → code de PRO (MODELE-DONNEES § 10.3)."""
    return TYPES_DE_MAGASIN.get(g, g), p


def numeros(g: Any, p: Any) -> tuple[Any, Any]:
    """Des renvois : une liste de numéros = une liste d'objets {id, numero}."""
    if isinstance(g, list) and isinstance(p, list) and all(isinstance(x, dict) for x in p):
        return g, [x.get("numero") for x in p]
    return g, p


def jour(g: Any, p: Any) -> tuple[Any, Any]:
    """Une date seule : les deux en AAAA-MM-JJ."""
    if isinstance(g, str) and isinstance(p, str):
        return g[:10], p[:10]
    return g, p


def valeur_seule(cle: str) -> Forme:
    """Un objet de PRO dont Gestion MP ne rendait qu'un champ (« magasin » : son nom)."""

    def traduire(g: Any, p: Any) -> tuple[Any, Any]:
        return (g, p.get(cle)) if isinstance(p, dict) else (g, p)

    return traduire


def table(correspondance: dict[Any, Any]) -> Forme:
    """Une table de correspondance déclarée (libellés codés)."""

    def traduire(g: Any, p: Any) -> tuple[Any, Any]:
        return correspondance.get(g, g), p

    return traduire


def suite(*formes: Forme) -> Forme:
    """Plusieurs traductions, l'une après l'autre."""

    def traduire(g: Any, p: Any) -> tuple[Any, Any]:
        for f in formes:
            g, p = f(g, p)
        return g, p

    return traduire


TEXTES_AIDE = {
    "Qualités & recettes": "Qualités et recettes",
    "la personne qui entretient le serveur": "l'administrateur technique",
}
"""Les noms que PRO donne à ses menus et à ses rôles dans les textes d'aide (ECRANS-PRO)."""


def texte_aide(g: Any, p: Any) -> tuple[Any, Any]:
    """Un texte d'aide : mêmes mots, menus et rôles nommés comme dans PRO."""
    if not isinstance(g, str):
        return g, p
    for avant, apres in TEXTES_AIDE.items():
        g = g.replace(avant, apres)
    return g.strip(), p


def adresse_ecran(g: Any, p: Any) -> tuple[Any, Any]:
    """Une adresse d'écran : PRO ouvre le même écran, avec l'onglet ou le filtre voulu."""
    if isinstance(g, str) and isinstance(p, str) and p.split("?")[0] == g:
        return p, p
    return g, p


def surcout_en_pourcent(g: Any, p: Any) -> tuple[Any, Any]:
    """Le détail de C35 : PRO dit le surcoût en fraction (D8, P8-3), Gestion MP en pourcent
    arrondi à 0,1 (comme `tests/moteur/sorties_pro.detail_comme_gestion_mp`)."""
    if not isinstance(p, list) or not any(isinstance(x, dict) and "surcout" in x for x in p):
        return g, p
    rendu = []
    for x in p:
        copie = dict(x)
        fraction = copie.pop("surcout", None)
        copie["surcout_pct"] = None if fraction is None else round(fraction * 100, 1)
        rendu.append(copie)
    return g, rendu


def conseil_recette(g: Any, p: Any) -> tuple[Any, Any]:
    """Audit n° 2 (décision Franges) : PRO dit « créer la matière Franges » sur un rôle pesant
    que nulle matière du catalogue ne porte (ligne et « quoi faire » de C01, `sans_matiere` sur
    un écart de recette) ; Gestion MP disait « Franges (0 %) ». Même anomalie, même compte :
    la forme de PRO est ramenée à celle de Gestion MP (`tests/moteur/jeux_outils.CONSEIL_C01`)."""
    import sys
    from pathlib import Path

    tests = str(Path(__file__).resolve().parents[1] / "tests")
    if tests not in sys.path:
        sys.path.insert(0, tests)
    from moteur.jeux_outils import sans_conseil_recette

    return g, sans_conseil_recette(p)


def pesee_comme_gestion_mp(p: dict[str, Any]) -> dict[str, Any]:
    """Une pesée de PRO lue comme l'archive de Gestion MP (D4 § 2) : l'« attendu » de Gestion MP
    est ce à quoi la pesée est comparée — le BL (`compare_au = bl`), sinon le reste à livrer
    (`reste`), sinon rien (0) ; un écart sans comparaison (`null`) y valait 0."""
    vue = dict(p)
    if p.get("numero") == "Brouillon" and p.get("statut_reception") == "brouillon":
        vue["numero"] = f"brouillon n° {p.get('reception_id')}"  # RESTES3 : « Brouillon » à l'écran
    compare = p.get("compare_au")
    vue["quantite_attendue"] = (
        p.get("quantite_bl") if compare == "bl" else p.get("quantite_attendue") if compare else 0.0
    )
    if compare is None and p.get("ecart") is None:
        vue["ecart"] = 0.0
    return vue


def dossier_comme_gestion_mp(p: dict[str, Any]) -> dict[str, Any]:
    """Un dossier de PRO lu comme Gestion MP, qui portait **une** facture par dossier (lot
    PLUSIEURS-FACTURES, décision du 12/10/2026) : `facture` = la première de `factures`,
    `ecart_facture` = son rapprochement, `factures` = les numéros de ses pièces."""
    vue = dict(p)
    factures = p.get("factures")
    if not isinstance(factures, list) or (factures and not isinstance(factures[0], dict)):
        return vue
    premiere = factures[0] if factures else None
    vue["facture"] = premiere
    vue["ecart_facture"] = premiere.get("ecart") if premiere else None
    vue["factures"] = sorted(x["facture"] for x in p.get("pieces", []) if x.get("facture"))
    return vue


NOTE_CLOTURE = re.compile(r"(\s*·\s*)?cours du jour \S+ figé à la clôture du \d{2}/\d{2}/\d{4}")


def note_de_cloture(g: Any, p: Any) -> tuple[Any, Any]:
    """Le commentaire d'une marchandise : la note « cours du jour … figé à la clôture » de
    Gestion MP est, dans PRO, la marque `cours_origine = clos_au_jour` (D7 ; rien de métier
    dans du texte, MODELE-DONNEES § 11) ; le reste du texte est comparé."""
    if isinstance(g, str) and NOTE_CLOTURE.search(g):
        return NOTE_CLOTURE.sub("", g).strip(), p
    return g, p


def aujourdhui() -> date:
    """Le jour de l'usine (les deux serveurs tournent sur l'horloge réelle)."""
    return datetime.now(USINE).date()


def codes_du_stock(p: Any) -> tuple[Any, int]:
    """Les codes du stock de PRO (RESTES3 § 1.1 : `statut`, `statut_couverture` « CRITIQUE »,
    `action` « CREER_BC »/« AUCUNE », `relance` sans émoji) ramenés aux libellés de Gestion MP
    (`calcul.constantes.LIBELLES_GESTION_MP`, par `tests/moteur/jeux_outils.comme_gestion_mp`) :
    même valeur logique, autre forme. Rend la réponse traduite et le nombre de valeurs
    traduites ; une valeur inconnue reste telle quelle et l'écart se voit."""
    import sys
    from pathlib import Path

    tests = str(Path(__file__).resolve().parents[1] / "tests")
    if tests not in sys.path:
        sys.path.insert(0, tests)
    from moteur.jeux_outils import comme_gestion_mp

    rendu = comme_gestion_mp(p)
    return rendu, _differentes(p, rendu)


def _differentes(a: Any, b: Any) -> int:
    """Le nombre de feuilles qui diffèrent entre deux structures de même forme."""
    if isinstance(a, dict) and isinstance(b, dict):
        return sum(_differentes(a[k], b.get(k)) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return sum(_differentes(x, y) for x, y in zip(a, b, strict=False))
    return int(a != b)
