"""Le cache du chargeur (lot S4 ; ARCHITECTURE § 7) : jamais périmé — la signature est lue en
base à chaque appel, si bien qu'une écriture se voit aussitôt, y compris d'un autre processus —
et un nombre de requêtes qui ne dépend pas de la taille de la base.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from fabriques.moteur import batir
from fabriques.stock import (
    JOUR,
    entree,
    fournisseur,
    lot,
    magasin,
    matiere,
    s,
    sortie,
    unique,
)
from sqlalchemy import event, text, update
from sqlalchemy.orm import Session

from gestion_mp_pro.db import fabrique, moteur
from gestion_mp_pro.modeles import (
    Commande,
    CommandeLigne,
    Devise,
    Lot,
    Parametre,
    Reception,
    ReceptionLigne,
)
from gestion_mp_pro.services import audit, donnees_moteur, horloge

__all__ = ["s"]

BACKEND = Path(__file__).resolve().parents[1]


@contextmanager
def compter_les_requetes() -> Iterator[list[str]]:
    """Les requêtes SQL envoyées pendant le bloc (toutes connexions du processus)."""
    vues: list[str] = []

    def noter(*args: object) -> None:
        vues.append(str(args[2]))

    event.listen(moteur(), "before_cursor_execute", noter)
    try:
        yield vues
    finally:
        event.remove(moteur(), "before_cursor_execute", noter)


def _grossir(s: Session, fois: int) -> None:
    """Autant de lots, d'écritures, de bons et de réceptions en plus, `fois` fois."""
    f = fournisseur(s)
    for _ in range(fois):
        m = matiere(s, fournisseur_id=f.id)
        x = lot(s, m, entre_le=JOUR - timedelta(days=3))
        entree(s, x, 100, JOUR - timedelta(days=3))
        sortie(s, x, 10)
        bc = Commande(fournisseur_id=f.id, date_commande=JOUR, devise="MAD")
        s.add(bc)
        s.flush()
        s.add(CommandeLigne(commande_id=bc.id, matiere_id=m.id, quantite=5))
        r = Reception(date=JOUR, fournisseur_id=f.id, devise="MAD")
        s.add(r)
        s.flush()
        s.add(ReceptionLigne(reception_id=r.id, matiere_id=m.id, quantite_pesee=4))
    s.flush()


def test_aucune_requete_par_ligne(s: Session) -> None:
    """Le chargeur lit la base en un nombre fixe de requêtes groupées, quelle que soit sa
    taille (ARCHITECTURE § 6 : aucune requête par ligne)."""
    batir(s)
    with compter_les_requetes() as petite:
        donnees_moteur.lire(s)
    _grossir(s, 25)
    with compter_les_requetes() as grande:
        d = donnees_moteur.lire(s)
    assert len(d.mouvements) > 50 and len(d.commandes) > 25
    assert len(grande) == len(petite) <= 60
    with compter_les_requetes() as signature:
        donnees_moteur.signature(s)
    assert len(signature) == 1


def test_le_cache_ne_relit_que_si_quelque_chose_a_change(s: Session) -> None:
    """Même signature : le même objet. Un mouvement, un réglage, une ligne de journal, un solde
    touché hors du chemin d'écriture, un nouveau jour : relu. Hérité :
    test_parcours::test_le_cache_ne_montre_jamais_un_chiffre_perime."""
    w = batir(s)
    donnees_moteur.invalider()
    premier = donnees_moteur.charger(s)
    assert donnees_moteur.charger(s) is premier
    x = lot(s, matiere(s, reference="Jute du cache"))
    entree(s, x, "12.5")
    apres_ecriture = donnees_moteur.charger(s)
    assert apres_ecriture is not premier
    assert [m.quantite for m in apres_ecriture.mouvements if m.reference == "Jute du cache"] == [
        12.5
    ]
    precedent = apres_ecriture
    gestes = [
        lambda: s.execute(
            update(Parametre)
            .where(Parametre.cle == "dso")
            .values(modifie_le=datetime(2100, 1, 1, tzinfo=horloge.FUSEAU))
        ),
        lambda: audit.journal(s, None, "essai du cache"),
        lambda: s.execute(
            text("UPDATE solde SET quantite = quantite + 1 WHERE lot_id = :l"), {"l": w.ids["ppa"]}
        ),
        lambda: horloge.fixer(horloge.maintenant() + timedelta(days=1)),
    ]
    for geste in gestes:
        geste()
        s.flush()
        relu = donnees_moteur.charger(s)
        assert relu is not precedent
        precedent = relu


def test_un_reglage_change_se_voit_a_horloge_figee(s: Session) -> None:
    """Deux changements d'un réglage (ou d'un cours) à la même heure — horloge figée des essais,
    ou deux écritures dans la même microseconde — ne laissent pas le cache ancien : la
    signature compte les `version` des réglages et des devises, pas seulement `modifie_le`."""
    assert horloge.est_figee()
    donnees_moteur.invalider()
    for valeur in ("45", "50", "55"):
        p = s.get_one(Parametre, "seuil_critique")
        p.valeur = valeur
        s.flush()
        assert donnees_moteur.charger(s).parametres.seuil_critique == float(valeur)
    for cours in ("11", "12"):
        d = s.get_one(Devise, "USD")
        d.cours = Decimal(cours)
        s.flush()
        assert donnees_moteur.charger(s).parametres.cours["USD"] == float(cours)


SCRIPT = textwrap.dedent(
    """
    import sys
    from datetime import date
    from gestion_mp_pro.db import fabrique
    from gestion_mp_pro.modeles import Lot
    from gestion_mp_pro.modeles.enums import DocumentMouvement, TypeMouvement
    from gestion_mp_pro.services import donnees_moteur, stock

    def lot_compte(reference):
        with fabrique()() as s:
            d = donnees_moteur.charger(s)
            return len([m for m in d.mouvements if m.reference == reference])

    mode, lot_id, magasin_id, reference = sys.argv[1], *map(int, sys.argv[2:4]), sys.argv[4]
    if mode == "ecrire":
        with fabrique()() as s:
            stock.ecrire(
                s, type=TypeMouvement.SORTIE, lot=s.get(Lot, lot_id),
                magasin_id=magasin_id, quantite=-1, jour=date(2026, 10, 1),
                auteur_id=None, piece=stock.Piece(DocumentMouvement.reprise),
            )
            s.commit()
    else:
        print(lot_compte(reference), flush=True)
        sys.stdin.readline()
        print(lot_compte(reference), flush=True)
    """
)


def _processus(*arguments: object) -> subprocess.Popen[str]:
    """Un autre processus Python, sur la même base."""
    env = dict(os.environ)
    return subprocess.Popen(  # noqa: S603 — l'interpréteur des essais, un script à nous
        [sys.executable, "-c", SCRIPT, *map(str, arguments)],
        cwd=BACKEND,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )


def test_une_ecriture_d_un_autre_processus_se_voit_aussitot() -> None:
    """Deux processus (comme les deux processus uvicorn) : chacun écrit, l'autre relit
    aussitôt le chiffre à jour — la signature est en base, pas en mémoire."""
    reference = unique("Fil des deux processus")
    with fabrique()() as session:
        x = lot(session, matiere(session, reference=reference), entre_le=date(2026, 9, 1))
        entree(session, x, 100, date(2026, 9, 1))
        lot_id, magasin_id = x.id, magasin(session).id
        session.commit()
    with fabrique()() as session:
        assert _compte(session, reference) == 1
    autre = _processus("ecrire", lot_id, magasin_id, reference)
    assert autre.wait(timeout=60) == 0
    with fabrique()() as session:
        assert _compte(session, reference) == 2
    lecteur = _processus("lire", lot_id, magasin_id, reference)
    assert lecteur.stdout is not None and lecteur.stdin is not None
    assert lecteur.stdout.readline().strip() == "2"
    with fabrique()() as session:
        x2 = session.get(Lot, lot_id)
        assert x2 is not None
        sortie(session, x2, 1, date(2026, 10, 2))
        session.commit()
    lecteur.stdin.write("\n")
    lecteur.stdin.flush()
    assert lecteur.stdout.readline().strip() == "3"
    assert lecteur.wait(timeout=60) == 0


def _compte(s: Session, reference: str) -> int:
    """Les écritures d'une matière que le chargeur voit."""
    return len([m for m in donnees_moteur.charger(s).mouvements if m.reference == reference])
