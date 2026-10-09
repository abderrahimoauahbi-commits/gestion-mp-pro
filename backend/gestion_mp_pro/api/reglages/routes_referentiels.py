"""Routes 31–42 du domaine « Réglages » : magasins, postes de frais, codes douaniers, motifs.

Inscrites sur le routeur de `routes.py` (même étiquette OpenAPI, même domaine).
"""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal

from fastapi import Response

from gestion_mp_pro.api.dependances import SessionDep, VersionDep
from gestion_mp_pro.api.erreurs import reponses
from gestion_mp_pro.api.reglages.routes import routeur
from gestion_mp_pro.api.reglages.schemas import (
    CodeDouanierCreation,
    CodeDouanierFiche,
    CodeDouanierModification,
    Libelle,
    MagasinCreation,
    MagasinFiche,
    MagasinModification,
    MotifLu,
    Motifs,
    PosteCreation,
    PosteFiche,
    PosteModification,
    TypeOperationLu,
)
from gestion_mp_pro.modeles import CodeDouanier, Magasin, PosteFrais
from gestion_mp_pro.securite import A, C, D, QuiDep, droit
from gestion_mp_pro.services import postes_frais as postes
from gestion_mp_pro.services import referentiels

SANS_CORPS = {"status_code": 204, "response_class": Response}


def _magasin(g: Magasin, detenus: Mapping[int, Decimal]) -> MagasinFiche:
    """La fiche d'un magasin."""
    return MagasinFiche(
        id=g.id,
        code=g.code,
        nom=g.nom,
        type=g.type,
        contenu=g.contenu,
        actif=g.actif,
        kg_detenus=float(detenus.get(g.id, Decimal(0))),
        version=g.version,
    )


@routeur.get(
    "/magasins",
    response_model=list[MagasinFiche],
    dependencies=[droit(*C)],
    summary="Les magasins (courants et quarantaines) et les kilos qu'ils détiennent.",
    responses=reponses(401, 403),
)
def lire_magasins(s: SessionDep) -> list[MagasinFiche]:
    """Route 31."""
    detenus = referentiels.detenus(s)
    return [_magasin(g, detenus) for g in referentiels.magasins(s)]


@routeur.post(
    "/magasins",
    response_model=MagasinFiche,
    status_code=201,
    dependencies=[droit(D)],
    summary="Créer un magasin.",
    responses=reponses(401, 403, 409, 422),
)
def creer_magasin(corps: MagasinCreation, qui: QuiDep, s: SessionDep) -> MagasinFiche:
    """Route 32."""
    g = referentiels.creer_magasin(s, qui, referentiels.MagasinSaisi(**corps.model_dump()))
    return _magasin(g, {})


@routeur.put(
    "/magasins/{ident}",
    response_model=MagasinFiche,
    dependencies=[droit(D)],
    summary="Modifier un magasin (ni désactivé ni retypé s'il détient de la matière).",
    responses=reponses(401, 403, 404, 409, 422),
)
def modifier_magasin(
    ident: int, corps: MagasinModification, qui: QuiDep, s: SessionDep
) -> MagasinFiche:
    """Route 33."""
    champs = corps.model_dump(exclude={"version"})
    g = referentiels.modifier_magasin(
        s, qui, ident, referentiels.MagasinSaisi(**champs), corps.version
    )
    return _magasin(g, referentiels.detenus(s))


def _poste(p: PosteFrais, u: postes.Usage, figees: int | None = None) -> PosteFiche:
    """La fiche d'un poste et son usage."""
    return PosteFiche(
        id=p.id,
        code=p.code,
        libelle=p.libelle,
        recuperable=p.recuperable,
        nature=p.nature,
        entre_valeur_douane=p.entre_valeur_douane,
        cle=p.cle,
        ordre=p.ordre,
        systeme=p.systeme,
        frais_ouverts=u.frais_ouverts,
        frais_clos=u.frais_clos,
        dossiers_ouverts=u.dossiers_ouverts,
        dossiers_clos=u.dossiers_clos,
        utilise=bool(u.frais),
        version=p.version,
        parts_figees=figees,
    )


@routeur.get(
    "/postes-frais",
    response_model=list[PosteFiche],
    dependencies=[droit(D, A)],
    summary="Les postes de frais d'importation, leur clé et leur usage.",
    responses=reponses(401, 403),
)
def lire_postes(s: SessionDep) -> list[PosteFiche]:
    """Route 34."""
    u = postes.usages(s)
    return [_poste(p, u.get(p.id, postes.Usage())) for p in postes.postes(s)]


@routeur.post(
    "/postes-frais",
    response_model=PosteFiche,
    status_code=201,
    dependencies=[droit(D)],
    summary="Créer un poste de frais.",
    responses=reponses(401, 403, 409, 422),
)
def creer_poste(corps: PosteCreation, qui: QuiDep, s: SessionDep) -> PosteFiche:
    """Route 35."""
    saisi = postes.PosteSaisi(**corps.model_dump(exclude={"code"}))
    return _poste(postes.creer(s, qui, corps.code, saisi), postes.Usage())


@routeur.put(
    "/postes-frais/{ident}",
    response_model=PosteFiche,
    dependencies=[droit(D)],
    summary="Modifier un poste : changer sa clé fige la répartition des dossiers clos.",
    responses=reponses(401, 403, 404, 409, 422),
)
def modifier_poste(ident: int, corps: PosteModification, qui: QuiDep, s: SessionDep) -> PosteFiche:
    """Route 36 : `parts_figees` dit combien de dossiers clos gardent leur répartition."""
    saisi = postes.PosteSaisi(**corps.model_dump(exclude={"version"}))
    figees = postes.modifier(s, qui, ident, saisi, corps.version)
    p = postes.poste(s, ident)
    return _poste(p, postes.usages(s).get(ident, postes.Usage()), figees)


@routeur.delete(
    "/postes-frais/{ident}",
    dependencies=[droit(D)],
    summary="Supprimer un poste ni système ni porté par un frais.",
    responses=reponses(401, 403, 404, 409, 422),
    **SANS_CORPS,
)
def supprimer_poste(ident: int, version: VersionDep, qui: QuiDep, s: SessionDep) -> Response:
    """Route 37."""
    postes.supprimer(s, qui, ident, version)
    return Response(status_code=204)


def _code(c: CodeDouanier, matieres: dict[int, int]) -> CodeDouanierFiche:
    """La fiche d'un code douanier."""
    return CodeDouanierFiche(
        id=c.id,
        code=c.code,
        libelle=c.libelle,
        taux_droits=float(c.taux_droits),
        actif=c.actif,
        nb_matieres=matieres.get(c.id, 0),
        version=c.version,
    )


@routeur.get(
    "/codes-douaniers",
    response_model=list[CodeDouanierFiche],
    dependencies=[droit(D, A)],
    summary="Les codes douaniers, leur taux de droits et le nombre de matières qui les portent.",
    responses=reponses(401, 403),
)
def lire_codes(s: SessionDep) -> list[CodeDouanierFiche]:
    """Route 38."""
    matieres = referentiels.matieres_par_code(s)
    return [_code(c, matieres) for c in referentiels.codes_douaniers(s)]


@routeur.post(
    "/codes-douaniers",
    response_model=CodeDouanierFiche,
    status_code=201,
    dependencies=[droit(D)],
    summary="Créer un code douanier.",
    responses=reponses(401, 403, 409, 422),
)
def creer_code(corps: CodeDouanierCreation, qui: QuiDep, s: SessionDep) -> CodeDouanierFiche:
    """Route 39."""
    c = referentiels.creer_code(s, qui, referentiels.CodeSaisi(**corps.model_dump()))
    return _code(c, {})


@routeur.put(
    "/codes-douaniers/{ident}",
    response_model=CodeDouanierFiche,
    dependencies=[droit(D)],
    summary="Modifier un code douanier (le code lui-même se corrige).",
    responses=reponses(401, 403, 404, 409, 422),
)
def modifier_code(
    ident: int, corps: CodeDouanierModification, qui: QuiDep, s: SessionDep
) -> CodeDouanierFiche:
    """Route 40."""
    saisi = referentiels.CodeSaisi(**corps.model_dump(exclude={"version"}))
    c = referentiels.modifier_code(s, qui, ident, saisi, corps.version)
    return _code(c, referentiels.matieres_par_code(s))


@routeur.delete(
    "/codes-douaniers/{ident}",
    dependencies=[droit(D)],
    summary="Supprimer un code douanier que nulle matière ne porte.",
    responses=reponses(401, 403, 404, 409, 422),
    **SANS_CORPS,
)
def supprimer_code(ident: int, qui: QuiDep, s: SessionDep, version: int | None = None) -> Response:
    """Route 41 : `?version=` facultatif (contrôlé s'il est donné)."""
    referentiels.supprimer_code(s, qui, ident, version)
    return Response(status_code=204)


@routeur.get(
    "/motifs",
    response_model=Motifs,
    dependencies=[droit(*C)],
    summary="Types d'opération et leurs rôles, motifs de mouvement, motifs de réclamation.",
    responses=reponses(401, 403),
)
def lire_motifs(s: SessionDep) -> Motifs:
    """Route 42 : une seule source pour les listes fermées de l'écran."""
    return Motifs(
        types=[
            TypeOperationLu(type=t, libelle=libelle, roles=[str(r) for r in roles])
            for t, (libelle, roles) in referentiels.TYPES_MOTIF.items()
        ],
        motifs=[
            MotifLu(
                id=m.id,
                type=m.type_operation,
                libelle=m.libelle,
                code_r=m.code_r,
                impose_role=m.impose_role,
            )
            for m in referentiels.motifs(s)
        ],
        reclamation_motifs=[
            Libelle(code=c, libelle=x) for c, x in referentiels.MOTIFS_RECLAMATION.items()
        ],
        reclamation_issues=[
            Libelle(code=c, libelle=x) for c, x in referentiels.ISSUES_RECLAMATION.items()
        ],
    )
