"""Pagination par curseur de la liste des bons (route 152), son aperçu (251) et l'accès borné
aux bons ouverts (252).

On prouve : l'union des pages est exactement la liste entière (mêmes id, même ordre date du bon
puis n° d'entrée, sans doublon ni saut) ; le total, les comptes par onglet, « à approuver »,
« en retard » et le pied de totaux sont ceux de tout le filtre ; la recherche SQL rend le même
ensemble que l'ancienne recherche Python SAUF le libellé de livraison, retiré (convention
PAGINATION4) ; l'accès `ouverts` ne rend que les bons ni soldés ni annulés.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from fabrique import *  # noqa: F403
from fabriques.pilotage import Usine, fixture_usine, jour  # noqa: F401
from fabriques.referentiels import fournisseur as ref_fournisseur
from fabriques.referentiels import matiere as ref_matiere

from gestion_mp_pro.modeles import Commande, CommandeLigne
from gestion_mp_pro.modeles.enums import OrigineSolde, StatutCommande
from gestion_mp_pro.modeles.recherche import normaliser
from gestion_mp_pro.services.commandes_lecture import LIBELLES_STATUT


def _poser(
    u: Usine,
    *,
    fournisseur_id: int,
    matiere_id: int,
    statut: StatutCommande,
    devise: str = "MAD",
    numero: str | None = None,
    le: date,
    promise: date | None = None,
    observations: str = "",
    conteneur: str = "",
) -> int:
    """Un bon posé en base (contrôle total du statut, de la devise et des dates)."""
    solde = (
        OrigineSolde.automatique
        if statut in (StatutCommande.soldee, StatutCommande.annulee)
        else None
    )
    c = Commande(
        numero=numero,
        fournisseur_id=fournisseur_id,
        statut=statut,
        date_commande=le,
        date_livraison_prevue=promise,
        devise=devise,
        observations=observations,
        conteneur=conteneur,
        solde_origine=solde,
    )
    u.s.add(c)
    u.s.flush()
    u.s.add(
        CommandeLigne(
            commande_id=c.id,
            matiere_id=matiere_id,
            quantite=Decimal(100),
            prix=Decimal(10),
        )
    )
    u.s.flush()
    return c.id


def _texte_ref(bon: dict[str, Any], designation: str) -> str:
    """L'ancienne recherche Python, SANS le libellé de livraison (ce que la SQL doit reproduire)."""
    morceaux = [
        bon["numero"] or "brouillon",
        bon["fournisseur"],
        bon["pays"],
        bon["devise"],
        LIBELLES_STATUT[bon["statut"]],
        bon["cree_par"] or "",
        bon["observations"],
        bon["expedition"]["conteneur"],
        bon["expedition"]["navire"],
        *bon["references"],
        designation,
    ]
    return normaliser(" ".join(morceaux))


def _pages(u: Usine, limite: int = 2, **params: Any) -> list[dict[str, Any]]:
    """L'union des pages, en suivant le curseur (limite petite pour en avoir plusieurs)."""
    elements: list[dict[str, Any]] = []
    apres: str | None = None
    while True:
        p = u.get(
            u.achats,
            "/api/commandes",
            limite=limite,
            **({"apres": apres} if apres else {}),
            **params,
        )
        elements += p["elements"]
        apres = p["suivant"]
        if not apres:
            return elements


def _bons(u: Usine, f1: int, f2: int, m1: int, m2: int) -> dict[str, int]:
    """Sept bons couvrant les onglets (dont un en retard, un soldé, un annulé)."""
    St = StatutCommande

    def p(**kw: Any) -> int:
        return _poser(u, **kw)

    return {
        "brouillon": p(fournisseur_id=f1, matiere_id=m1, statut=St.brouillon, le=jour(-2)),
        "a_approuver": p(
            fournisseur_id=f1,
            matiere_id=m1,
            statut=St.a_approuver,
            numero="BC-APP-1",
            le=jour(-3),
            observations="MARQUEOBS",
        ),  # fmt: skip
        "envoyee": p(
            fournisseur_id=f2,
            matiere_id=m2,
            statut=St.envoyee,
            numero="BC-ENV-1",
            le=jour(-5),
            promise=jour(20),
            devise="USD",
            conteneur="MSCU7788",
        ),  # fmt: skip
        "confirmee": p(
            fournisseur_id=f2,
            matiere_id=m2,
            statut=St.confirmee,
            numero="BC-CONF-1",
            le=jour(-7),
            promise=jour(15),
        ),  # fmt: skip
        "retard": p(
            fournisseur_id=f1,
            matiere_id=m1,
            statut=St.envoyee,
            numero="BC-TARDIF-9",
            le=jour(-40),
            promise=jour(-10),
            devise="USD",
        ),  # fmt: skip
        "soldee": p(
            fournisseur_id=f2, matiere_id=m2, statut=St.soldee, numero="BC-OLD-1", le=jour(-60)
        ),
        "annulee": p(
            fournisseur_id=f1, matiere_id=m1, statut=St.annulee, numero="BC-OLD-2", le=jour(-61)
        ),
    }


def _decor(u: Usine) -> dict[str, Any]:
    """Deux fournisseurs, leurs matières, et sept bons couvrant les onglets, dont un en retard."""
    f1 = ref_fournisseur(nom="ALPHATEX FILATURE", pays="PORTUGAL", delai_jours=30, s=u.s)
    f2 = ref_fournisseur(nom="BETAWEAVE MILLS", pays="EGYPTE", delai_jours=30, s=u.s)
    m1 = ref_matiere("ZREF-COTON", designation="Coton cardé", fournisseur_id=f1, s=u.s)
    m2 = ref_matiere("ZREF-LAINE", designation="Laine peignée", fournisseur_id=f2, s=u.s)
    desc = {m1: "Coton cardé", m2: "Laine peignée"}
    return {"bons": _bons(u, f1, f2, m1, m2), "desc": desc, "m1": m1, "m2": m2}


def test_union_des_pages_est_la_liste_entiere(usine: Usine) -> None:
    """Union des pages = liste entière, ordre (date du bon desc, n° d'entrée desc), sans doublon."""
    u = usine
    d = _decor(u)
    page = u.get(u.achats, "/api/commandes", limite=500)
    attendus = sorted(d["bons"].values(), key=lambda i: i)
    union = _pages(u, limite=2)
    ids = [e["id"] for e in union]
    assert sorted(ids) == attendus and len(ids) == len(set(ids))
    assert page["total"] == len(attendus)
    # Ordre stable : date du bon décroissante, puis n° d'entrée décroissant.
    ordre = sorted(union, key=lambda e: (e["date_commande"], e["id"]), reverse=True)
    assert ids == [e["id"] for e in ordre]


def test_comptes_par_onglet_et_indicateurs(usine: Usine) -> None:
    """L'aperçu : comptes par onglet, « à approuver », « en retard » et indicateurs exacts."""
    u = usine
    _decor(u)
    a = u.get(u.achats, "/api/commandes/apercu")
    assert (a["brouillon"], a["a_approuver"], a["envoyee"], a["confirmee"], a["clos"]) == (
        1,
        1,
        2,
        1,
        2,
    )
    assert a["total"] == 7
    i = a["indicateurs"]
    assert i["ouverts"] == 5  # tout sauf les deux clos
    assert i["brouillons"] == 1 and i["a_approuver"] == 1
    assert i["partis"] == 3  # envoyee (×2) + confirmee
    assert i["retard"] == 1  # le seul bon en retard


def test_filtre_en_retard_exact_et_borne(usine: Usine) -> None:
    """Le filtre « en retard » ne rend que le bon en retard ; l'aperçu le compte dans son onglet."""
    u = usine
    d = _decor(u)
    page = u.get(u.achats, "/api/commandes", filtre="retard", limite=500)
    assert [e["id"] for e in page["elements"]] == [d["bons"]["retard"]]
    assert page["total"] == 1
    assert all(e["en_retard"] for e in page["elements"])
    a = u.get(u.achats, "/api/commandes/apercu", filtre="retard")
    assert a["envoyee"] == 1 and a["total"] == 1 and a["clos"] == 0


def test_pied_de_totaux_suit_la_recherche(usine: Usine) -> None:
    """Le pied (Σ kg, Σ par devise, Σ MAD) de l'aperçu = la somme sur les bons de l'onglet."""
    u = usine
    _decor(u)
    elements = u.get(u.achats, "/api/commandes", statut="envoyee", limite=500)["elements"]
    a = u.get(u.achats, "/api/commandes/apercu", statut="envoyee")
    assert a["quantite"] == sum(e["quantite"] for e in elements)
    assert abs(a["montant_estime_mad"] - sum(e["montant_estime_mad"] for e in elements)) < 1e-6
    par_devise: dict[str, float] = {}
    for e in elements:
        par_devise[e["devise"]] = par_devise.get(e["devise"], 0.0) + e["montant_estime"]
    rendu = {m["devise"]: m["montant_estime"] for m in a["montants"]}
    assert set(rendu) == set(par_devise)
    for dev, v in par_devise.items():
        assert abs(rendu[dev] - v) < 1e-6


def test_recherche_sql_identique_a_l_ancienne_sauf_livraison(usine: Usine) -> None:
    """Pour chaque jeton des champs cherchés, la recherche SQL rend exactement les bons dont le
    texte (ancienne recherche, SANS le libellé de livraison) le contient ; un mot qui n'est que
    dans l'état de livraison (« retard ») ne trouve plus rien (convention PAGINATION4)."""
    u = usine
    d = _decor(u)
    tous = u.get(u.achats, "/api/commandes", limite=500)["elements"]
    # Texte de référence par bon (désignation de sa matière connue du décor).
    designation = {d["m1"]: "Coton cardé", d["m2"]: "Laine peignée"}
    ligne_matiere = {e["id"]: d["m1"] if "ZREF-COTON" in e["references"] else d["m2"] for e in tous}
    texte = {e["id"]: _texte_ref(e, designation[ligne_matiere[e["id"]]]) for e in tous}
    jetons = ["alphatex", "betaweave", "portugal", "egypte", "usd", "mad", "marqueobs",
              "mscu7788", "zref-coton", "zref-laine", "coton", "laine", "confirmee",
              "envoyee"]  # fmt: skip
    for jeton in jetons:
        attendu = {i for i, t in texte.items() if normaliser(jeton) in t}
        rendu = {
            e["id"] for e in u.get(u.achats, "/api/commandes", q=jeton, limite=500)["elements"]
        }
        assert rendu == attendu, f"jeton « {jeton} » : {rendu} ≠ {attendu}"
    # « retard » n'est que dans le libellé de livraison du bon en retard : plus trouvé.
    rendu = {e["id"] for e in u.get(u.achats, "/api/commandes", q="retard", limite=500)["elements"]}
    assert d["bons"]["retard"] not in rendu
    # mais le filtre « en retard », lui, le rend (l'état reste accessible).
    filtre = u.get(u.achats, "/api/commandes", filtre="retard", limite=500)["elements"]
    assert [e["id"] for e in filtre] == [d["bons"]["retard"]]


def test_ouverts_borne_exclut_les_clos(usine: Usine) -> None:
    """L'accès borné `ouverts` ne rend que les bons ni soldés ni annulés (saisie, Ma journée)."""
    u = usine
    d = _decor(u)
    ouverts = u.get(u.achats, "/api/commandes/ouverts")
    ids = {e["id"] for e in ouverts}
    assert d["bons"]["soldee"] not in ids and d["bons"]["annulee"] not in ids
    assert ids == {
        d["bons"][k] for k in ("brouillon", "a_approuver", "envoyee", "confirmee", "retard")
    }
