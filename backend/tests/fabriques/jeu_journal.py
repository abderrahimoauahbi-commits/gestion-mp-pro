"""Un jeu figé réécrit en base PRO, fin (lot S4) : le journal du stock (identifiants gardés ; la
jambe d'arrivée d'un transfert prend le numéro qui suit son départ, comme dans Gestion MP) et
les dossiers d'importation ; puis `batir_jeu`, qui enchaîne tout.
"""

from __future__ import annotations

from fabriques.jeu_base import (
    Index,
    commandes,
    comptes,
    inserer,
    instant,
    qualites,
    referentiels,
    reglages,
)
from fabriques.jeu_flux import TYPE_BASE, lots, metiers, ordres, receptions, soldes
from fabriques.moteur_base import ajouter
from fabriques.stock import vider
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from gestion_mp_pro.calcul import modele as c
from gestion_mp_pro.calcul.constantes import TYPES_MOUVEMENT
from gestion_mp_pro.modeles import (
    Dossier,
    DossierFrais,
    DossierFraisPart,
    DossierLigne,
    Facture,
    Motif,
    Mouvement,
    Operation,
    PosteFrais,
)

Document = tuple[str, dict[str, int]]
PRIX_PERMIS = {"OUVERTURE", "RECEPTION", "RETOUR_FOURNISSEUR", "AJUSTEMENT"}
"""`ck_mouvement_prix_entree` : seules les entrées (et ce qui recopie leur prix) ont un prix ;
Gestion MP écrivait aussi un prix sur les sorties et les transferts (sans effet sur le coût)."""


def _operation(s: Session, m: c.Mouvement, genre: str, **champs: object) -> Document:
    """Une opération validée pour une écriture du jeu."""
    o = ajouter(
        s,
        Operation(
            type=genre,
            numero=f"J{m.id}",
            statut="validee",
            date=m.date,
            validee_le=instant(m.date),
            **champs,
        ),
    )
    return "operation", {
        "operation_id": o.id,
        **({"ordre_id": champs["ordre_id"]} if "ordre_id" in champs else {}),
    }  # type: ignore[dict-item]


def _document(s: Session, m: c.Mouvement, ix: Index, reception_de: dict[int, int]) -> Document:
    """Le document d'une écriture originale (une annulation reprend celui de l'original)."""
    if m.type == "ENTREE_RECEPTION" and m.ligne_reception_id in reception_de:
        return "reception", {"reception_id": reception_de[m.ligne_reception_id]}  # type: ignore[index]
    if m.type == "SORTIE_PROD" and m.numero_of:
        return "ordre", {"ordre_id": ix.ordres[m.numero_of]}
    if m.type == "RETOUR_PRODUCTION" and m.numero_of:
        return _operation(s, m, "retour_machine", ordre_id=ix.ordres[m.numero_of])
    if m.type == "RETOUR_FOURNISSEUR":
        fournisseur = ix.fournisseurs.get(m.fournisseur) or next(iter(ix.fournisseurs.values()))
        return _operation(s, m, "retour_fournisseur", fournisseur_id=fournisseur)
    return "reprise", {}


def _ligne(
    m: c.Mouvement, ix: Index, document: Document, motifs: dict[str, int]
) -> dict[str, object]:
    """Ce qu'une écriture a de commun à ses jambes."""
    devise = m.devise or "MAD"
    return {
        "date_effet": m.date,
        "saisi_le": instant(m.date),
        "type": TYPE_BASE[m.type],
        "matiere_id": ix.matieres[m.reference],
        "lot_id": ix.lots[(m.reference, m.lot_fournisseur)],
        "prix": m.prix_unite if TYPE_BASE[m.type] in PRIX_PERMIS else 0,
        "devise": devise,
        "cours": m.cours if m.cours and devise != "MAD" else None,
        "document": document[0],
        **document[1],
        "document_numero": m.reference_doc,
        "contrepasse_id": m.contrepasse_id,
        "motif_id": motifs.get(m.motif_retour),
        "auteur_id": ix.comptes.get(m.utilisateur),
    }


def journal(s: Session, d: c.Donnees, ix: Index, reception_de: dict[int, int]) -> None:
    """Le journal du jeu en base : quantités signées, deux jambes par transfert."""
    motifs: dict[str, int] = {}
    for code, ident in s.execute(
        select(Motif.code_r, Motif.id).order_by(Motif.ordre, Motif.id)
    ).all():
        if code:
            motifs.setdefault(code, ident)
    documents: dict[int, Document] = {}
    lignes: list[dict[str, object]] = []
    for m in sorted(d.mouvements, key=lambda x: x.id or 0):
        assert m.id is not None
        doc = documents.get(m.contrepasse_id or 0) or _document(s, m, ix, reception_de)
        documents[m.id] = doc
        commun = _ligne(m, ix, doc, motifs)
        if m.type == "TRANSFERT_MAGASIN":
            lignes.append(
                {
                    **commun,
                    "id": m.id,
                    "magasin_id": ix.magasins[m.magasin_source],
                    "quantite": -m.quantite,
                    "paire_id": m.id,
                }
            )
            lignes.append(
                {
                    **commun,
                    "id": m.id + 1,
                    "magasin_id": ix.magasins[m.magasin_destination],
                    "quantite": m.quantite,
                    "paire_id": m.id,
                }
            )
            continue
        signe = TYPES_MOUVEMENT[m.type][1]
        magasin = m.magasin_source if signe < 0 else m.magasin_destination
        lignes.append(
            {
                **commun,
                "id": m.id,
                "magasin_id": ix.magasins[magasin],
                "quantite": m.quantite * signe,
            }
        )
    s.flush()
    inserer(s, Mouvement, lignes)


def _lignes_et_frais(
    s: Session, ix: Index, did: int, x: c.DossierImport, postes: dict[str, int]
) -> None:
    """Les marchandises d'un dossier (numéros gardés), ses frais et leurs parts figées."""
    inserer(
        s,
        DossierLigne,
        [
            {
                "id": ln.id,
                "dossier_id": did,
                "reception_ligne_id": ln.ligne_reception_id,
                "matiere_id": ix.matieres[ln.reference],
                "lot_id": ix.lots.get((ln.reference, ln.lot_fournisseur)),
                "fournisseur_id": ix.fournisseurs.get(ln.fournisseur),
                "quantite_kg": ln.quantite,
                "valeur_devise": ln.valeur_devise,
                "devise": ln.devise,
                "cours": ln.cours if ln.cours and ln.devise != "MAD" else None,
                "cours_origine": "reprise" if ln.cours and ln.devise != "MAD" else None,
            }
            for ln in x.lignes
        ],
    )
    for ch in x.charges:
        fid = ajouter(
            s,
            DossierFrais(
                dossier_id=did,
                poste_id=postes[ch.poste],
                montant=ch.montant,
                ligne_id=ch.ligne,
                piece=ch.piece,
                commentaire=ch.commentaire,
            ),
        ).id
        s.add_all(
            DossierFraisPart(frais_id=fid, ligne_id=lig, montant=mt, origine="reprise")
            for lig, mt in ch.parts.items()
        )


def dossiers(s: Session, d: c.Donnees, ix: Index) -> None:
    """Les dossiers d'importation, leurs marchandises (numéros gardés), frais et parts."""
    postes = dict(s.execute(select(PosteFrais.code, PosteFrais.id)).all())
    for x in d.dossiers_import:
        nn, aa = x.numero.split("/")
        facture = ix.factures.get(x.facture) if x.facture else None
        if facture is not None:
            s.execute(
                update(Facture)
                .where(Facture.id == facture)
                .values(montant=x.facture_montant or None, devise=x.facture_devise or "MAD")
            )
        did = ajouter(
            s,
            Dossier(
                numero=x.numero,
                annee=2000 + int(aa),
                rang=int(nn),
                libelle=x.libelle,
                date_arrivee=x.date_arrivee,
                banque=x.banque,
                commentaire=x.commentaire,
                statut="clos" if x.statut == "Clos" else "ouvert",
                facture_id=facture,
                clos_le=instant(x.date_arrivee or d.mouvements[0].date)
                if x.statut == "Clos"
                else None,
            ),
        ).id
        _lignes_et_frais(s, ix, did, x, postes)
    s.flush()


def batir_jeu(s: Session, d: c.Donnees) -> Index:
    """Le jeu entier en base, dans la transaction de l'essai (base vidée d'abord)."""
    vider(s)
    ix = Index()
    reglages(s, d.parametres)
    comptes(s, d, ix)
    referentiels(s, d, ix)
    qualites(s, d, ix)
    commandes(s, d, ix)
    lots(s, d, ix)
    reception_de = receptions(s, d, ix)
    ordres(s, d, ix)
    journal(s, d, ix, reception_de)
    soldes(s, d, ix)
    dossiers(s, d, ix)
    metiers(s, d)
    s.flush()
    return ix
