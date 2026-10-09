"""Le seul chemin d'écriture du stock (`services/stock.py`, lot S4) : refus SR1–SR12 mot pour
mot, suspension par inventaire limitée au périmètre (K2), couvert à sa date, cours figé,
transfert en deux lignes liées, contre-passation unique datée comme l'original.
"""

from __future__ import annotations

import ast
from decimal import Decimal
from pathlib import Path

import pytest
from fabriques.stock import (
    JOUR,
    REPRISE,
    autre_magasin,
    entree,
    inventaire_ouvert,
    jour,
    lot,
    magasin,
    matiere,
    s,
    sortie,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import Devise, Mouvement, Parametre, Solde
from gestion_mp_pro.modeles.enums import DocumentMouvement, TypeMagasin, TypeMouvement
from gestion_mp_pro.services import stock

__all__ = ["s"]


def _solde(s: Session, lot_id: int, magasin_id: int) -> Decimal:
    q = s.scalar(
        select(Solde.quantite).where(Solde.lot_id == lot_id, Solde.magasin_id == magasin_id)
    )
    return q if q is not None else Decimal(0)


def _refus(fonction, *args, **kw) -> Refus:  # type: ignore[no-untyped-def]
    with pytest.raises(Refus) as exc:
        fonction(*args, **kw)
    return exc.value


def test_une_ecriture_nulle_est_refusee(s: Session) -> None:
    """SR1 (une quantité sous le gramme est nulle une fois arrondie)."""
    x = lot(s, matiere(s))
    for q in (0, 0.0004):
        r = _refus(entree, s, x, q)
        assert (r.http, r.code) == (422, "quantite_invalide")
        assert r.detail == "Une écriture de stock ne peut pas être nulle."


def test_la_date_doit_etre_permise(s: Session) -> None:
    """SR2 : ni futur, ni avant 2000, ni période close (`periode.date_permise`, D1–D3)."""
    x = lot(s, matiere(s))
    assert _refus(entree, s, x, 10, jour(1)).code == "date_future"
    assert _refus(entree, s, x, 10, JOUR.replace(year=1999)).code == "date_trop_ancienne"
    s.get(Parametre, "date_cloture").valeur = jour(-5).isoformat()  # type: ignore[union-attr]
    r = _refus(entree, s, x, 10, jour(-5))
    assert (r.http, r.code) == (409, "periode_close")


def test_magasin_inconnu_ou_desactive(s: Session) -> None:
    """SR3, SR4 : un magasin désactivé ne reçoit plus rien, mais on peut encore en sortir."""
    x = lot(s, matiere(s))
    r = stock.ecrire(
        s, type=TypeMouvement.OUVERTURE, lot=x, magasin_id=magasin(s).id, quantite=5,
        jour=JOUR, piece=REPRISE, auteur_id=None,
    )  # fmt: skip
    assert r.quantite == Decimal("5.000")
    r2 = _refus(
        stock.ecrire, s, type=TypeMouvement.OUVERTURE, lot=x, magasin_id=999_999, quantite=5,
        jour=JOUR, piece=REPRISE, auteur_id=None,
    )  # fmt: skip
    assert (r2.http, r2.code, r2.detail) == (422, "valeur_inconnue", "Magasin inconnu.")
    g = autre_magasin(s, code="VIEUX-MAG")
    entree(s, x, 30, g=g)
    g.actif = False
    r3 = _refus(entree, s, x, 1, g=g)
    assert r3.http == 422
    assert r3.detail == "Le magasin « VIEUX-MAG » est désactivé : il ne reçoit plus rien."
    sortie(s, x, 30, g=g)
    assert _solde(s, x.id, g.id) == 0


def test_le_stock_ne_passe_jamais_sous_zero_au_gramme(s: Session) -> None:
    """SR6. Hérité : test_parcours::test_le_stock_ne_passe_jamais_sous_zero ;
    test_audit2_atelier::test_le_refus_du_stock_parle_en_kilos_au_gramme."""
    m = matiere(s, reference="Fil gramme")
    x = lot(s, m, numero="G-1")
    entree(s, x, 1000)
    r = _refus(sortie, s, x, "1000.5")
    assert (r.http, r.code) == (409, "stock_insuffisant")
    assert r.detail == (
        "Le lot « G-1 » de « Fil gramme » ne porte que 1 000,000 kg dans « Magasin principal », "
        "1 000,500 kg demandés. Choisir un autre lot, ou faire d'abord un ajustement justifié si "
        "la matière est bien là."
    )
    assert _refus(sortie, s, x, 10_000).code == "stock_insuffisant"
    sortie(s, x, 1000)
    assert _solde(s, x.id, magasin(s).id) == 0


def test_une_sortie_datee_avant_l_entree_du_lot_est_refusee(s: Session) -> None:
    """SR8. Hérité : test_valeur_et_dates::test_une_sortie_datee_avant_l_entree_du_lot_est_refusee
    (transfert, ajustement, retour au fournisseur datés d'hier sur un lot entré aujourd'hui)."""
    m = matiere(s, reference="Fil du matin")
    x = lot(s, m, numero="M-1")
    entree(s, x, 100)
    for type_ in (TypeMouvement.AJUSTEMENT, TypeMouvement.RETOUR_FOURNISSEUR):
        r = _refus(sortie, s, x, 10, jour(-1), type=type_)
        assert (r.http, r.code) == (409, "lot_absent_a_la_date")
        assert r.detail == (
            "Le lot « M-1 » de « Fil du matin » n'est entré dans « Magasin principal » que le "
            "08/10/2026 : une écriture datée du 07/10/2026 ne peut pas le prendre. La dater au "
            "jour où la matière était là, ou choisir un lot présent à cette date."
        )
    g = autre_magasin(s)
    r = _refus(
        stock.transferer, s, lot=x, source_id=magasin(s).id, destination_id=g.id, quantite=10,
        jour=jour(-1), piece=REPRISE, auteur_id=None,
    )  # fmt: skip
    assert r.code == "lot_absent_a_la_date"
    assert _solde(s, x.id, magasin(s).id) == 100


def test_une_ecriture_ne_creuse_pas_le_lot_apres_sa_date(s: Session) -> None:
    """SR9. Hérité : test_valeur_et_dates::test_une_ecriture_ne_creuse_pas_le_lot_apres_sa_date :
    100 (J−10), −80 (J−3), +80 (hier) ; −50 à J−5 → « Au J−3, il n'y avait que 20,00 kg »."""
    m = matiere(s, reference="Fil creux")
    x = lot(s, m, numero="C-1", entre_le=jour(-10))
    entree(s, x, 100, jour(-10))
    sortie(s, x, 80, jour(-3))
    entree(s, x, 80, jour(-1))
    r = _refus(sortie, s, x, 50, jour(-5))
    assert (r.http, r.code) == (409, "stock_insuffisant")
    assert r.detail == (
        "Au 05/10/2026, il n'y avait que 20,00 kg du lot « C-1 » de « Fil creux » dans "
        "« Magasin principal », 50,00 kg demandés au 03/10/2026 : la matière est sortie depuis "
        "par d'autres écritures. Choisir un autre lot, ou dater l'écriture après l'entrée de la "
        "matière."
    )
    sortie(s, x, 50, jour(-1))
    assert _solde(s, x.id, magasin(s).id) == 50


def test_le_manque_le_jour_meme_prime(s: Session) -> None:
    """S23 : si le jour même ne suffit pas, c'est ce jour-là que le refus nomme (« . »)."""
    m = matiere(s, reference="Fil court")
    x = lot(s, m, numero="K-1", entre_le=jour(-4))
    entree(s, x, 30, jour(-4))
    entree(s, x, 100, jour(-1))
    r = _refus(sortie, s, x, 50, jour(-2))
    assert r.detail.startswith("Au 06/10/2026, il n'y avait que 30,00 kg du lot « K-1 »")
    assert "demandés au 06/10/2026. Choisir un autre lot" in r.detail


def test_l_inventaire_ne_suspend_que_son_perimetre(s: Session) -> None:
    """SR5 et K2 (DECISIONS N3, T2) : la matière comptée est suspendue dans le magasin compté
    (entrées comprises) ; une autre matière, ou un autre magasin, bouge librement ; un
    inventaire global suspend la matière partout ; l'inventaire lui-même écrit."""
    comptee, libre = matiere(s), matiere(s)
    x, y = lot(s, comptee), lot(s, libre)
    entree(s, x, 100)
    entree(s, y, 100)
    g = autre_magasin(s)
    i = inventaire_ouvert(s, magasin(s), [comptee], numero="INV-2026-0042")
    for f in (lambda: sortie(s, x, 10), lambda: entree(s, x, 10)):
        r = _refus(f)
        assert (r.http, r.code) == (409, "inventaire_en_cours")
        assert r.detail == (
            "L'inventaire INV-2026-0042 est en cours sur « Magasin principal » : les mouvements "
            "y sont suspendus jusqu'à sa validation."
        )
    sortie(s, y, 10)
    entree(s, x, 5, g=g)
    piece = stock.Piece(DocumentMouvement.inventaire, i.id, i.numero)
    entree(s, x, -3, type=TypeMouvement.AJUSTEMENT, piece=piece)
    inventaire_ouvert(s, None, [libre], numero="INV-2026-0043")
    assert "INV-2026-0043" in _refus(sortie, s, y, 1, g=magasin(s)).detail
    entree(s, x, 1, g=g)


def test_le_cours_est_fige_sur_l_ecriture(s: Session) -> None:
    """S18, I16 : une entrée payée en dollars garde le cours du jour de l'écriture (ou celui
    figé par la commande) ; changer le cours demain ne la réécrit pas ; son annulation le
    recopie. Le dirham et un prix nul n'ont pas de cours ; une devise inconnue est refusée."""
    x = lot(s, matiere(s))
    usd = s.get(Devise, "USD")
    assert usd is not None
    au_jour = entree(s, x, 100, prix="2.5", devise="usd")
    fige = entree(s, x, 50, prix="2.5", devise="USD", cours="9.5")
    usd.cours = Decimal("11.25")
    s.flush()
    s.refresh(au_jour)
    assert (au_jour.devise, au_jour.cours, fige.cours) == ("USD", Decimal("10"), Decimal("9.5"))
    assert entree(s, x, 10, prix=3).cours is None
    assert entree(s, x, 10, devise="USD").cours is None
    assert _refus(entree, s, x, 10, prix=1, devise="XXX").code == "valeur_inconnue"
    lignes = stock.contrepasser_mouvements(s, [au_jour], None)
    inverse = s.scalars(select(Mouvement).where(Mouvement.contrepasse_id == au_jour.id)).one()
    assert (lignes, inverse.cours, inverse.prix) == (1, Decimal("10"), Decimal("2.5"))


def test_un_transfert_ecrit_deux_lignes_liees(s: Session) -> None:
    """S35, SR11 : la sortie de la source (sa paire est elle-même), puis l'entrée."""
    x = lot(s, matiere(s))
    entree(s, x, 100)
    g = autre_magasin(s)
    depart, arrivee = stock.transferer(
        s, lot=x, source_id=magasin(s).id, destination_id=g.id, quantite="40.5", jour=JOUR,
        piece=REPRISE, auteur_id=None, motif_texte="Rangement",
    )  # fmt: skip
    assert (depart.paire_id, arrivee.paire_id) == (depart.id, depart.id)
    assert (depart.quantite, arrivee.quantite) == (Decimal("-40.500"), Decimal("40.500"))
    assert (depart.type, arrivee.motif_texte) == (TypeMouvement.TRANSFERT, "Rangement")
    assert (_solde(s, x.id, magasin(s).id), _solde(s, x.id, g.id)) == (
        Decimal("59.5"),
        Decimal("40.5"),
    )
    r = _refus(
        stock.transferer, s, lot=x, source_id=g.id, destination_id=g.id, quantite=1, jour=JOUR,
        piece=REPRISE, auteur_id=None,
    )  # fmt: skip
    assert (r.http, r.detail) == (422, "Un transfert va d'un magasin à un autre.")


def test_contrepasser_un_document_une_fois_date_comme_l_original(s: Session) -> None:
    """S40–S45, SR12 : l'inverse de chaque ligne, datée comme l'original (la saisie dit quand
    on annule), sorties défaites d'abord, paire de transfert gardée ; une fois."""
    from fabriques.stock import utilisateur  # noqa: PLC0415

    x = lot(s, matiere(s), entre_le=jour(-6))
    entree(s, x, 100, jour(-6))
    g = autre_magasin(s)
    piece = stock.Piece(DocumentMouvement.reprise)
    stock.transferer(
        s, lot=x, source_id=magasin(s).id, destination_id=g.id, quantite=30, jour=jour(-4),
        piece=piece, auteur_id=None,
    )  # fmt: skip
    originaux = list(
        s.scalars(
            select(Mouvement).where(Mouvement.lot_id == x.id, Mouvement.date_effet == jour(-4))
        )
    )
    qui = utilisateur(s, "Sara")
    assert stock.contrepasser_mouvements(s, originaux, qui.id) == 2
    inverses = list(
        s.scalars(
            select(Mouvement)
            .where(Mouvement.contrepasse_id.in_([o.id for o in originaux]))
            .order_by(Mouvement.id)
        )
    )
    assert [i.date_effet for i in inverses] == [jour(-4), jour(-4)]
    assert [i.quantite for i in inverses] == [Decimal("30.000"), Decimal("-30.000")]
    assert inverses[0].paire_id == inverses[0].id == inverses[1].paire_id
    assert inverses[0].commentaire == f"Annulation du mouvement n°{inverses[0].contrepasse_id}"
    assert {i.auteur_id for i in inverses} == {qui.id}
    assert (_solde(s, x.id, magasin(s).id), _solde(s, x.id, g.id)) == (100, 0)
    with pytest.raises(Refus) as deja:
        stock.contrepasser_mouvements(s, originaux[:1], qui.id)
    assert (deja.value.code, deja.value.detail) == ("deja_annule", "Ce document a déjà été annulé.")


def test_contrepasser_un_document_par_sa_cle(s: Session) -> None:
    """`contrepasser(piece)` vise les lignes du document qui ne sont ni annulées ni des
    annulations ; une seconde fois : SR12. Refusée si la matière est déjà repartie (SR6)."""
    from gestion_mp_pro.modeles import Inventaire  # noqa: PLC0415

    x = lot(s, matiere(s, reference="Fil compté"), numero="I-1")
    entree(s, x, 100)
    i = Inventaire(numero="INV-ESSAI-1", date=JOUR, statut="valide", valide_le=func.now())
    s.add(i)
    s.flush()
    piece = stock.Piece(DocumentMouvement.inventaire, i.id, i.numero)
    entree(s, x, 20, type=TypeMouvement.AJUSTEMENT, piece=piece)
    sortie(s, x, 110)
    r = _refus(stock.contrepasser, s, piece, None)
    assert r.code == "stock_insuffisant" and "ne porte que 10,000 kg" in r.detail
    entree(s, x, 20)
    assert stock.contrepasser(s, piece, None) == 1
    assert _refus(stock.contrepasser, s, piece, None).code == "deja_annule"


MODULES_DU_MODELE = {"gestion_mp_pro.modeles", "gestion_mp_pro.modeles.stock"}


def _ecritures_du_journal(source: str) -> list[int]:
    """Les lignes qui créent un mouvement hors du chemin : `Mouvement(…)` du modèle (pas la
    dataclass du moteur), `insert(Mouvement)`, ou un `INSERT INTO mouvement` écrit en SQL."""
    arbre = ast.parse(source)
    noms, modules = set(), set()
    for noeud in ast.walk(arbre):
        if isinstance(noeud, ast.ImportFrom) and noeud.module in MODULES_DU_MODELE:
            noms |= {a.asname or a.name for a in noeud.names if a.name == "Mouvement"}
        if isinstance(noeud, ast.ImportFrom) and noeud.module == "gestion_mp_pro":
            modules |= {a.asname or a.name for a in noeud.names if a.name == "modeles"}
        if isinstance(noeud, ast.Import):
            modules |= {a.asname or a.name for a in noeud.names if a.name in MODULES_DU_MODELE}

    def est_le_modele(n: ast.expr) -> bool:
        if isinstance(n, ast.Name):
            return n.id in noms
        return (
            isinstance(n, ast.Attribute)
            and n.attr == "Mouvement"
            and (isinstance(n.value, ast.Name) and n.value.id in modules)
        )

    lignes = []
    for noeud in ast.walk(arbre):
        if isinstance(noeud, ast.Call) and (
            est_le_modele(noeud.func)
            or (
                isinstance(noeud.func, ast.Name)
                and noeud.func.id == "insert"
                and any(est_le_modele(a) for a in noeud.args)
            )
        ):
            lignes.append(noeud.lineno)
        if (
            isinstance(noeud, ast.Constant)
            and isinstance(noeud.value, str)
            and "insert into mouvement" in noeud.value.lower()
        ):
            lignes.append(noeud.lineno)
    return lignes


def test_seul_chemin_d_ecriture() -> None:
    """I01 : aucun mouvement créé dans le paquet hors de `services/stock.py` et de la reprise
    (l'essai voit `Mouvement(…)`, `insert(Mouvement)` et le SQL écrit à la main)."""
    paquet = Path(__file__).resolve().parents[1] / "gestion_mp_pro"
    fautifs = {
        f.relative_to(paquet).as_posix(): lignes
        for f in paquet.rglob("*.py")
        if (lignes := _ecritures_du_journal(f.read_text(encoding="utf-8")))
    }
    permis = {k for k in fautifs if k == "services/stock.py" or k.startswith("reprise/")}
    assert "services/stock.py" in permis
    assert {k: v for k, v in fautifs.items() if k not in permis} == {}


def test_l_essai_du_seul_chemin_voit_les_detours() -> None:
    """L'essai précédent n'est pas aveugle : il voit les trois façons d'écrire au journal."""
    assert _ecritures_du_journal("from gestion_mp_pro.modeles import Mouvement\nMouvement(id=1)")
    assert _ecritures_du_journal("from gestion_mp_pro import modeles as m\nm.Mouvement(id=1)")
    assert _ecritures_du_journal(
        "from gestion_mp_pro.modeles.stock import Mouvement as M\ninsert(M).values()"
    )
    assert _ecritures_du_journal("x = 'INSERT INTO mouvement (id) VALUES (1)'")
    assert not _ecritures_du_journal(
        "from gestion_mp_pro.calcul.modele import Mouvement\nMouvement(date=1)"
    )


def test_les_soldes_sont_le_cache_exact_du_journal(s: Session) -> None:
    """I02 : après des entrées, sorties, transferts et annulations, chaque solde égale la
    somme du journal de son lot dans son magasin.
    Hérité : test_parcours::test_les_soldes_egalent_le_journal."""
    x = lot(s, matiere(s))
    entree(s, x, "12.345")
    sortie(s, x, "2.005")
    g = autre_magasin(s)
    stock.transferer(
        s, lot=x, source_id=magasin(s).id, destination_id=g.id, quantite=5, jour=JOUR,
        piece=REPRISE, auteur_id=None,
    )  # fmt: skip
    journal = dict(
        s.execute(
            select(Mouvement.magasin_id, func.sum(Mouvement.quantite))
            .where(Mouvement.lot_id == x.id)
            .group_by(Mouvement.magasin_id)
        ).all()
    )
    assert journal == {magasin(s).id: Decimal("5.340"), g.id: Decimal("5.000")}
    assert {k: _solde(s, x.id, k) for k in journal} == journal
    q = magasin(s, TypeMagasin.quarantaine)
    assert _solde(s, x.id, q.id) == 0
