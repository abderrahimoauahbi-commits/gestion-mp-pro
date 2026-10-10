/**
 * Onglet « Historique » de la fiche d'un métier (`/metiers/:id?onglet=historique`, nouveau) : les
 * montages (le, par, étage, fils avant → après, sur les métiers avant / après, écart, origine),
 * lus dans l'historique des montages (`GET /metiers/{id}/montages`) ; puis le journal des
 * réglages (`Historique`).
 */
import { Historique } from '../../composants/documents/Historique'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { Vide } from '../../composants/retour/Vide'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { horodatage, nombre, nombreSigne } from '../../lib/format'
import { useLecture } from '../../lib/requetes'
import type { Schema } from '../../lib/types'

type Montage = Schema<'MontageEvenementFiche'>

/** « POIL 1,5 m (50 %), CHAINE 4,2 m » : les fils d'un côté de l'événement. */
export function filsLisibles(lignes: readonly Record<string, unknown>[]): string {
  if (!lignes.length) return 'vide'
  return lignes
    .map((l) => {
      const pct =
        typeof l.pourcentage === 'number' && l.pourcentage !== 100 ? ` (${nombre(l.pourcentage, 0)} %)` : ''
      return `${String(l.reference ?? '')} ${nombre(typeof l.metres === 'number' ? l.metres : null, 0, 2)} m${pct}`
    })
    .join(', ')
}

const COLONNES: Colonne<Montage>[] = [
  { cle: 'quand', titre: 'Le', valeur: (x) => x.quand, rendu: (x) => horodatage(x.quand) },
  { cle: 'par', titre: 'Par', valeur: (x) => x.par ?? '' },
  {
    cle: 'etage',
    titre: 'Étage',
    droite: true,
    valeur: (x) => x.etage,
    rendu: (x) => (x.etage == null ? 'plusieurs' : nombre(x.etage)),
  },
  {
    cle: 'fils',
    titre: 'Fils (avant → après)',
    valeur: (x) => filsLisibles(x.apres),
    rendu: (x) => `${filsLisibles(x.avant)} → ${filsLisibles(x.apres)}`,
  },
  {
    cle: 'avant',
    titre: 'Sur les métiers avant (kg)',
    droite: true,
    valeur: (x) => x.avant_kg,
    rendu: (x) => nombre(x.avant_kg, 0, 2),
  },
  {
    cle: 'apres',
    titre: 'après (kg)',
    droite: true,
    valeur: (x) => x.apres_kg,
    rendu: (x) => nombre(x.apres_kg, 0, 2),
  },
  {
    cle: 'effet',
    titre: 'Écart (kg)',
    droite: true,
    valeur: (x) => x.effet_kg,
    rendu: (x) => nombreSigne(x.effet_kg, 0, 2),
  },
  { cle: 'origine', titre: 'Origine', valeur: (x) => x.origine },
]

export function OngletHistorique({ id }: { id: number }) {
  const montages = useLecture<Montage[]>(`/metiers/${id}/montages`)
  return (
    <>
      {montages.isError ? (
        <Erreur erreur={montages.error} onReessayer={() => void montages.refetch()} />
      ) : null}
      {montages.isPending ? <Chargement quoi="les montages" /> : null}
      {montages.data ? (
        <DataTable
          libelle="Montages"
          lignes={montages.data}
          colonnes={COLONNES}
          cle={(x) => x.id}
          recherche={false}
          hauteur="fenetre"
          vide={<Vide>Aucun montage enregistré.</Vide>}
        />
      ) : null}
      <Historique objet="metier" id={id} />
    </>
  )
}
