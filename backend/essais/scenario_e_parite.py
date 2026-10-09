"""Étape 23 du scénario : le même mois rejoué dans Gestion MP (parité dynamique, § 7.4).

Gestion MP est lancé sur sa propre copie de `gestion_mp_comparaison`, à l'heure du scénario, et
les mêmes gestes y sont joués par son API (`scenario_gmp_gestes`). Les photos prises aux mêmes
points de contrôle (stock, coût moyen, valeur des matières du scénario ; numéros donnés ; refus ;
plan d'achat ; coût du dossier) sont comparées aux tolérances de § 7.5.

Écart déclaré (règle K7, docs/lots/RESTES.md : décision de Mohamed, le fil monté est du stock) :
à une date passée, PRO compte le fil monté de ce soir-là, Gestion MP non ; la photo de fin de
novembre de M1 diffère donc exactement de 445,5 kg et de 445,5 × coût moyen — forme et ampleur
vérifiées, rien d'autre n'est excusé.
"""

from __future__ import annotations

from typing import Any

import scenario_gmp_atelier as atelier
import scenario_gmp_gestes as gestes
import scenario_gmp_serveur as gmp
from scenario_monde import Monde
from scenario_outils import KG, MAD, Horloge

MONTAGE_KG = 445.5


def _rejouer(m: Monde) -> gestes.Jeu:
    dossier = m.avant["dossier"]
    horloge = Horloge(dossier / "horloge-gmp.txt")
    horloge.aller(_jour0())
    copie = str(m.avant["base"]).replace("_essai", "_gmp_essai")
    with gmp.lancer(copie, dossier, horloge) as postes:
        jeu = gestes.Jeu(postes, horloge)
        for geste in (
            gestes.referentiels,
            gestes.achats,
            atelier.camion,
            atelier.atelier,
            atelier.fin_du_mois,
        ):
            geste(jeu)
    from scenario_bases import supprimer

    supprimer(copie)
    return jeu


def _jour0() -> Any:
    from datetime import date

    return date(2026, 11, 2)


def _comparer_photo(m: Monde, nom: str, gmp_photo: dict[str, Any], machine: float = 0.0) -> None:
    v = m.verif
    pro = m.avant["photos"].get(nom, {})
    for cle, (stock, cmup, valeur) in gmp_photo.items():
        p_stock, p_cmup, p_valeur = pro.get(cle, (None, None, None))
        en_plus = machine if cle == "M1" else 0.0
        v.egal(
            f"{nom} {cle} : stock (PRO = GMP{' + K7' if en_plus else ''})",
            p_stock,
            stock + en_plus,
            KG,
        )
        v.proche(f"{nom} {cle} : coût moyen", p_cmup, cmup)
        v.egal(f"{nom} {cle} : valeur", p_valeur, valeur + en_plus * cmup, MAD)


def etape_parite(m: Monde) -> None:
    """Étape 23 : Gestion MP rejoue le mois ; mêmes chiffres, mêmes numéros, mêmes refus."""
    v = m.verif
    if m.court or not gmp.disponible():
        m.noter("Étape 23 (parité dynamique) : sautée (version courte ou Gestion MP absent).")
        return
    jeu = _rejouer(m)
    faits = m.avant["faits"]
    for nom in (
        "camion",
        "dossier",
        "of1",
        "montage",
        "of2",
        "quarantaine",
        "retour_fournisseur",
        "inventaire",
        "annulation",
    ):
        _comparer_photo(m, nom, jeu.photos[nom])
    _comparer_photo(m, "fin_novembre", jeu.photos["fin_novembre"], machine=MONTAGE_KG)
    for cle in ("M1", "M2", "M3"):
        v.egal(
            f"plan d'achat {cle} : même proposition",
            faits["plan_achat"][cle],
            jeu.photos["plan_achat"][cle],
            KG,
        )
    v.egal("envoi des bons : statuts et numéros", list(faits["envoi"]), list(jeu.photos["envoi"]))
    v.egal(
        "approbation : statut et numéro",
        list(faits["approbation"]),
        list(jeu.photos["approbation"]),
    )
    v.egal(
        "hausse de 20 % : à approuver, cours figé",
        list(faits["hausse"]),
        list(jeu.photos["hausse"]),
    )
    v.egal("numéros des réceptions", faits["receptions"], jeu.photos["receptions"])
    v.egal("bon EUR soldé à la libération", faits["bon_eur"], jeu.photos["bon_eur"])
    v.egal("bon EUR rouvert par le retour", faits["bon_eur_rouvert"], jeu.photos["bon_eur_rouvert"])
    v.egal("numéro de l'OF1", faits["of1_numero"], jeu.photos["of1_numero"])
    v.egal("OF antidaté : même refus", faits["antidate"], jeu.photos["antidate"])
    for cle, valeur in jeu.photos["dossier_fiche"].items():
        v.egal(f"dossier : {cle}", faits["dossier_fiche"][cle], valeur, MAD)
    ecart, valeur = jeu.photos["inventaire_ecart"]
    v.egal("inventaire : écart (kg)", faits["inventaire_ecart"][0], ecart, KG)
    v.egal("inventaire : écart (MAD)", faits["inventaire_ecart"][1], valeur, MAD)
    m.noter(
        f"Parité dynamique : Gestion MP {gmp.commit()} rejoué sur sa copie, "
        f"{sum(p.appels for p in jeu.p.values())} appels."
    )
