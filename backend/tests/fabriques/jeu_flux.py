"""Un jeu figé réécrit en base PRO, seconde partie (lot S4) : réceptions (lignes aux numéros
qu'y lisent les entrées et les dossiers), lots, ordres, journal du stock (identifiants gardés,
quantités signées, transfert en deux jambes), soldes, dossiers, métiers.
"""

from __future__ import annotations

import itertools
from collections import defaultdict

from fabriques.jeu_base import Index, inserer, instant
from fabriques.moteur_base import ajouter
from sqlalchemy.orm import Session

from gestion_mp_pro.calcul import modele as c
from gestion_mp_pro.calcul.chargement import TYPE_MOTEUR
from gestion_mp_pro.modeles import (
    Facture,
    Lot,
    Metier,
    Ordre,
    OrdreQualite,
    Reception,
    ReceptionLigne,
    Solde,
)

TYPE_BASE = {moteur: base for base, moteur in TYPE_MOTEUR.items()}
QUALITES = {"Conforme": "conforme", "Réserve": "reserve", "Refusé": "refuse"}
Cle = tuple[str, str]


def lots(s: Session, d: c.Donnees, ix: Index) -> None:
    """Un lot par (matière, numéro) cité : entré à sa première date, fournisseur du journal."""
    vus: dict[Cle, list[c.Mouvement]] = defaultdict(list)
    for m in d.mouvements:
        vus[(m.reference, m.lot_fournisseur)].append(m)
    autres = {(ln.reference, ln.lot_fournisseur) for r in d.receptions for ln in r.lignes}
    autres |= {(x.reference, x.lot_fournisseur) for dos in d.dossiers_import for x in dos.lignes}
    for cle in [*vus, *sorted(k for k in autres - set(vus) if k[1])]:
        ecritures = vus.get(cle, [])
        fournisseurs = [
            m.fournisseur for m in ecritures if m.fournisseur and m.type != "RETOUR_FOURNISSEUR"
        ]
        ix.lots[cle] = ajouter(
            s,
            Lot(
                matiere_id=ix.matieres[cle[0]],
                numero=cle[1],
                entre_le=min((m.date for m in ecritures), default=d.mouvements[0].date),
                fournisseur_id=ix.fournisseurs.get(fournisseurs[0]) if fournisseurs else None,
            ),
        ).id


def _numeros_des_lignes(d: c.Donnees) -> dict[tuple[int, int], int]:
    """(réception, ligne) → n° de ligne de réception, d'après les entrées qui le citent ; les
    autres lignes d'une réception prennent les numéros voisins (Gestion MP les numérotait à la
    suite), pour que l'ordre des lignes reste le leur."""
    libres = {
        (i, j): (r.date_reception, ln.reference, ln.lot_fournisseur, round(ln.quantite_pesee, 3))
        for i, r in enumerate(d.receptions)
        for j, ln in enumerate(r.lignes)
    }
    numeros: dict[tuple[int, int], int] = {}
    entrees = [m for m in d.mouvements if m.type == "ENTREE_RECEPTION" and m.ligne_reception_id]
    for m in sorted(entrees, key=lambda x: x.id or 0):
        if m.contrepasse_id or m.ligne_reception_id in numeros.values():
            continue
        cle = (m.date, m.reference, m.lot_fournisseur, round(m.quantite, 3))
        place = next((k for k, v in libres.items() if v == cle), None)
        if place is not None:
            numeros[place] = m.ligne_reception_id  # type: ignore[assignment]
            del libres[place]
    return _voisins(d, numeros)


def _voisins(d: c.Donnees, numeros: dict[tuple[int, int], int]) -> dict[tuple[int, int], int]:
    """Les lignes sans entrée prennent le numéro que leur rang appelle (premier connu − rang)."""
    pris = set(numeros.values())
    suivant = itertools.count(max([*pris, 0]) + 1000)
    for i, r in enumerate(d.receptions):
        connus = [(j, numeros[(i, j)]) for j in range(len(r.lignes)) if (i, j) in numeros]
        base = connus[0][1] - connus[0][0] if connus else None
        for j in range(len(r.lignes)):
            if (i, j) in numeros:
                continue
            voulu = base + j if base is not None else None
            numeros[(i, j)] = (
                voulu if voulu is not None and voulu > 0 and voulu not in pris else next(suivant)
            )
            pris.add(numeros[(i, j)])
    return numeros


def receptions(s: Session, d: c.Donnees, ix: Index) -> dict[int, int]:
    """Les réceptions et leurs lignes ; rend {n° de ligne : réception}."""
    numeros = _numeros_des_lignes(d)
    prix = {
        (p.date_bc, p.reference, p.numero_bc, round(p.quantite, 3)): p for p in d.historique_prix
    }
    reception_de: dict[int, int] = {}
    for i, r in enumerate(d.receptions):
        validee = r.statut == "Validée"
        devise = _devise(r, prix, ix)
        rid = ajouter(
            s,
            Reception(
                numero=r.numero if validee else None,
                statut="validee" if validee else "brouillon",
                date=r.date_reception,
                fournisseur_id=ix.fournisseurs[r.fournisseur],
                devise=devise,
                numero_bl=r.numero_bl,
                facture_id=_facture(s, ix, r, devise),
                cree_par_id=ix.comptes.get(r.receptionnaire),
                validee_par_id=ix.comptes.get(r.controleur_qualite) if validee else None,
                validee_le=instant(r.validee_le or r.date_reception) if validee else None,  # type: ignore[arg-type]
            ),
        ).id
        for j, ln in enumerate(r.lignes):
            bon = ln.numero_bc or r.numero_bc
            payee = prix.get(
                (r.date_reception, ln.reference, bon or r.numero, round(ln.quantite_pesee, 3))
            )
            avec_lot = validee and ln.statut_qualite != "Refusé" and ln.lot_fournisseur
            lid = numeros[(i, j)]
            reception_de[lid] = rid
            inserer(
                s,
                ReceptionLigne,
                [
                    {
                        "id": lid,
                        "reception_id": rid,
                        "commande_ligne_id": ix.lignes_bc.get((bon, ln.reference)),
                        "matiere_id": ix.matieres[ln.reference],
                        "lot_numero": ln.lot_fournisseur,
                        "lot_id": ix.lots[(ln.reference, ln.lot_fournisseur)] if avec_lot else None,
                        "quantite_attendue": ln.quantite_commandee,
                        "quantite_bl": ln.quantite_bl,
                        "quantite_pesee": ln.quantite_pesee,
                        "nb_bobines": ln.nb_bobines,
                        "nb_palettes": ln.nb_palettes,
                        "magasin_id": ix.magasins.get(ln.magasin),
                        "qualite": QUALITES[ln.statut_qualite],
                        "observations": ln.observations,
                        "prix": payee.prix_achat if payee else 0,
                    }
                ],
            )
    return reception_de


def _devise(r: c.Reception, prix: dict[tuple[object, ...], c.LignePrix], ix: Index) -> str:
    """La devise d'une réception : celle de ses prix payés, sinon celle de son bon."""
    for ln in r.lignes:
        cle = (
            r.date_reception,
            ln.reference,
            ln.numero_bc or r.numero_bc or r.numero,
            round(ln.quantite_pesee, 3),
        )
        if cle in prix:
            return prix[cle].devise
    return ix.devises_bc.get(r.numero_bc, "MAD")


def _facture(s: Session, ix: Index, r: c.Reception, devise: str) -> int | None:
    """La facture d'une réception (une par fournisseur et numéro)."""
    if not r.numero_facture:
        return None
    if r.numero_facture not in ix.factures:
        ix.factures[r.numero_facture] = ajouter(
            s,
            Facture(
                fournisseur_id=ix.fournisseurs[r.fournisseur],
                numero=r.numero_facture,
                devise=devise,
            ),
        ).id
    return ix.factures[r.numero_facture]


def ordres(s: Session, d: c.Donnees, ix: Index) -> None:
    """Les ordres validés et leurs fabrications."""
    magasin = next(iter(ix.magasins.values()))
    for o in d.ordres:
        oid = ajouter(
            s,
            Ordre(
                numero=o.numero,
                statut="valide",
                date=o.date,
                magasin_id=magasin,
                valide_le=instant(o.valide_le or o.date),  # type: ignore[arg-type]
                commentaire=o.commentaire,
                prevu_fige=o.theorique is not None,
                taux_perte_fige=o.perte,
            ),
        ).id
        ix.ordres[o.numero] = oid
        s.add_all(
            OrdreQualite(ordre_id=oid, qualite_id=ix.qualites[q], m2=m2) for q, m2 in o.fabrications
        )
    s.flush()


def metiers(s: Session, d: c.Donnees) -> None:
    """Les métiers (le fil monté n'est pas dans les jeux réels)."""
    for x in d.metiers:
        ajouter(
            s,
            Metier(
                code=x.code,
                nom=x.nom,
                laize=x.laize,
                bobines_par_metre=x.densite,
                etages=x.etages,
                actif=x.actif,
            ),
        )


def soldes(s: Session, d: c.Donnees, ix: Index) -> None:
    """Les soldes tenus du jeu (C12 les confronte au journal)."""
    inserer(
        s,
        Solde,
        [
            {"lot_id": ix.lots[(ref, lot)], "magasin_id": ix.magasins[mag], "quantite": q}
            for (ref, lot, mag), q in (d.soldes or {}).items()
        ],
    )
