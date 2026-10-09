"""Le rapport Markdown de la comparaison avec Gestion MP (lot C1 ; ARCHITECTURE § 14.3).

`resultat-comparaison-<date>.md` : volumes, versions des deux logiciels, contrôle « même
base », puis par section — valeurs comparées, écarts expliqués par classe (ampleur maximale),
à corriger ; le détail des écarts à corriger ; le verdict (code de sortie 0 si « à corriger :
0 »). Le même rapport alimente `docs/COMPARAISON-GESTION-MP.md`.
"""

from __future__ import annotations

from datetime import datetime

from comparaison import Resultat
from parite_rapport import CORRECTIONS

TITRE_SOURCE = {
    "gestion_mp": "Production de Gestion MP (référentiels réels, sa commande réelle)",
    "gestion_mp_comparaison": "Année d'essai simulée (import de l'ERP Fil)",
}


def _ampleur(details: list[tuple[str, str, object, object]]) -> str:
    """Un aperçu du premier écart à corriger (sinon vide)."""
    return "" if not details else f" (ex. {details[0][0]} · {details[0][1]})"


def entete(r: Resultat) -> list[str]:
    """Le titre, la date, les versions, et le contrôle « même base »."""
    titre = TITRE_SOURCE.get(r.source, r.source)
    lignes = [
        f"# Comparaison avec Gestion MP — {titre}",
        "",
        f"- Faite le **{datetime.now().astimezone():%Y-%m-%d %H:%M}**, mode **{r.mode}**.",
        f"- Gestion MP servi : `{r.versions.get('gestion_mp', '?')}` · "
        f"Gestion MP PRO : `{r.versions.get('pro', '?')}`.",
        f"- Source : `{r.source}` (copie en lecture seule) → base PRO reprise ; "
        f"{len(r.dates)} date(s) : {', '.join(r.dates)}.",
        f"- Empreinte de `gestion_mp` et de la source : "
        f"{'inchangées' if r.prep.source_intacte else '**MODIFIÉES PENDANT LA COMPARAISON**'} "
        "(aucune écriture).",
    ]
    etat = "resynchronisée (reprise rejouée sur la copie)" if r.prep.resynchronisee else "identique"
    lignes.append(
        f"- Même base : signature de la copie `{r.prep.signature_copie[:16]}…` = signature de la "
        f"dernière reprise de PRO `{r.prep.signature_pro[:16]}…` — **{etat}**."
    )
    return lignes


def tableau(r: Resultat) -> list[str]:
    """Le tableau par section : comparées, expliquées par classe, à corriger."""
    lignes = [
        "",
        "## Chiffre par chiffre, par section",
        "",
        "| Section | Valeurs comparées | Expliquées (classe) | À corriger |",
        "| --- | ---: | --- | ---: |",
    ]
    for section in sorted(r.sections):
        compte = r.sections[section]
        classes = ", ".join(
            f"{k} {n}"
            for k, n in sorted(compte.items())
            if k not in ("comparées", "à corriger", "moteur à corriger")
        )
        a_corriger = compte.get("à corriger", 0) + compte.get("moteur à corriger", 0)
        lignes.append(
            f"| {section} | {compte.get('comparées', 0)} | {classes or '—'} | "
            f"{'**' + str(a_corriger) + '**' if a_corriger else '0'} |"
        )
    return lignes


def details(r: Resultat, maxi: int = 50) -> list[str]:
    """Le détail des écarts à corriger (en clair)."""
    if not r.details:
        return []
    lignes = ["", "## Écarts à corriger (détail)", ""]
    for lieu, champ, g, p in r.details[:maxi]:
        lignes.append(f"- `{lieu}` · {champ} : Gestion MP `{str(g)[:80]}` / PRO `{str(p)[:80]}`")
    if len(r.details) > maxi:
        lignes.append(f"- … et {len(r.details) - maxi} autre(s).")
    return lignes


def corrections(r: Resultat) -> list[str]:
    """Les corrections et traductions déclarées rencontrées, avec leur compte et leur raison."""
    expliquees = r.expliquees
    if not expliquees:
        return []
    lignes = ["", "## Différences voulues rencontrées (corrections et traductions déclarées)", ""]
    for code, texte in CORRECTIONS.items():
        if expliquees.get(code):
            lignes.append(f"- **{code}** ({expliquees[code]}) — {texte}")
    for code, n in sorted(expliquees.items()):
        if code not in CORRECTIONS:
            lignes.append(f"- **{code}** ({n}) — forme déclarée.")
    return lignes


def verdict(r: Resultat) -> list[str]:
    """Le verdict : total comparé, expliqué, à corriger."""
    expliquees = sum(r.expliquees.values())
    lignes = [
        "",
        "## Verdict",
        "",
        f"- Valeurs comparées : **{r.comparees}**.",
        f"- Écarts expliqués (différences voulues) : **{expliquees}**.",
        f"- **À corriger : {r.a_corriger}**{_ampleur(r.details)}.",
    ]
    if r.fautes:
        lignes += [
            "",
            "### Essai de sensibilité (fautes injectées dans PRO)",
            "",
            "Le comparateur doit voir chacune :",
            *[f"- {f}" for f in r.fautes],
            f"\n→ à corriger relevé : **{r.a_corriger}** "
            f"({'vu' if r.a_corriger >= len(r.fautes) else 'MANQUÉ'}).",
        ]
    return lignes


def rediger(r: Resultat) -> str:
    """Le rapport Markdown complet."""
    lignes = entete(r) + tableau(r) + corrections(r) + details(r) + verdict(r) + [""]
    return "\n".join(lignes)


def fusionner(*resultats: Resultat) -> str:
    """Plusieurs résultats (modes, sources) dans un seul document."""
    return "\n\n---\n\n".join(rediger(r) for r in resultats)
