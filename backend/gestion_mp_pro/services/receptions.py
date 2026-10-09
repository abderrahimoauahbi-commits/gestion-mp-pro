"""Les réceptions : un camion, une ou plusieurs commandes, entières ou partielles (REGLES § 3 ;
`gestion_mp/api/receptions.py`, corrigé : A-01, A-04, A-09, A-11, D-02, D-08, C-16).

- **Créer** : une saisie peut porter des bons en deux devises ; elle donne une réception par
  devise, chacune avec sa facture, **dans une seule transaction** (A-09) : une seconde devise
  refusée ne laisse pas la première en brouillon.
- Un brouillon se **corrige** (lignes remplacées) et se **supprime** ; sans numéro jusqu'à la
  validation (M65). Son recalage s'écrit à la modification et à la validation.
- **Valider** : verrou des bons (excédent, deux postes), blocages, quarantaine pour une ligne
  sous réserve, lot interne `LOT-AAAA-NNNN` numéroté ici (jamais avant : aucun trou), numéro
  `REC-AAAA-NNNN`, lots et entrées en stock par `services/stock.py` (cours figé du bon), puis
  soldes des bons recalés (une ligne en quarantaine reste attendue : D-02).
- **Annuler** : contre-passation de toutes ses entrées (datées de l'original) ; une réception
  toute refusée s'annule sans mouvement (A-01) ; une réception dans un dossier s'en détache
  d'abord.
- La facture d'une réception validée se complète ou se corrige ici (route 174).
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import Reception, ReceptionLigne
from gestion_mp_pro.modeles.enums import (
    DocumentMouvement,
    QualiteReception,
    Role,
    SerieNumero,
    StatutDocument,
    TypeMouvement,
)
from gestion_mp_pro.services import (
    audit,
    brouillons,
    factures,
    horloge,
    lots,
    numerotation,
    periode,
    stock,
)
from gestion_mp_pro.services.brouillons import Brouillon
from gestion_mp_pro.services.commandes_socle import recaler_soldes
from gestion_mp_pro.services.comptes import Acteur, message_refus
from gestion_mp_pro.services.receptions_blocages import blocages, contexte
from gestion_mp_pro.services.receptions_saisie import Saisie, preparer
from gestion_mp_pro.services.receptions_socle import (
    appliquer_recalage,
    bons,
    charger,
    commandes_de,
    detacher_d_abord,
    dossier_de,
    lignes_triees,
    nom_reception,
    quarantaine,
    toucher,
    verifier,
    verrouiller_bons,
)

VOIENT_LES_BROUILLONS = frozenset({Role.direction, Role.achats})


def brouillons_a_valider(s: Session, role: str) -> int | None:
    """La pastille « Réceptions » du menu : les brouillons qui attendent leur validation
    (direction et achats ; `None` pour les autres rôles)."""
    if role not in VOIENT_LES_BROUILLONS:
        return None
    requete = select(func.count()).where(Reception.statut == StatutDocument.brouillon)
    return int(s.scalar(requete) or 0)


# ── Brouillons ───────────────────────────────────────────────────────────────


def _nouvelle(
    s: Session, qui: audit.Qui, e: Saisie, devise: str, lignes: list[ReceptionLigne]
) -> Reception:
    """Une réception en brouillon d'une devise (sans numéro)."""
    r = Reception(
        date=e.date,
        fournisseur_id=e.fournisseur_id,
        devise=devise,
        numero_bl=e.numero_bl.strip(),
        controle_par=e.controle_par.strip(),
        observations=e.observations,
        cree_par_id=qui.id,
        lignes=lignes,
    )
    s.add(r)
    s.flush()
    return r


def creer(s: Session, qui: audit.Qui, e: Saisie) -> list[Reception]:
    """Les brouillons d'un camion, un par devise, tous ou aucun (A-09, R8r)."""
    prep = preparer(s, e)
    creees: list[Reception] = []
    for devise, lignes in prep.par_devise.items():
        r = _nouvelle(s, qui, e, devise, lignes)
        r.facture_id = factures.attacher(
            s, qui, f=prep.fournisseur, e=e.factures.get(devise), devise=devise, reception_id=r.id
        )
        appliquer_recalage(r, bons(s, [r]))
        audit.creation(
            s,
            qui,
            "création réception",
            r,
            detail=f"{nom_reception(r)} · {prep.fournisseur.nom} · {len(lignes)} ligne(s)",
        )
        creees.append(r)
    return creees


def _brouillon(s: Session, rid: int, version: int, *, valide: str, annule: str) -> Reception:
    """Le brouillon verrouillé, à sa version ; refus si la réception est validée ou annulée."""
    r = charger(s, rid, verrou=True)
    verifier(s, r, version)
    if r.statut == StatutDocument.validee:
        raise Refus.etat(valide, code="deja_valide")
    if r.statut == StatutDocument.annulee:
        raise Refus.etat(annule, code="deja_annule")
    return r


def modifier(s: Session, qui: audit.Qui, rid: int, version: int, e: Saisie) -> Reception:
    """Corrige un brouillon : en-tête, facture, toutes ses lignes remplacées, puis recalage
    (R-RCP-12). Un brouillon garde une seule devise (X-RCP-01)."""
    r = _brouillon(
        s,
        rid,
        version,
        valide="Une réception validée est entrée en stock : elle ne se modifie plus. L'annuler "
        "(elle se contre-passe), puis en saisir une nouvelle.",
        annule="Cette réception est annulée : elle ne se modifie plus.",
    )
    prep = preparer(s, e)
    if len(prep.par_devise) > 1:
        raise Refus.saisie(
            f"Une réception ne mêle pas deux devises ({', '.join(sorted(prep.par_devise))}) : "
            "chaque devise a sa facture. Enregistrer une réception par devise (même BL, même "
            "date).",
            code="devise_incompatible",
        )
    devise, lignes = next(iter(prep.par_devise.items()))
    with audit.suivre(s, qui, "modification réception", r) as geste:
        r.date, r.fournisseur_id, r.devise = e.date, e.fournisseur_id, devise
        r.numero_bl, r.controle_par = e.numero_bl.strip(), e.controle_par.strip()
        r.observations = e.observations
        r.facture_id = factures.attacher(
            s, qui, f=prep.fournisseur, e=e.factures.get(devise), devise=devise, reception_id=r.id
        )
        r.lignes.clear()
        s.flush()
        r.lignes.extend(lignes)
        s.flush()
        appliquer_recalage(r, bons(s, [r]))
        toucher(r)
        s.flush()
        geste.detail = f"{nom_reception(r)} · {len(lignes)} ligne(s)"
    return r


def supprimer(s: Session, qui: audit.Qui, rid: int, version: int) -> None:
    """Supprime un brouillon : rien n'est entré en stock, aucun numéro n'est perdu."""
    r = _brouillon(
        s,
        rid,
        version,
        valide="Une réception validée ne se supprime pas : l'annuler.",
        annule="Une réception annulée ne se supprime pas : elle reste la trace du camion.",
    )
    audit.suppression(s, qui, "suppression réception", r, detail=nom_reception(r))
    s.delete(r)
    s.flush()


# ── Validation ───────────────────────────────────────────────────────────────


def _entrer(
    s: Session,
    qui: audit.Qui,
    r: Reception,
    x: ReceptionLigne,
    *,
    numero: str,
    cours_du_bon: Callable[[ReceptionLigne], Decimal | None],
) -> None:
    """Le lot (créé ou complété) et l'entrée en stock d'une ligne non refusée."""
    if x.magasin_id is None:  # pragma: no cover — écarté par les blocages
        raise Refus.saisie("Ligne sans magasin.")
    numero_lot = lots.numero_interne(s, r.date) if x.lot_interne else x.lot_numero
    poids = x.quantite_pesee / x.nb_bobines if x.nb_bobines else 0
    lot = lots.lot_ou_creer(
        s,
        x.matiere_id,
        numero_lot,
        r.date,
        fournisseur_id=r.fournisseur_id,
        poids_bobine=poids,
        interne=x.lot_interne,
    )
    stock.ecrire(
        s,
        type=TypeMouvement.RECEPTION,
        lot=lot,
        magasin_id=x.magasin_id,
        quantite=x.quantite_pesee,
        jour=r.date,
        piece=stock.Piece(DocumentMouvement.reception, r.id, numero),
        auteur_id=qui.id,
        prix=x.prix,
        devise=r.devise,
        cours=cours_du_bon(x),
        liens=stock.Liens(
            commentaire="sous réserve" if x.qualite == QualiteReception.reserve else ""
        ),
    )
    x.lot_id = lot.id


def valider(s: Session, qui: audit.Qui, rid: int, version: int) -> Reception:
    """Écrit la réception d'un coup : lots, entrées en stock, prix payés (R-RCP-18 à 26)."""
    r = _brouillon(
        s,
        rid,
        version,
        valide="Cette réception est déjà validée.",
        annule="Cette réception est annulée : elle ne se valide plus.",
    )
    periode.date_permise(s, r.date)
    verrouiller_bons(s, r)
    b = bons(s, [r])
    appliquer_recalage(r, b)
    q = quarantaine(s)
    manques = blocages(s, r, contexte(s, [r], b, q))
    if manques:
        raise Refus(manques[0].code, manques[0].message)
    acceptees = [x for x in lignes_triees(r) if x.qualite != QualiteReception.refuse]
    avant = audit.photo(r)
    numero = numerotation.numero(s, SerieNumero.REC, r.date)
    for x in acceptees:
        if x.qualite == QualiteReception.reserve and q is not None:
            x.magasin_id = q.id

    def cours_du_bon(x: ReceptionLigne) -> Decimal | None:
        """Le cours figé par le bon dans la devise de la réception, sinon celui du jour."""
        if x.commande_ligne_id is None:
            return None
        c = b.bon(x.commande_ligne_id)
        return c.cours if c.devise == r.devise and c.cours else None

    for x in acceptees:
        _entrer(s, qui, r, x, numero=numero, cours_du_bon=cours_du_bon)
    # Numéro et statut ensemble (contrainte `numero ⇔ validée`).
    r.numero, r.statut = numero, StatutDocument.validee
    r.validee_par_id, r.validee_le = qui.id, horloge.maintenant()
    s.flush()
    recaler_soldes(s, qui, commandes_de(r, b), "réception")
    detail = (
        f"{numero} · {len(acceptees)} entrée(s)"
        if acceptees
        else f"{numero} · tout refusé, rien n'entre en stock"
    )
    a, apres = audit.differences(avant, audit.photo(r))
    audit.journal(
        s,
        qui,
        "validation réception",
        "reception",
        r.id,
        numero=numero,
        detail=detail,
        avant=a,
        apres=apres,
    )
    return r


# ── Annulation ───────────────────────────────────────────────────────────────


def annuler(s: Session, qui: audit.Qui, rid: int, version: int, motif: str) -> Reception:
    """Annule une réception validée : ses entrées sont contre-passées (si la matière est encore
    là) ; toute refusée, elle s'annule sans mouvement (A-01). Les bons se recalent : soldé de
    lui-même et plus livré, un bon se rouvre ; soldé à la main, il le reste (R-RCP-27 à 29)."""
    r = charger(s, rid, verrou=True)
    verifier(s, r, version)
    if r.statut == StatutDocument.annulee:
        raise Refus.etat("Cette réception est déjà annulée.", code="deja_annule")
    if r.statut == StatutDocument.brouillon:
        raise Refus.etat("Seule une réception validée s'annule ; un brouillon se supprime.")
    dossier = dossier_de(s, r)
    if dossier is not None:
        raise Refus.etat(detacher_d_abord(dossier, "l'annuler"), code="documents_lies")
    numero = r.numero or ""
    if any(x.qualite != QualiteReception.refuse for x in r.lignes):
        stock.contrepasser(s, stock.Piece(DocumentMouvement.reception, r.id, numero), qui.id)
    motif = motif.strip()
    with audit.suivre(
        s, qui, "annulation réception", r, numero=numero, detail=f"{numero} · {motif}"
    ):
        r.statut, r.annulee_le, r.annulee_par_id = (
            StatutDocument.annulee,
            horloge.maintenant(),
            qui.id,
        )
        r.annulation_motif = motif
        s.flush()
    recaler_soldes(s, qui, commandes_de(r, bons(s, [r])), "annulation de réception")
    return r


# ── « À valider » (registre de `services/brouillons.py`, lot D5) ─────────────

RANG_RECEPTION = 0
"""Le même jour, une réception passe en premier : elle apporte la matière (S131)."""


class _GenreReception:
    """Les réceptions en brouillon dans « À valider » (direction et achats seulement)."""

    nom = "reception"

    def lister(self, s: Session, qui: Acteur) -> list[Brouillon]:
        """Les brouillons de réception, avec leurs blocages (aucun pour les autres rôles : les
        réceptions leur sont fermées)."""
        if qui.role not in VOIENT_LES_BROUILLONS:
            return []
        from gestion_mp_pro.services.receptions_lecture import FiltresReceptions
        from gestion_mp_pro.services.receptions_liste import liste

        return [
            Brouillon(
                genre=self.nom,
                type="reception",
                id=r.id,
                version=r.version,
                date=r.date,
                libelle="Réception",
                resume=" · ".join(
                    filter(None, [r.fournisseur, ", ".join(b.numero for b in r.commandes)])
                ),
                quantite=r.pese,
                cree_par=r.cree_par,
                cree_le=None,
                lien=f"/receptions/{r.id}",
                rang=RANG_RECEPTION,
                peut_valider=True,
                valide_par="la direction, responsable achats",
                blocages=r.blocages,
            )
            for r in liste(s, FiltresReceptions(statut=StatutDocument.brouillon))
        ]

    def valider(self, s: Session, qui: Acteur, ident: int, version: int | None) -> str:
        """La validation à l'unité (route 172) ; sans version, celle de la base."""
        if qui.role not in VOIENT_LES_BROUILLONS:
            raise Refus.droit(message_refus(VOIENT_LES_BROUILLONS))
        if version is None:
            version = charger(s, ident).version
        return valider(s, qui, ident, version).numero or ""


GENRE_BROUILLON = _GenreReception()
brouillons.inscrire(GENRE_BROUILLON)
