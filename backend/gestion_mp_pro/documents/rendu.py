"""Le rendu des documents imprimables : Jinja2, papier à en-tête de l'usine, A4 (ARCHITECTURE § 11).

Un seul environnement pour tous les documents (bon fournisseur, étiquettes, feuille de comptage,
bilan) : échappement automatique, gabarits de `documents/gabarits/`, filtres de
`documents/format.py` dans la langue du document. Le papier à en-tête est celui de l'usine
(décision A22 de Mohamed, repris de Gestion MP `achats.py` `en_tete_societe`, `pied_societe`) :
raison sociale en rouge avec grande initiale, secteur, forme juridique et capital, siège, ville,
téléphone ; pied : banques (séparées par « · » dans le réglage), ICE, R.C, N.I.F, C.N.S.S,
patente. Sans raison sociale réglée, un bandeau le dit **à l'écran seulement**.

Usage (un lot qui écrit un document) :

    from gestion_mp_pro.documents import rendu
    html = rendu.rendre("bon_commande.html", societe=rendu.societe(s), langue="en",
                        titre="BC-2026-0012", bon=donnees)
    return rendu.reponse(html)

Le gabarit commence par `{% extends "_papier_a_en_tete.html" %}` et remplit `{% block contenu %}`
(voir le gabarit pour les autres blocs : `style`, `pages`, `avant_pages`).
"""

from __future__ import annotations

import base64
import hashlib
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

from jinja2 import (
    Environment,
    FileSystemLoader,
    StrictUndefined,
    Template,
    pass_context,
    select_autoescape,
)
from jinja2.runtime import Context
from markupsafe import Markup
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.responses import HTMLResponse

from gestion_mp_pro.documents import format as fmt
from gestion_mp_pro.documents.format import Langue
from gestion_mp_pro.journalisation import CSP
from gestion_mp_pro.modeles import Parametre

GABARITS = Path(__file__).parent / "gabarits"

CLES_SOCIETE = (
    "nom_entreprise",
    "forme_juridique",
    "secteur",
    "adresse",
    "ville",
    "telephone",
    "banques",
    "ice",
    "rc",
    "identifiant_fiscal",
    "cnss",
    "patente",
)
"""Les réglages « Société » que porte le papier à en-tête (REGLAGES § 3.9)."""

IDENTIFIANTS_LEGAUX = (
    ("ice", "ICE"),
    ("rc", "R.C"),
    ("identifiant_fiscal", "N.I.F"),
    ("cnss", "C.N.S.S"),
    ("patente", "PATENTE"),
)
"""Le pied du papier, dans l'ordre du papier de l'usine (Gestion MP `IDENTIFIANTS_LEGAUX`)."""

LIBELLES: dict[str, dict[str, str]] = {
    "fr": {"siege": "SIÈGE SOCIAL", "banques": "BANQUES"},
    "en": {"siege": "HEAD OFFICE", "banques": "BANKS"},
}
"""Les mots du papier à en-tête selon la langue du document (le bon fournisseur est anglais)."""

SCRIPT_IMPRIMER = (
    'document.getElementById("imprimer").addEventListener("click", function () { print(); });'
)
"""Le seul script d'un document : le bouton « Imprimer » (permis par son empreinte, CSP)."""


def _empreinte(script: str) -> str:
    """L'empreinte CSP d'un script en ligne (`'sha256-…'`)."""
    return "'sha256-" + base64.b64encode(hashlib.sha256(script.encode()).digest()).decode() + "'"


CSP_DOCUMENT = CSP.replace(
    "default-src 'self';", f"default-src 'self'; script-src {_empreinte(SCRIPT_IMPRIMER)};"
)
"""La politique de l'application, plus le script du bouton « Imprimer », et rien d'autre."""


@dataclass(frozen=True)
class Societe:
    """Ce que dit le papier à en-tête de l'usine (lignes vides omises à l'impression)."""

    nom: str = ""
    forme_juridique: str = ""
    secteur: str = ""
    adresse: str = ""
    ville: str = ""
    telephone: str = ""
    banques: tuple[str, ...] = ()
    identifiants: tuple[tuple[str, str], ...] = ()

    @property
    def reglee(self) -> bool:
        """La raison sociale est-elle réglée ? (sinon : bandeau « En-tête non réglé » à l'écran)."""
        return bool(self.nom)


def societe_de(valeurs: Mapping[str, str]) -> Societe:
    """Le papier à en-tête depuis les réglages `{clé: valeur}` (espaces retirés)."""
    v = {cle: (valeurs.get(cle) or "").strip() for cle in CLES_SOCIETE}
    return Societe(
        nom=v["nom_entreprise"],
        forme_juridique=v["forme_juridique"],
        secteur=v["secteur"],
        adresse=v["adresse"],
        ville=v["ville"],
        telephone=v["telephone"],
        banques=tuple(b.strip() for b in v["banques"].split("·") if b.strip()),
        identifiants=tuple((lib, v[cle]) for cle, lib in IDENTIFIANTS_LEGAUX if v[cle]),
    )


def societe(s: Session) -> Societe:
    """Le papier à en-tête de l'usine, lu dans les réglages « Société »."""
    lignes = s.execute(
        select(Parametre.cle, Parametre.valeur).where(Parametre.cle.in_(CLES_SOCIETE))
    )
    return societe_de({cle: valeur for cle, valeur in lignes})


def _filtre(fonction: Callable[..., str]) -> Callable[..., str]:
    """Un filtre Jinja qui écrit dans la langue du document (`langue` du contexte)."""

    @pass_context
    def filtre(contexte: Context, valeur: Any, *args: Any) -> str:
        """La fonction de `format`, dans la langue du document."""
        return fonction(valeur, *args, langue=contexte.get("langue", "fr"))

    return filtre


@cache
def environnement() -> Environment:
    """L'environnement Jinja2 des documents (échappement automatique, variables exigées)."""
    env = Environment(
        loader=FileSystemLoader(GABARITS),
        autoescape=select_autoescape(enabled_extensions=("html",), default_for_string=True),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=False,
    )
    env.filters.update(
        nombre=_filtre(fmt.nombre),
        kg=_filtre(fmt.kg),
        kg_entier=_filtre(fmt.kg_entier),
        m2=_filtre(fmt.m2),
        date=_filtre(fmt.jour),
        horodatage=fmt.horodatage,
        montant=fmt.montant,
        montant_precis=fmt.montant_precis,
        prix=fmt.prix,
        cours=fmt.cours,
        pourcent=fmt.pourcent,
        part=fmt.part,
    )
    env.globals.update(VIDE=fmt.VIDE)
    return env


def script_imprimer() -> Markup:
    """Le script du bouton « Imprimer » (`<script>{{ script_imprimer }}</script>`)."""
    return Markup(SCRIPT_IMPRIMER)  # noqa: S704 — constante du module, permise par son empreinte


def rendre(
    gabarit: str | Template,
    *,
    societe: Societe,
    titre: str,
    langue: Langue = "fr",
    paysage: bool = False,
    **donnees: Any,
) -> str:
    """Le document HTML complet : le gabarit (nom dans `gabarits/`, ou modèle déjà compilé par
    `environnement().from_string`) sur le papier à en-tête, dans la langue voulue."""
    return (
        environnement()
        .get_template(gabarit)
        .render(
            societe=societe,
            titre=titre,
            langue=langue,
            mots=LIBELLES[langue],
            paysage=paysage,
            script_imprimer=script_imprimer(),
            **donnees,
        )
    )


def reponse(html: str, statut: int = 200) -> HTMLResponse:
    """Un document à ouvrir dans un onglet (`inline`), avec la politique qui permet « Imprimer »."""
    return HTMLResponse(
        html,
        status_code=statut,
        headers={"Content-Disposition": "inline", "Content-Security-Policy": CSP_DOCUMENT},
    )


REPONSES_HTML: dict[int | str, dict[str, Any]] = {200: {"content": {"text/html": {}}}}
"""À fusionner dans les `responses` d'une route de document (OpenAPI : du HTML, pas du JSON)."""
