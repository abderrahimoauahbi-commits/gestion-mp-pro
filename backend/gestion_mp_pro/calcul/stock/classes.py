"""Classes ABC (valeur de consommation) et XYZ (régularité de la demande), jours de sécurité.

Portage de `moteur._classer_abc`, `_jours_securite` et du bloc XYZ de `etat_stock`
(`Stock!AA10`, `Stock!AF10`).
"""

from __future__ import annotations

import math

from gestion_mp_pro.calcul.constantes import MOIS
from gestion_mp_pro.calcul.modele import Parametres
from gestion_mp_pro.calcul.stock.journal import Agregat
from gestion_mp_pro.calcul.stock.ligne import LigneStock


def jours_securite(classe: str, parametres: Parametres) -> float:
    """Les jours de sécurité de la classe ABC (A, B, sinon C)."""
    if classe == "A":
        return parametres.securite_a
    if classe == "B":
        return parametres.securite_b
    return parametres.securite_c


def classer_abc(lignes: list[LigneStock], parametres: Parametres) -> None:
    """Classe ABC sur la valeur de consommation annuelle en MAD : % cumulé = Σ(valeurs ≥ la
    mienne) / Σ totale, seuils 80/95 % ; les ex æquo partagent cumul et RANG d'Excel."""
    total = sum(max(0.0, ligne.valeur_conso_annuelle_mad) for ligne in lignes)
    ordre = sorted(lignes, key=lambda x: -x.valeur_conso_annuelle_mad)
    cumul = 0.0
    cumul_par_valeur: dict[float, float] = {}
    rang_par_valeur: dict[float, int] = {}
    for position, ligne in enumerate(ordre, start=1):
        cumul += ligne.valeur_conso_annuelle_mad
        cumul_par_valeur[ligne.valeur_conso_annuelle_mad] = cumul
        rang_par_valeur.setdefault(ligne.valeur_conso_annuelle_mad, position)
    for ligne in lignes:
        ligne.rang = rang_par_valeur.get(ligne.valeur_conso_annuelle_mad, 0)
    for ligne in lignes:
        if not total:
            ligne.pourcentage_cumule = 0.0
            ligne.classe_abc = "C"
            continue
        ligne.pourcentage_cumule = cumul_par_valeur[ligne.valeur_conso_annuelle_mad] / total
        if ligne.pourcentage_cumule <= parametres.seuil_abc_a:
            ligne.classe_abc = "A"
        elif ligne.pourcentage_cumule <= parametres.seuil_abc_b:
            ligne.classe_abc = "B"
        else:
            ligne.classe_abc = "C"


def classer_xyz(ligne: LigneStock, agregat: Agregat | None, parametres: Parametres) -> None:
    """Coefficient de variation (population, ÷ 12) des sorties nettes des douze mois clos ;
    « — » : rien n'est sorti ; une demande parfaitement régulière (cv = 0) est X."""
    sort = False
    if agregat:
        serie = [max(0.0, agregat.sorties_par_mois.get(i, 0.0)) for i in range(MOIS)]
        moyenne = sum(serie) / MOIS
        if moyenne:
            sort = True
            variance = sum((v - moyenne) ** 2 for v in serie) / MOIS
            ligne.cv_demande = math.sqrt(variance) / moyenne
    if not ligne.cv_demande and not sort:
        ligne.classe_xyz = "—"
    elif ligne.cv_demande <= parametres.seuil_xyz_x:
        ligne.classe_xyz = "X"
    elif ligne.cv_demande <= parametres.seuil_xyz_y:
        ligne.classe_xyz = "Y"
    else:
        ligne.classe_xyz = "Z"
