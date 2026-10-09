/**
 * Les colonnes des deux onglets de l'inventaire (ECRANS-PRO partie 6) : « En cours de comptage »
 * et « Inventaires clos ». La valeur de l'écart n'est montrée qu'à qui voit les prix.
 */
import { Badge } from '../../composants/retour/Badge'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { date, horodatage, nombre, part } from '../../lib/format'
import { BadgeHorsTolerance, EcartKg, ValeurEcart } from './communs'
import styles from './Inventaire.module.css'
import { statut } from '../../lib/statuts'
import { magasinDe, type InventaireResume } from './types'

type C = Colonne<InventaireResume>

const numero: C = {
  cle: 'numero',
  titre: 'Inventaire',
  rendu: (i) => (
    <span className={styles.valeur}>
      <strong className={styles.lot}>{i.numero}</strong>
      {i.libelle ? <span className={styles.note}>{i.libelle}</span> : null}
    </span>
  ),
  recherche: (i) => [i.libelle],
}
const jour: C = { cle: 'date', titre: 'Date', rendu: (i) => date(i.date), valeur: (i) => i.date }
const magasin: C = { cle: 'magasin', titre: 'Magasin', valeur: (i) => magasinDe(i) }
const perimetre: C = { cle: 'perimetre', titre: 'Périmètre' }
const tolerance: C = {
  cle: 'tolerance',
  titre: 'Tolérance',
  droite: true,
  rendu: (i) => part(i.tolerance, 0),
}
const comptes: C = {
  cle: 'comptes',
  titre: 'Lots comptés',
  droite: true,
  valeur: (i) => i.nb_comptees,
  rendu: (i) => `${nombre(i.nb_comptees)} / ${nombre(i.nb_lignes)}`,
}
const hors: C = {
  cle: 'hors',
  titre: 'Hors tolérance',
  aide: 'Rouge : des écarts hors tolérance restent sans justification ; orange : tous justifiés',
  droite: true,
  valeur: (i) => i.hors_tolerance,
  rendu: (i) => <BadgeHorsTolerance hors={i.hors_tolerance} sansJustification={i.sans_justification} />,
}
const ecart: C = {
  cle: 'ecart',
  titre: 'Écart (kg)',
  aide: 'Retenu − théorique, sur les lots comptés',
  droite: true,
  valeur: (i) => i.ecart_total,
  rendu: (i) => <EcartKg valeur={i.statut === 'abandonne' ? null : i.ecart_total} />,
}
const valeur: C = {
  cle: 'valeur',
  titre: 'Valeur de l’écart',
  aide: 'Au coût moyen (CMUP) tant que l’inventaire est ouvert, au coût de chaque ajustement écrit une fois validé',
  droite: true,
  valeur: (i) => i.ecart_valeur_mad,
  rendu: (i) => (
    <ValeurEcart
      net={i.statut === 'abandonne' ? null : i.ecart_valeur_mad}
      absolu={i.ecart_valeur_absolue_mad}
    />
  ),
}
const etat: C = {
  cle: 'etat',
  titre: 'État',
  valeur: (i) => statut('inventaire', i.statut).libelle,
  rendu: (i) => <Badge famille="inventaire" valeur={i.statut} />,
}

/** « {ouvreur} · validé par {nom} le … » [« · annulé par {nom} le … »]. */
export function parDe(i: InventaireResume): string {
  const morceaux = [i.cree_par]
  if (i.valide_le) morceaux.push(`validé par ${i.valide_par} le ${horodatage(i.valide_le)}`)
  if (i.abandonne_le) morceaux.push(`abandonné par ${i.abandonne_par} le ${horodatage(i.abandonne_le)}`)
  if (i.annule_le) morceaux.push(`annulé par ${i.annule_par} le ${horodatage(i.annule_le)}`)
  return morceaux.filter(Boolean).join(' · ')
}

const par: C = {
  cle: 'par',
  titre: 'Par',
  valeur: parDe,
  rendu: (i) => {
    const [ouvreur, ...suite] = parDe(i).split(' · ')
    return (
      <span className={`${styles.valeur} ${styles.lot}`}>
        <span>{ouvreur}</span>
        {suite.map((s) => (
          <span key={s} className={styles.note}>
            {s}
          </span>
        ))}
      </span>
    )
  },
}

/** Les colonnes d'un onglet ; sans la valeur de l'écart pour qui ne voit pas les prix. */
export function colonnesInventaires(onglet: 'cours' | 'passes', voitPrix: boolean): C[] {
  const prix = voitPrix ? [valeur] : []
  if (onglet === 'cours')
    return [numero, jour, magasin, perimetre, tolerance, comptes, hors, ecart, ...prix, par]
  return [numero, jour, magasin, perimetre, comptes, hors, ecart, ...prix, etat, par]
}
