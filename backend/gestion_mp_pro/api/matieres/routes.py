"""Routes du domaine « Matières » (API-PRO § 1.9, routes 70–81).

Les chemins fixes (`/matieres/reference`, `/classement`, `/tableur…`) sont déclarés avant
`/matieres/{ident}`.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, File, Form, Query, Response, UploadFile

from gestion_mp_pro.api.communs import nouveau_routeur
from gestion_mp_pro.api.dependances import SessionDep
from gestion_mp_pro.api.erreurs import Refus, reponses
from gestion_mp_pro.api.matieres.schemas import (
    ApercuClassement,
    ApercuImport,
    ClassementEntree,
    LigneImport,
    MatiereCreation,
    MatiereFiche,
    MatiereModification,
    MatiereResume,
    ReferenceComposee,
    ResultatImport,
)
from gestion_mp_pro.exports import referentiels as classeurs
from gestion_mp_pro.securite import A, C, D, QuiDep, droit, peut
from gestion_mp_pro.services import classement, matieres, tableur_matieres
from gestion_mp_pro.services import matieres_lecture as lecture

routeur = nouveau_routeur("matieres")
SANS_CORPS = {"status_code": 204, "response_class": Response}
XLSX = {200: {"content": {classeurs.TYPE_XLSX: {}}, "description": "Classeur Excel"}}
TAILLE_MAX = 10 * 1024 * 1024
"""Un tableur du catalogue : 10 Mo au plus."""


def _filtres(
    q: Annotated[str | None, Query(max_length=200, description="mots, sans accents")] = None,
    role: Annotated[int | None, Query(ge=1)] = None,
    fournisseur: Annotated[int | None, Query(ge=1)] = None,
    actif: bool | None = None,
) -> lecture.Filtres:
    """Les filtres de la liste (et de son export)."""
    return lecture.Filtres(q=q, role=role, fournisseur=fournisseur, actif=actif)


FiltresDep = Annotated[lecture.Filtres, Depends(_filtres)]


def _pour(qui: QuiDep, ligne: lecture.Ligne) -> lecture.Ligne:
    """L'alimentation ne lit ni la devise, ni l'unité du prix, ni le minimum de commande."""
    return ligne if peut(qui, "voir_prix") else lecture.sans_achat(ligne)


def _xlsx(contenu: bytes, nom: str) -> Response:
    """Un classeur en pièce jointe."""
    return Response(
        contenu,
        media_type=classeurs.TYPE_XLSX,
        headers={"Content-Disposition": f'attachment; filename="{nom}"'},
    )


@routeur.get(
    "/matieres",
    response_model=list[MatiereResume],
    dependencies=[droit(*C)],
    summary="Le catalogue des matières (prix retirés pour l'alimentation).",
    responses=reponses(401, 403, 422),
)
def lister(qui: QuiDep, s: SessionDep, f: FiltresDep) -> list[MatiereResume]:
    """Route 70 : tout le catalogue, trié par référence ; `q` : tous les mots."""
    lignes = lecture.lister(s, f)
    return [MatiereResume.model_validate(_pour(qui, x), from_attributes=True) for x in lignes]


@routeur.get(
    "/matieres/reference",
    response_model=ReferenceComposee,
    dependencies=[droit(*C)],
    summary="La référence composée de la classification (saisie semi-automatique).",
    responses=reponses(401, 403, 422),
)
def reference(
    s: SessionDep,
    *,
    composition_id: Annotated[int | None, Query(ge=1)] = None,
    type_fil_id: Annotated[int | None, Query(ge=1)] = None,
    titrage_id: Annotated[int | None, Query(ge=1)] = None,
    couleur_id: Annotated[int | None, Query(ge=1)] = None,
    couleur_code: Annotated[str, Query(max_length=32)] = "",
    suffixe: Annotated[str, Query(max_length=16)] = "",
) -> ReferenceComposee:
    """Route 75 : `existe` dit si une matière porte déjà cette référence."""
    r = lecture.composer(
        s,
        composition_id=composition_id,
        type_fil_id=type_fil_id,
        titrage_id=titrage_id,
        couleur_id=couleur_id,
        couleur_code=couleur_code,
        suffixe=suffixe,
    )
    return ReferenceComposee.model_validate(r, from_attributes=True)


@routeur.get(
    "/matieres/classement",
    response_model=ApercuClassement,
    dependencies=[droit(D, A)],
    summary="Ce que le classement automatique déduirait des références (rien n'est écrit).",
    responses=reponses(401, 403),
)
def apercu_classement(s: SessionDep) -> ApercuClassement:
    """Route 76."""
    return ApercuClassement.model_validate(classement.apercu(s), from_attributes=True)


@routeur.post(
    "/matieres/classement",
    response_model=ApercuClassement,
    dependencies=[droit(D, A)],
    summary="Classer les matières choisies, à leur version lue.",
    responses=reponses(401, 403, 404, 409, 422),
)
def appliquer_classement(corps: ClassementEntree, qui: QuiDep, s: SessionDep) -> ApercuClassement:
    """Route 77 : une valeur déjà renseignée n'est jamais écrasée."""
    fait = classement.appliquer(s, qui, corps.ids, corps.versions)
    return ApercuClassement.model_validate(fait, from_attributes=True)


@routeur.get(
    "/matieres/tableur",
    dependencies=[droit(D, A)],
    summary="Le modèle du tableur : le catalogue actuel (feuille « Matières »).",
    responses={**reponses(401, 403), **XLSX},
    response_class=Response,
)
def modele_tableur(s: SessionDep) -> Response:
    """Route 78 : + colonnes « Priorité dans le groupe », « Vider », « Version »."""
    return _xlsx(classeurs.modele_tableur(lecture.lister(s)), "matieres.xlsx")


async def _contenu(fichier: UploadFile) -> bytes:
    """Le fichier reçu, 10 Mo au plus."""
    contenu = await fichier.read(TAILLE_MAX + 1)
    if len(contenu) > TAILLE_MAX:
        raise Refus.saisie("Fichier trop lourd (10 Mo au plus).", code="fichier_trop_gros")
    return contenu


def _apercu(a: tableur_matieres.Apercu) -> dict[str, object]:
    """L'aperçu en clair : lignes, compteurs, empreinte."""
    return {
        "lignes": [LigneImport.model_validate(x, from_attributes=True) for x in a.lignes],
        "creees": a.compte("nouvelle"),
        "modifiees": a.compte("modifiee"),
        "inchangees": a.compte("inchangee"),
        "erreurs": a.compte("erreur"),
        "appliquable": a.appliquable,
        "empreinte_apercu": a.empreinte,
    }


@routeur.post(
    "/matieres/tableur/apercu",
    response_model=ApercuImport,
    dependencies=[droit(D, A)],
    summary="Relire un tableur : ce qui serait créé, modifié, et ce qui ne va pas.",
    responses=reponses(401, 403, 422),
)
async def apercu_tableur(fichier: Annotated[UploadFile, File()], s: SessionDep) -> ApercuImport:
    """Route 79 : rien n'est écrit."""
    contenu = await _contenu(fichier)
    return ApercuImport(**_apercu(tableur_matieres.apercu(s, contenu)))  # type: ignore[arg-type]


@routeur.post(
    "/matieres/tableur/appliquer",
    response_model=ResultatImport,
    dependencies=[droit(D, A)],
    summary="Appliquer le tableur, tout ou rien, s'il dit encore ce que l'aperçu a montré.",
    responses=reponses(401, 403, 409, 422),
)
async def appliquer_tableur(
    fichier: Annotated[UploadFile, File()],
    empreinte_apercu: Annotated[str, Form(min_length=1, max_length=64)],
    qui: QuiDep,
    s: SessionDep,
) -> ResultatImport:
    """Route 80 : 409 si une matière a changé depuis l'aperçu."""
    contenu = await _contenu(fichier)
    fait = tableur_matieres.appliquer(s, qui, contenu, empreinte_apercu)
    return ResultatImport(**_apercu(fait))  # type: ignore[arg-type]


@routeur.get(
    "/export/matieres",
    dependencies=[droit(D, A)],
    summary="Le catalogue en classeur Excel (avec les filtres de la liste).",
    responses={**reponses(401, 403, 422), **XLSX},
    response_class=Response,
)
def exporter(s: SessionDep, f: FiltresDep) -> Response:
    """Route 81 : classification, achat, conditionnement, stock."""
    lignes = lecture.lister(s, f)
    return _xlsx(classeurs.matieres(lignes), classeurs.nom_de_fichier("matieres"))


@routeur.get(
    "/matieres/{ident}",
    response_model=MatiereFiche,
    dependencies=[droit(*C)],
    summary="La fiche d'une matière et ses traces.",
    responses=reponses(401, 403, 404, 422),
)
def lire(ident: int, qui: QuiDep, s: SessionDep) -> MatiereFiche:
    """Route 71."""
    return MatiereFiche.model_validate(_pour(qui, lecture.lire(s, ident)), from_attributes=True)


@routeur.post(
    "/matieres",
    response_model=MatiereFiche,
    status_code=201,
    dependencies=[droit(D, A)],
    summary="Créer une matière.",
    responses=reponses(401, 403, 409, 422),
)
def creer(corps: MatiereCreation, qui: QuiDep, s: SessionDep) -> MatiereFiche:
    """Route 72."""
    m = matieres.creer(s, qui, corps.model_dump())
    return MatiereFiche.model_validate(lecture.lire(s, m.id), from_attributes=True)


@routeur.put(
    "/matieres/{ident}",
    response_model=MatiereFiche,
    dependencies=[droit(D, A)],
    summary="Modifier une matière (la fiche entière, à sa version lue).",
    responses=reponses(401, 403, 404, 409, 422),
)
def modifier(ident: int, corps: MatiereModification, qui: QuiDep, s: SessionDep) -> MatiereFiche:
    """Route 73 : désactiver ne revalide que ce qui change."""
    matieres.modifier(s, qui, ident, corps.model_dump(exclude={"version"}), corps.version)
    return MatiereFiche.model_validate(lecture.lire(s, ident), from_attributes=True)


@routeur.delete(
    "/matieres/{ident}",
    dependencies=[droit(D, A)],
    summary="Supprimer une matière sans aucune trace (sinon la désactiver).",
    responses=reponses(401, 403, 404, 409, 422),
    **SANS_CORPS,
)
def supprimer(ident: int, qui: QuiDep, s: SessionDep, version: int | None = None) -> Response:
    """Route 74 : `?version=` facultatif (contrôlé s'il est donné)."""
    matieres.supprimer(s, qui, ident, version)
    return Response(status_code=204)
