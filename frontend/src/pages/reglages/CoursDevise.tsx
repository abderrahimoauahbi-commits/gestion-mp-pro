/**
 * Fenêtre « Les cours du {nom} ({CODE} → MAD) » (route 28) : chaque cours saisi, le plus récent
 * d'abord, sa variation et qui l'a saisi ; quatre décimales à la française (P8-13).
 */
import { Fenetre } from '../../composants/mise-en-page/Fenetre'
import { Erreur } from '../../composants/retour/Erreur'
import { Note } from '../../composants/retour/Note'
import { useListePaginee } from '../../composants/tableaux/ChargerPlus'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { cours, horodatage, partSignee } from '../../lib/format'
import type { Schema } from '../../lib/types'
import type { DeviseFiche } from './Devises'

type Cours = Schema<'CoursHistorique'>

const COLONNES: readonly Colonne<Cours>[] = [
  { cle: 'saisi_le', titre: 'Saisi le', rendu: (c) => horodatage(c.saisi_le) },
  { cle: 'cours', titre: 'Cours (MAD)', droite: true, rendu: (c) => cours(c.cours) },
  { cle: 'variation', titre: 'Variation', droite: true, rendu: (c) => partSignee(c.variation, 2) },
  { cle: 'par', titre: 'Par' },
]

export function CoursDevise({ devise, onFermer }: { devise: DeviseFiche; onFermer: () => void }) {
  const p = useListePaginee<Cours>(`/devises/${devise.code}/cours`)
  return (
    <Fenetre titre={`Les cours du ${devise.nom} (${devise.code} → MAD)`} taille="large" onFermer={onFermer}>
      <Note>Le plus récent d’abord. Le cours en vigueur est le premier de la liste.</Note>
      {p.requete.isError ? (
        <Erreur erreur={p.requete.error} onReessayer={() => void p.requete.refetch()} />
      ) : null}
      <DataTable<Cours>
        libelle={`Cours de ${devise.code}`}
        lignes={p.lignes}
        colonnes={COLONNES}
        cle={(c) => c.id}
        recherche={false}
        serveur
        total={p.total}
        chargerPlus={p.chargerPlus}
        hauteur="fenetre"
        vide={p.requete.isPending ? 'Chargement…' : 'Aucun cours saisi depuis la mise en service.'}
      />
    </Fenetre>
  )
}
