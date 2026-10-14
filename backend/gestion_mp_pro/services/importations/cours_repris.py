"""Une marchandise reçue qui entre (ou revient) dans un dossier prend le cours figé de son bon,
comme à l'ouverture ; sans bon, elle est sans cours (comptée au cours du jour). Son cours payé
à la banque ne survit pas à sa sortie (facture retirée, réception détachée, dossier annulé).

Ce n'est pas silencieux (audit n° 2, 14/10/2026) : la réponse du geste (`DossierFiche.avis`),
le journal et l'écran le disent, et le **dernier cours payé** est proposé quand il se retrouve —
sans schéma nouveau : la sortie l'écrit au journal (`avant.cours_payes`, par ligne reçue), le
retour le relit.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import array
from sqlalchemy.orm import Session

from gestion_mp_pro.documents.format import nombre
from gestion_mp_pro.modeles import DossierLigne, Journal
from gestion_mp_pro.modeles.enums import ObjetJournal, OrigineCours
from gestion_mp_pro.services.importations.socle import BonFige, bons

CLE_JOURNAL = "cours_payes"
"""La clé, dans `avant`, des cours payés que la sortie d'une marchandise garde au journal."""
ONGLET = "le cours payé à la banque se ressaisit dans l'onglet Marchandises"


def cours_payes(lignes: Iterable[DossierLigne]) -> dict[str, object]:
    """Ce que le journal garde des marchandises reçues qui sortent : leur cours payé (tout cours
    qui n'est pas celui du bon), par ligne reçue — `{"cours_payes": {"412": 10.05}}`, ou rien."""
    payes = {
        str(x.reception_ligne_id): float(x.cours)
        for x in lignes
        if x.reception_ligne_id and x.cours is not None and x.cours_origine != OrigineCours.bon
    }
    return {CLE_JOURNAL: payes} if payes else {}


def derniers_cours_payes(s: Session, ids: Iterable[int]) -> dict[int, Decimal]:
    """Le dernier cours payé connu de chaque ligne reçue, relu dans le journal des dossiers (la
    sortie la plus récente d'abord)."""
    voulues = {int(i) for i in ids}
    if not voulues:
        return {}
    requete = (
        select(Journal.avant)
        .where(
            Journal.objet == ObjetJournal.dossier,
            Journal.avant[CLE_JOURNAL].has_any(array([str(i) for i in sorted(voulues)])),
        )
        .order_by(Journal.quand.desc(), Journal.id.desc())
    )
    resultat: dict[int, Decimal] = {}
    for (avant,) in s.execute(requete):
        for cle, cours in ((avant or {}).get(CLE_JOURNAL) or {}).items():
            if int(cle) in voulues and int(cle) not in resultat:
                resultat[int(cle)] = Decimal(str(cours))
    return resultat


def _cours(valeur: Decimal | float) -> str:
    """« 10,05 » (jusqu'à quatre décimales utiles)."""
    return nombre(float(valeur), 0, 4)


def _entrees(lignes: list[DossierLigne], figes: Mapping[int, BonFige]) -> list[str]:
    """« 2 marchandises au cours du bon BC-… (10 MAD pour 1 USD) », « 1 marchandise sans cours
    payé (comptée au cours du jour) »."""
    par_bon: dict[tuple[str, str, str], int] = defaultdict(int)
    sans_cours = 0
    for x in lignes:
        bon = figes.get(x.reception_ligne_id) if x.reception_ligne_id else None
        if x.cours is not None and bon is not None:
            par_bon[(bon.numero, _cours(x.cours), x.devise)] += 1
        elif x.devise != "MAD":
            sans_cours += 1
    morceaux = [
        f"{n} marchandise{'s' if n > 1 else ''} au cours du bon {numero} ({cours} MAD pour 1 {dev})"
        for (numero, cours, dev), n in sorted(par_bon.items())
    ]
    if sans_cours:
        quoi = "marchandises" if sans_cours > 1 else "marchandise"
        morceaux.append(f"{sans_cours} {quoi} sans cours payé (comptée au cours du jour)")
    return morceaux


def avis(s: Session, facture: str, lignes: list[DossierLigne]) -> list[str]:
    """Ce que la réponse dit des marchandises de la facture qui entrent : leur cours (celui du
    bon, ou aucun), et — si elles sont déjà sorties d'un dossier avec un cours payé — que c'est
    une **reprise**, avec le dernier cours payé saisi à ressaisir."""
    figes = bons(s, (x.reception_ligne_id for x in lignes if x.reception_ligne_id))
    entrees = _entrees(lignes, figes)
    if not entrees:
        return []
    derniers = derniers_cours_payes(
        s, (x.reception_ligne_id for x in lignes if x.reception_ligne_id)
    )
    if not derniers:
        return [
            f"Facture {facture} : {' ; '.join(entrees)} — le cours du bon est celui des réglages à "
            f"la confirmation des prix ; {ONGLET}."
        ]
    par_devise: dict[str, set[str]] = defaultdict(set)
    for x in lignes:
        if x.reception_ligne_id in derniers:
            par_devise[x.devise].add(_cours(derniers[x.reception_ligne_id]))
    rappel = ", ".join(f"{dev} à {' et '.join(sorted(c))}" for dev, c in sorted(par_devise.items()))
    return [
        f"Facture {facture} : reprise de {' ; '.join(entrees)} — le cours payé saisi avant sa "
        f"sortie ne revient pas ({ONGLET}). Dernier cours payé saisi : {rappel}."
    ]


def marque(notes: list[str]) -> str:
    """Ce que le journal ajoute au détail du geste : une reprise, ou rien."""
    reprise = any(x.startswith("Facture") and " : reprise de " in x for x in notes)
    return " · reprise : le cours payé d'avant la sortie ne revient pas" if reprise else ""
