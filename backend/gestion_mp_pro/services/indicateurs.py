"""La photo du jour des indicateurs (routes 231, 232 ; tâche `photo_indicateurs` de D10).

Une photo par jour : la valeur du stock (celle de la Valorisation et du Cockpit : magasins et
métiers au coût moyen), la couverture pondérée, les ruptures, critiques et urgentes, le budget
à commander, le reste à livrer des bons, et l'OTIF moyen des réceptions notées des **douze
derniers mois** (une réception, une voix ; E-17). Reprendre la photo du jour la remplace et
s'écrit au journal (E-17) ; la tâche de fond ne la refait jamais (D10).
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro.calcul.fournisseurs import performance_receptions
from gestion_mp_pro.calcul.pilotage import cockpit
from gestion_mp_pro.calcul.suivi import indicateurs_du_cockpit
from gestion_mp_pro.documents.format import montant
from gestion_mp_pro.modeles import IndicateurJour
from gestion_mp_pro.modeles.enums import ObjetJournal
from gestion_mp_pro.modeles.types import JOURS, MONTANT, TAUX, arrondir
from gestion_mp_pro.services import audit, horloge
from gestion_mp_pro.services.pilotage import lire, valoriser_lecture

ACTION = "photo des indicateurs"
"""L'action du journal (E-17)."""


def photographier(s: Session, qui: audit.Qui | None = None) -> IndicateurJour:
    """La photo d'aujourd'hui, prise ou reprise (journalisée ; `qui` absent : la tâche)."""
    jour = horloge.aujourd_hui()
    lecture = lire(s, jour)
    d = lecture.donnees
    i = indicateurs_du_cockpit(cockpit(d, jour, lecture.lignes), performance_receptions(d), jour)
    valeur = valoriser_lecture(s, lecture).total_mad
    photo = s.get(IndicateurJour, jour)
    reprise = photo is not None
    if photo is None:
        photo = IndicateurJour(jour=jour)
        s.add(photo)
    photo.pris_le = horloge.maintenant()
    photo.pris_par_id = qui.id if qui is not None else None
    photo.valeur_stock_mad = arrondir(valeur, MONTANT)
    photo.couverture_jours = arrondir(i.couverture_jours, JOURS)
    photo.ruptures, photo.critiques, photo.urgents = i.ruptures, i.critiques, i.urgents
    photo.a_commander_mad = arrondir(i.a_commander_mad, MONTANT)
    photo.commandes_en_cours_mad = arrondir(i.commandes_en_cours_mad, MONTANT)
    photo.otif_moyen = arrondir(i.otif_moyen, TAUX) if i.otif_moyen is not None else None
    detail = (
        f"{'reprise' if reprise else 'prise'} du {jour:%d/%m/%Y} · valeur du stock "
        f"{montant(valeur, 'MAD')} · {i.ruptures} rupture(s), {i.critiques} critique(s)"
    )
    audit.journal(s, qui, ACTION, ObjetJournal.systeme, None, detail=detail)
    s.flush()
    return photo


def historique(s: Session, du: date | None = None, au: date | None = None) -> list[IndicateurJour]:
    """Route 231 : les photos, dans l'ordre des jours (bornes comprises)."""
    requete = select(IndicateurJour).order_by(IndicateurJour.jour)
    if du is not None:
        requete = requete.where(IndicateurJour.jour >= du)
    if au is not None:
        requete = requete.where(IndicateurJour.jour <= au)
    return list(s.scalars(requete))
