"""Les lignes d'un bon que ce camion n'a pas apportées (livraison en plusieurs fois).

Choisir le bon reprend toutes ses lignes qui restent à livrer ; le camion n'en apporte souvent
qu'une partie. Une ligne **non livrée** est une ligne de bon, pas refusée, laissée entièrement
vide : ni BL, ni pesée, ni palette, ni bobine, ni lot (les observations ne comptent pas). Elle ne
bloque rien (`receptions_blocages`) ; la validation la **retire** de la réception, dans sa
transaction et au journal, avant d'écrire lots et mouvements : elle reste due sur le bon, qui
reste ouvert pour le camion suivant. Une réception dont toutes les lignes sont ainsi vides ne se
valide pas (`RIEN_N_EST_PESE`). Décision de Mohamed du 12/10/2026
(docs/lots/LIVRAISON-PARTIELLE.md).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from gestion_mp_pro.modeles import Reception, ReceptionLigne
from gestion_mp_pro.modeles.enums import QualiteReception
from gestion_mp_pro.services import audit
from gestion_mp_pro.services.commandes_socle import nom_commande
from gestion_mp_pro.services.receptions_socle import Bons, lignes_triees, nom_reception

RIEN_N_EST_PESE = (
    "Rien n'est pesé : saisir ce que le camion a apporté (les lignes laissées vides restent "
    "dues sur le bon)."
)
"""Le refus d'une réception dont toutes les lignes sont non livrées (le même à l'écran)."""


def non_livree(x: ReceptionLigne) -> bool:
    """Vrai pour une ligne de bon, pas refusée, entièrement vide : ce camion ne l'a pas apportée."""
    return (
        x.commande_ligne_id is not None
        and x.qualite != QualiteReception.refuse
        and not x.quantite_bl
        and not x.quantite_pesee
        and not x.nb_palettes
        and not x.nb_bobines
        and not x.bobines_en_plus
        and not (x.lot_numero or "").strip()
        and not x.lot_interne
    )


def tout_est_vide(r: Reception) -> bool:
    """Vrai si la réception a des lignes et qu'aucune n'a été livrée par ce camion."""
    return bool(r.lignes) and all(non_livree(x) for x in r.lignes)


def retirer(s: Session, qui: audit.Qui, r: Reception, b: Bons, references: dict[int, str]) -> int:
    """Retire les lignes non livrées d'un brouillon qu'on valide (journal « lignes non livrées
    retirées », la photo de chacune en `avant`) ; rend leur nombre. Leurs lignes de bon gardent
    leur reste à livrer : rien n'est reçu pour elles."""
    retirees = [x for x in lignes_triees(r) if non_livree(x)]
    if not retirees:
        return 0
    noms = sorted({nom_commande(b.bon(x.commande_ligne_id or 0)) for x in retirees})
    quoi = ", ".join(references.get(x.matiere_id, "?") for x in retirees)
    audit.journal(
        s,
        qui,
        "lignes non livrées retirées",
        "reception",
        r.id,
        detail=f"{nom_reception(r)} · {len(retirees)} ligne(s) non livrée(s) par ce camion, "
        f"toujours due(s) sur {', '.join(noms)} : {quoi}",
        avant={"lignes": [audit.photo(x) for x in retirees]},
    )
    for x in retirees:
        r.lignes.remove(x)
    s.flush()
    return len(retirees)
