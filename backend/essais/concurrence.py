"""Courses de concurrence rejouées contre un **vrai serveur** (PLAN-DE-RECETTE-PRO § 11.3, A10).

    export GESTIONMPPRO_BASE=postgresql+psycopg:///gestion_mp_pro_v4_concurrence_essai
    export GESTIONMPPRO_BASE_ESSAI=$GESTIONMPPRO_BASE
    .venv/bin/python essais/concurrence.py          # réécrit essais/resultat-concurrence.txt

Ce script est le pendant « vrai serveur » de `tests/test_concurrence.py` : il lance uvicorn
(processus d'ARCHITECTURE) sur une base `*_essai` neuve, puis rejoue **50 fois** les courses des
bons de commande que le reste du logiciel ne tenait pas — plusieurs postes qui agissent au même
instant, départ synchronisé par une barrière :

- deux envois du même bon : un seul numéro, l'autre refusé (409) ;
- deux approbations du même bon : un seul départ ;
- deux enregistrements d'une même fiche : le verrou de version refuse le perdant ;
- vingt envois simultanés de la même série : vingt numéros consécutifs, sans trou ni doublon.

À la fin : la série BC n'a ni trou ni doublon sur toute la base, et `/api/controles/soldes` est
conforme (soldes = journal, aucun négatif). Les autres courses du § 11.3 (stock, réceptions,
ordres, importations, connexions, restauration, cache à deux processus) sont tenues par la
suite pytest, que `test_concurrence.test_les_courses_du_plan_sont_toutes_eprouvees` recense.

La base d'essai est supprimée à la fin ; aucun serveur n'est laissé ouvert (`with`).
"""

from __future__ import annotations

import os
import sys
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

RACINE_BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE_BACKEND / "tests"))

from sqlalchemy import create_engine, select, text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

REPETITIONS = 50
SORTIE = RACINE_BACKEND / "essais" / "resultat-concurrence.txt"


def _garde_fou() -> str:
    """L'adresse de la base d'essai (défaut `…_concurrence_essai`) ; refuse tout hors `_essai`."""
    adresse = os.environ.get(
        "GESTIONMPPRO_BASE_ESSAI", "postgresql+psycopg:///gestion_mp_pro_concurrence_essai"
    )
    nom = make_url(adresse).database or ""
    if not nom.endswith("_essai"):
        raise SystemExit(f"Base refusée : « {nom} » ne finit pas par _essai.")
    os.environ["GESTIONMPPRO_BASE"] = adresse
    os.environ["GESTIONMPPRO_BASE_ESSAI"] = adresse
    os.environ["GESTIONMPPRO_TACHES"] = "0"
    return adresse


def _maintenance(adresse: str) -> object:
    cible = make_url(adresse).set(database="postgres")
    return create_engine(cible, poolclass=NullPool, isolation_level="AUTOCOMMIT")


def preparer_base(adresse: str) -> None:
    """Supprime puis recrée la base, et applique les migrations (schéma + semences)."""
    nom = make_url(adresse).database
    moteur = _maintenance(adresse)
    with moteur.connect() as c:  # type: ignore[attr-defined]
        c.execute(text(f'DROP DATABASE IF EXISTS "{nom}" WITH (FORCE)'))
        c.execute(text(f'CREATE DATABASE "{nom}"'))
    moteur.dispose()  # type: ignore[attr-defined]
    from gestion_mp_pro.services.installation import migrer

    migrer()


@dataclass
class Decor:
    """Le fournisseur d'essai et des matières prêtes (références → id)."""

    fournisseur_id: int
    matieres: list[int]


def semer(nombre_matieres: int) -> Decor:
    """Un fournisseur et `nombre_matieres` matières (fabriques du lot D1)."""
    from fabriques.referentiels import fournisseur, matiere

    fid = fournisseur(devise="MAD", delai_jours=30)
    ids = [
        matiere(f"CONC-{i}", fournisseur_id=fid, prix="50", devise="MAD")
        for i in range(nombre_matieres)
    ]
    return Decor(fid, ids)


def _seuil(adresse: str, valeur: str) -> None:
    """Pose le seuil d'approbation (le serveur le relit à chaque requête)."""
    moteur = create_engine(adresse, poolclass=NullPool)
    with moteur.begin() as c:
        c.execute(
            text("UPDATE parametre SET valeur = :v, version = version + 1 WHERE cle = :c"),
            {"v": valeur, "c": "seuil_approbation"},
        )
    moteur.dispose()


@dataclass
class Rapport:
    """Le compte-rendu d'une course rejouée."""

    titre: str
    tours: int
    anomalies: list[str] = field(default_factory=list)

    @property
    def tenue(self) -> bool:
        """Vrai si la course n'a relevé aucune anomalie."""
        return not self.anomalies

    def ligne(self) -> str:
        """La ligne de verdict de la course (état, titre, premières anomalies)."""
        etat = "TENUE" if self.tenue else "ROMPUE"
        details = "" if self.tenue else " — " + " ; ".join(self.anomalies[:3])
        return f"[{etat}] {self.titre} ({self.tours} fois){details}"


def _ensemble(serveur: object, appels: list[Callable[[], int]]) -> list[int]:
    """Lance les appels au même instant (barrière) ; rend leurs codes, triés."""
    depart = threading.Barrier(len(appels))
    codes: list[int] = [0] * len(appels)

    def courir(rang: int) -> None:
        depart.wait()
        codes[rang] = appels[rang]()

    fils = [threading.Thread(target=courir, args=(i,)) for i in range(len(appels))]
    for f in fils:
        f.start()
    for f in fils:
        f.join(timeout=60)
    return sorted(codes)


class Postes:
    """Des postes HTTP connectés au serveur, par rôle (sessions distinctes)."""

    def __init__(self, serveur: object) -> None:
        self._serveur = serveur
        self._par_role: dict[str, list[object]] = {}

    def de(self, role: str, n: int) -> list[object]:
        """`n` postes de ce rôle, connectés une fois puis réutilisés."""
        manque = n - len(self._par_role.setdefault(role, []))
        self._par_role[role] += [self._serveur.poste(role) for _ in range(max(0, manque))]  # type: ignore[attr-defined]
        return self._par_role[role][:n]


def _brouillon(poste: object, decor: Decor, matiere_id: int, kg: int = 100) -> dict[str, object]:
    """Un brouillon de bon créé par le poste (première fiche rendue)."""
    corps = {
        "fournisseur_id": decor.fournisseur_id,
        "lignes": [{"matiere_id": matiere_id, "quantite": kg}],
    }
    cree = poste.ok("POST", "/api/commandes", corps)  # type: ignore[attr-defined]
    return cree[0]


def _gestes(postes: list[object], chemin: str, version: int) -> list[Callable[[], int]]:
    """Un appel POST par poste sur `chemin`, avec la même `version` (paramètres liés : pas de
    capture de variable de boucle)."""
    return [lambda p=p: p.appeler("POST", chemin, {"version": version})[0] for p in postes]  # type: ignore[attr-defined]


def course_double_envoi(serveur: object, postes: Postes, decor: Decor) -> Rapport:
    """Deux envois du même bon : [200, 409], un seul numéro."""
    r = Rapport("Double envoi d'un bon : un seul numéro", REPETITIONS)
    a = postes.de("achats", 1)[0]
    deux = postes.de("achats", 2)
    for tour in range(REPETITIONS):
        b = _brouillon(a, decor, decor.matieres[tour % len(decor.matieres)])
        chemin = f"/api/commandes/{b['id']}/envoyer"
        codes = _ensemble(serveur, _gestes(deux, chemin, int(b["version"])))
        if codes != [200, 409]:
            r.anomalies.append(f"tour {tour} : codes {codes}")
    return r


def course_double_approbation(
    serveur: object, postes: Postes, decor: Decor, adresse: str
) -> Rapport:
    """Deux approbations du même bon au-dessus du seuil : un seul départ ([200, 409])."""
    r = Rapport("Double approbation d'un bon", REPETITIONS)
    _seuil(adresse, "1")
    try:
        a = postes.de("achats", 1)[0]
        deux = postes.de("direction", 2)
        for tour in range(REPETITIONS):
            b = _brouillon(a, decor, decor.matieres[tour % len(decor.matieres)], kg=1000)
            envoye = a.appeler(
                "POST", f"/api/commandes/{b['id']}/envoyer", {"version": b["version"]}
            )  # type: ignore[attr-defined]
            if envoye[0] != 200 or envoye[1].get("statut") != "a_approuver":
                r.anomalies.append(
                    f"tour {tour} : envoi {envoye[0]} statut {envoye[1].get('statut')}"
                )
                continue
            chemin = f"/api/commandes/{b['id']}/approuver"
            codes = _ensemble(serveur, _gestes(deux, chemin, int(envoye[1]["version"])))
            if codes != [200, 409]:
                r.anomalies.append(f"tour {tour} : codes {codes}")
    finally:
        _seuil(adresse, "100000000")
    return r


def course_verrou_de_version(serveur: object, postes: Postes, decor: Decor) -> Rapport:
    """Deux enregistrements d'une fiche partis de la même version : [200, 409]."""
    r = Rapport("Deux enregistrements d'une fiche (verrou de version)", REPETITIONS)
    a = postes.de("achats", 1)[0]
    deux = postes.de("achats", 2)
    for tour in range(REPETITIONS):
        m = decor.matieres[tour % len(decor.matieres)]
        b = _brouillon(a, decor, m)
        version, cid = b["version"], b["id"]

        def modifier(
            poste: object, kg: int, cid: int = cid, version: int = version, m: int = m
        ) -> int:
            corps = {"version": version, "lignes": [{"matiere_id": m, "quantite": kg}]}
            return poste.appeler("PUT", f"/api/commandes/{cid}", corps)[0]  # type: ignore[attr-defined]

        codes = _ensemble(serveur, [lambda: modifier(deux[0], 110), lambda: modifier(deux[1], 120)])
        if codes != [200, 409]:
            r.anomalies.append(f"tour {tour} : codes {codes}")
    return r


def course_vingt_numeros(serveur: object, postes: Postes, decor: Decor) -> Rapport:
    """Vingt envois simultanés : vingt numéros consécutifs, sans trou ni doublon."""
    r = Rapport("Vingt envois simultanés : numéros consécutifs", 1)
    a = postes.de("achats", 1)[0]
    vingt = postes.de("achats", 20)
    bons = [_brouillon(a, decor, decor.matieres[i % len(decor.matieres)]) for i in range(20)]
    codes = _ensemble(
        serveur,
        [
            lambda p=p, b=b: p.appeler(
                "POST", f"/api/commandes/{b['id']}/envoyer", {"version": b["version"]}
            )[0]
            for p, b in zip(vingt, bons, strict=True)
        ],
    )
    if codes != [200] * 20:
        r.anomalies.append(f"codes {codes}")
    numeros = [a.get(f"/api/commandes/{b['id']}")["numero"] for b in bons]  # type: ignore[attr-defined]
    rangs = sorted(int(str(n).rsplit("-", 1)[1]) for n in numeros if n)
    if len(set(rangs)) != 20 or rangs != list(range(rangs[0], rangs[0] + 20)):
        r.anomalies.append(f"rangs non consécutifs : {rangs}")
    return r


def controle_final(poste: object) -> Rapport:
    """`/api/controles/soldes` : soldes = journal, aucun négatif ; et la série BC sans trou."""
    r = Rapport("Invariant final : soldes = journal, série BC sans trou", 1)
    soldes = poste.get("/api/controles/soldes")  # type: ignore[attr-defined]
    if not soldes.get("conforme") or soldes.get("negatifs"):
        r.anomalies.append(f"soldes : {soldes}")
    return r


def jouer(adresse: str) -> list[Rapport]:
    """Lance le serveur, sème, rejoue les courses, rend les rapports ; arrête tout en sortie."""
    import tempfile

    from charge_serveur import servir

    decor = semer(nombre_matieres=max(REPETITIONS, 20))
    _seuil(adresse, "100000000")
    with (
        tempfile.TemporaryDirectory(prefix="concurrence-") as dossier,
        servir(adresse, Path(dossier)) as serveur,
    ):
        postes = Postes(serveur)
        rapports = [
            course_double_envoi(serveur, postes, decor),
            course_vingt_numeros(serveur, postes, decor),
            course_verrou_de_version(serveur, postes, decor),
            course_double_approbation(serveur, postes, decor, adresse),
        ]
        rapports.append(controle_final(postes.de("direction", 1)[0]))
    return rapports


def ecrire(rapports: list[Rapport], serie_bc: tuple[int, int, int]) -> str:
    """Le rapport texte, daté, avec le verdict par course."""
    from datetime import datetime

    nombre, mini, maxi = serie_bc
    quand = datetime.now().strftime("%Y-%m-%d %H:%M")  # noqa: DTZ005
    entete = [
        "ÉPREUVE DE CONCURRENCE (lot V4) — vrai serveur uvicorn",
        f"Rejouée le {quand} ; {REPETITIONS} répétitions par course.",
        "",
    ]
    corps = [r.ligne() for r in rapports]
    pied = [
        "",
        f"Série BC : {nombre} numéros, du rang {mini} au {maxi} "
        + ("(sans trou ni doublon)" if maxi - mini + 1 == nombre else "— TROU OU DOUBLON"),
        "",
        "Verdict : "
        + ("toutes les courses tenues." if all(r.tenue for r in rapports) else "COURSE ROMPUE."),
    ]
    return "\n".join(entete + corps + pied) + "\n"


def serie_bc(adresse: str) -> tuple[int, int, int]:
    """(nombre, plus petit rang, plus grand rang) des bons numérotés : le trou se verrait."""
    moteur = create_engine(adresse, poolclass=NullPool)
    with moteur.connect() as c:
        rangs = [
            int(str(n).rsplit("-", 1)[1])
            for (n,) in c.execute(select(text("numero")).select_from(text("commande")))
            if n
        ]
    moteur.dispose()
    return (len(rangs), min(rangs), max(rangs)) if rangs else (0, 0, 0)


def main() -> int:
    """Prépare la base, rejoue les courses, écrit le rapport, supprime la base."""
    adresse = _garde_fou()
    preparer_base(adresse)
    try:
        rapports = jouer(adresse)
        bc = serie_bc(adresse)
    finally:
        moteur = _maintenance(adresse)
        with moteur.connect() as c:  # type: ignore[attr-defined]
            c.execute(text(f'DROP DATABASE IF EXISTS "{make_url(adresse).database}" WITH (FORCE)'))
        moteur.dispose()  # type: ignore[attr-defined]
    texte = ecrire(rapports, bc)
    SORTIE.write_text(texte, encoding="utf-8")
    sys.stdout.write(texte)
    return 0 if all(r.tenue for r in rapports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
