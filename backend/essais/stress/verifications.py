"""Les invariants contrôlés à chaque fin de mois, par un autre chemin que l'écran :

- `GET /controles/soldes` (soldes = journal, aucun négatif) **et** le même recompte en SQL direct ;
- Entré − Sorti = Reste sur tout le journal ;
- le stock de chaque matière rendu par `GET /stock` contre la somme SQL des soldes (net, en
  quarantaine) et des fils montés (en machine) ; disponible et projeté cohérents entre eux ;
- le vérificateur indépendant `essais/verification_chiffres.py` (lot V1), joué **en mémoire** sur
  l'application à l'heure de la simulation (toutes ses familles) ;
- l'échéancier contre les factures et frais non réglés de la base ;
- la restauration d'une sauvegarde sur une base à part (fin d'année) : mêmes comptes de lignes.

Un invariant faux est une anomalie `invariant` (classe PROBABLE jusqu'à l'analyse, qui tranche
entre défaut de l'application et recompte du simulateur mal posé).
"""

from __future__ import annotations

import subprocess
import sys
import urllib.parse
from pathlib import Path
from typing import Any

from essais.stress.monde import Monde

KG = 0.0015
ESSAIS = Path(__file__).resolve().parents[1]
TABLES_COMPTEES = (
    "mouvement",
    "lot",
    "solde",
    "commande",
    "commande_ligne",
    "reception",
    "reception_ligne",
    "ordre",
    "operation",
    "dossier",
    "inventaire",
    "facture",
    "utilisateur",
)


def _libpq(base: str) -> str:
    return base.replace("postgresql+psycopg://", "postgresql://", 1)


class Sql:
    """Une connexion de lecture à la base de la simulation."""

    def __init__(self, base: str) -> None:
        import psycopg

        self.connexion = psycopg.connect(_libpq(base), autocommit=True)

    def lignes(self, requete: str, params: Any = None) -> list[tuple[Any, ...]]:
        """Les lignes d'une lecture, décimaux en `float`."""
        from decimal import Decimal

        with self.connexion.cursor() as c:
            c.execute(requete, params)
            return [
                tuple(float(v) if isinstance(v, Decimal) else v for v in r) for r in c.fetchall()
            ]

    def un(self, requete: str, params: Any = None) -> Any:
        """La première valeur de la première ligne."""
        lignes = self.lignes(requete, params)
        return lignes[0][0] if lignes else None

    def fermer(self) -> None:
        """Ferme la connexion."""
        self.connexion.close()


def _anomalie(m: Monde, sujet: str, detail: str) -> None:
    m.journal.anomalie("PROBABLE", "invariant", detail, sujet=sujet)
    m.journal.note(f"  ✗ invariant — {sujet} : {detail[:300]}")


def soldes_et_journal(m: Monde, sql: Sql) -> None:
    """Soldes = journal (API puis SQL), aucun solde négatif, Entré − Sorti = Reste."""
    lu = m.D.get("/controles/soldes")
    if not lu["conforme"]:
        _anomalie(
            m, "controles/soldes", f"{len(lu['ecarts'])} écart(s), {lu['negatifs']} négatif(s)"
        )
    ecarts = sql.lignes(
        "SELECT COALESCE(j.lot_id, s.lot_id), COALESCE(j.magasin_id, s.magasin_id), "
        "COALESCE(j.q, 0), COALESCE(s.quantite, 0) FROM "
        "(SELECT lot_id, magasin_id, SUM(quantite) q FROM mouvement GROUP BY lot_id, magasin_id) j "
        "FULL OUTER JOIN solde s ON s.lot_id = j.lot_id AND s.magasin_id = j.magasin_id "
        "WHERE ABS(COALESCE(j.q, 0) - COALESCE(s.quantite, 0)) > 0.0005"
    )
    if ecarts:
        _anomalie(m, "soldes SQL ≠ journal SQL", f"{len(ecarts)} : {ecarts[:3]}")
    negatifs = sql.un("SELECT COUNT(*) FROM solde WHERE quantite < 0")
    if negatifs:
        _anomalie(m, "soldes négatifs", f"{negatifs}")
    entre, sorti, reste = sql.lignes(
        "SELECT (SELECT COALESCE(SUM(quantite), 0) FROM mouvement WHERE quantite > 0), "
        "(SELECT COALESCE(-SUM(quantite), 0) FROM mouvement WHERE quantite < 0), "
        "(SELECT COALESCE(SUM(quantite), 0) FROM solde)"
    )[0]
    if abs(entre - sorti - reste) > KG:
        _anomalie(m, "Entré − Sorti ≠ Reste", f"{entre} − {sorti} ≠ {reste}")
    m.journal.note(
        f"  · journal : entré {entre:,.1f} kg, sorti {sorti:,.1f} kg, reste {reste:,.1f} kg"
    )


def stock_par_matiere(m: Monde, sql: Sql) -> None:
    """`GET /stock` contre la base : net, quarantaine, en machine ; disponible cohérent."""
    net = {
        r: (q, quar)
        for r, q, quar in sql.lignes(
            "SELECT a.reference, SUM(s.quantite), "
            "SUM(CASE WHEN mg.type = 'quarantaine' THEN s.quantite ELSE 0 END) "
            "FROM solde s JOIN lot l ON l.id = s.lot_id JOIN matiere a ON a.id = l.matiere_id "
            "JOIN magasin mg ON mg.id = s.magasin_id GROUP BY a.reference"
        )
    }
    machine: dict[str, float] = {}
    for metier in m.D.get("/metiers"):
        if not metier.get("actif", True):
            continue
        for f in metier.get("fils", []):
            machine[f["reference"]] = machine.get(f["reference"], 0.0) + float(f["poids"])
    stock = m.D.get("/stock")
    ecarts: list[str] = []
    for x in stock["lignes"]:
        ref = x["reference"]
        q, quar = net.get(ref, (0.0, 0.0))
        if abs(float(x["stock_net"]) - q) > KG:
            ecarts.append(f"{ref} net écran {x['stock_net']} / SQL {q}")
        if abs(float(x["stock_quarantaine"]) - quar) > KG:
            ecarts.append(f"{ref} quarantaine écran {x['stock_quarantaine']} / SQL {quar}")
        if abs(float(x["stock_machine"]) - machine.get(ref, 0.0)) > KG:
            ecarts.append(
                f"{ref} machine écran {x['stock_machine']} / métiers {machine.get(ref, 0.0)}"
            )
        attendu = float(x["stock_net"]) - float(x["stock_quarantaine"]) + float(x["stock_machine"])
        if abs(float(x["stock_disponible"]) - attendu) > KG:
            ecarts.append(
                f"{ref} disponible {x['stock_disponible']} ≠ net − quarantaine + machine {attendu}"
            )
    manquantes = [
        r for r in net if r not in {x["reference"] for x in stock["lignes"]} and abs(net[r][0]) > KG
    ]
    if manquantes:
        ecarts.append(f"matières en stock absentes de l'écran : {manquantes[:5]}")
    if ecarts:
        _anomalie(m, "stock par matière", f"{len(ecarts)} écart(s) : " + " ; ".join(ecarts[:4]))
    else:
        m.journal.note(f"  ✓ stock par matière : {len(stock['lignes'])} lignes = SQL")


def echeancier(m: Monde, sql: Sql) -> None:
    """Les pièces non réglées de l'échéancier contre la base."""
    ech = m.A.get("/echeancier?du=2000-01-01&au=2099-12-31")
    factures_ecran = sum(1 for x in ech["lignes"] + ech["a_dater"] if x["objet"] == "facture")
    frais_ecran = sum(1 for x in ech["lignes"] + ech["a_dater"] if x["objet"] == "frais")
    factures_sql = sql.un(
        "SELECT COUNT(*) FROM facture f WHERE f.payee_le IS NULL AND COALESCE(f.numero, '') <> '' "
        "AND EXISTS (SELECT 1 FROM reception r WHERE r.facture_id = f.id AND r.statut = 'validee')"
    )
    frais_sql = sql.un(
        "SELECT COUNT(*) FROM dossier_frais fr JOIN dossier d ON d.id = fr.dossier_id "
        "WHERE fr.payee_le IS NULL AND d.statut <> 'annule'"
    )
    if factures_ecran != factures_sql or frais_ecran != frais_sql:
        _anomalie(
            m,
            "échéancier",
            f"factures écran {factures_ecran} / SQL {factures_sql} ; "
            f"frais écran {frais_ecran} / SQL {frais_sql}",
        )
    else:
        m.journal.note(
            f"  ✓ échéancier : {factures_ecran} factures et {frais_ecran} frais à régler"
        )


class _Acces:
    """Ce que le vérificateur V1 lit : l'application en mémoire (direction) et la base en SQL."""

    def __init__(self, m: Monde, sql: Sql) -> None:
        self.m = m
        self.base = sql

    def get(self, chemin: str, **params: Any) -> Any:
        """Une lecture de l'API (paramètres répétés pour une liste)."""
        propres = {k: v for k, v in params.items() if v is not None}
        q = "?" + urllib.parse.urlencode(propres, doseq=True) if propres else ""
        r = self.m.D.appeler("GET", chemin + q, None, (200, 404), note="vérificateur V1")
        if not r.ok:
            raise RuntimeError(f"GET {chemin}{q} : {r.statut} {r.detail}")
        return r.corps

    def sql(self, requete: str, params: Any = None) -> list[tuple[Any, ...]]:
        """Une lecture SQL."""
        return self.base.lignes(requete, params)


def verificateur_v1(m: Monde, sql: Sql, dates: int) -> None:
    """Le vérificateur indépendant des chiffres, en mémoire, à l'heure de la simulation."""
    if str(ESSAIS) not in sys.path:
        sys.path.insert(0, str(ESSAIS))
    import verification_chiffres as vc

    releve = vc.verifier(_Acces(m, sql), m.jour, dates)
    for ligne in releve.lignes():
        m.journal.note("  " + ligne)
    for nom, famille in releve.familles.items():
        for e in famille.ecarts[:5]:
            m.journal.anomalie("PROBABLE", "invariant", e, sujet=f"V1 {nom}")


def controler(m: Monde, dates: int = 2) -> None:
    """Tous les invariants d'une fin de mois."""
    sql = Sql(m.base)
    try:
        soldes_et_journal(m, sql)
        stock_par_matiere(m, sql)
        echeancier(m, sql)
        verificateur_v1(m, sql, dates)
    finally:
        sql.fermer()


def restauration_a_part(m: Monde, fichier: Path) -> None:
    """La sauvegarde de l'application restaurée dans `gestion_mp_pro_stress_restaure_essai` ;
    les comptes de lignes des tables d'activité doivent être ceux de la base vivante."""
    from gestion_mp_pro.reprise.sauvegarde import outil

    nom = "gestion_mp_pro_stress_restaure_essai"
    admin = _libpq(m.base.rsplit("/", 1)[0] + "/postgres")
    subprocess.run(  # noqa: S603 — outils PostgreSQL, arguments à nous
        [outil("psql"), admin, "-Atc", f'DROP DATABASE IF EXISTS "{nom}" WITH (FORCE)'],
        check=True,
        capture_output=True,
    )
    subprocess.run(  # noqa: S603
        [outil("psql"), admin, "-Atc", f'CREATE DATABASE "{nom}"'], check=True, capture_output=True
    )
    subprocess.run(  # noqa: S603
        [
            outil("pg_restore"),
            "--no-owner",
            "-d",
            m.base.rsplit("/", 1)[0].replace("postgresql+psycopg://", "postgresql://") + "/" + nom,
            str(fichier),
        ],
        check=False,
        capture_output=True,
    )  # noqa: S603
    vivante, restauree = Sql(m.base), Sql(m.base.rsplit("/", 1)[0] + "/" + nom)
    try:
        ecarts = []
        for table in TABLES_COMPTEES:
            a, b = (
                vivante.un(f"SELECT COUNT(*) FROM {table}"),  # noqa: S608 — noms à nous
                restauree.un(f"SELECT COUNT(*) FROM {table}"),  # noqa: S608
            )
            if a != b:
                ecarts.append(f"{table} {a} ≠ {b}")
        if ecarts:
            _anomalie(m, "restauration sur une base à part", " ; ".join(ecarts))
        else:
            m.journal.note(
                f"  ✓ restauration à part : {len(TABLES_COMPTEES)} tables aux mêmes comptes"
            )
    finally:
        vivante.fermer()
        restauree.fermer()
        subprocess.run(  # noqa: S603
            [outil("psql"), admin, "-Atc", f'DROP DATABASE IF EXISTS "{nom}" WITH (FORCE)'],
            check=False,
            capture_output=True,
        )  # noqa: S603
