/**
 * Les volets de l'aperçu du tableur : « Erreurs », « Modifiées » (une ligne par champ qui
 * change, avant → après, libellés traduits pour tous les champs — P7-11), « Créées ». Ouvert
 * d'office : Erreurs s'il y en a, sinon Modifiées, sinon Créées.
 */
import { useState } from 'react'

import { Onglets } from '../../composants/mise-en-page/Onglets'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { VIDE } from '../../lib/format'
import styles from './catalogue.module.css'
import type { ApercuImport, LigneImport } from './types'

type Volet = 'erreurs' | 'modifiees' | 'creees'

interface LigneChamp {
  cle: string
  ligne: number
  reference: string
  champ: string
  avant: string
  apres: string
}

/** Le volet ouvert d'office. */
export function voletInitial(a: ApercuImport): Volet {
  return a.erreurs ? 'erreurs' : a.modifiees ? 'modifiees' : 'creees'
}

/** Les champs qui changent, une ligne par champ. */
export function champsModifies(lignes: readonly LigneImport[]): LigneChamp[] {
  return lignes
    .filter((l) => l.etat === 'modifiee')
    .flatMap((l) =>
      l.changements.map((c) => ({
        cle: `${l.ligne}-${c.champ}`,
        ligne: l.ligne,
        reference: l.reference,
        champ: c.libelle,
        avant: c.avant,
        apres: c.apres,
      })),
    )
}

const COL_ERREURS: Colonne<LigneImport>[] = [
  { cle: 'ligne', titre: 'Ligne', droite: true, largeur: 70 },
  { cle: 'reference', titre: 'Référence', rendu: (l) => <span className={styles.code}>{l.reference}</span> },
  { cle: 'erreurs', titre: 'Ce qui ne va pas', valeur: (l) => l.erreurs.join(' ; ') },
]

const COL_MODIFIEES: Colonne<LigneChamp>[] = [
  { cle: 'reference', titre: 'Référence', rendu: (l) => <span className={styles.code}>{l.reference}</span> },
  { cle: 'champ', titre: 'Champ' },
  { cle: 'avant', titre: 'Avant', valeur: (l) => l.avant || VIDE },
  { cle: 'apres', titre: 'Après', valeur: (l) => l.apres || VIDE },
]

const COL_CREEES: Colonne<LigneImport>[] = [
  { cle: 'ligne', titre: 'Ligne', droite: true, largeur: 70 },
  {
    cle: 'reference',
    titre: 'Référence créée',
    rendu: (l) => <span className={styles.code}>{l.reference}</span>,
  },
]

export function VolumesApercu({ a }: { a: ApercuImport }) {
  const [volet, setVolet] = useState<Volet>(() => voletInitial(a))
  const erreurs = a.lignes.filter((l) => l.etat === 'erreur')
  const creees = a.lignes.filter((l) => l.etat === 'nouvelle')
  return (
    <>
      <Onglets<Volet>
        libelle="Volets de l’aperçu"
        actif={volet}
        onChange={setVolet}
        onglets={[
          { cle: 'erreurs', libelle: 'Erreurs', compte: a.erreurs },
          { cle: 'modifiees', libelle: 'Modifiées', compte: a.modifiees },
          { cle: 'creees', libelle: 'Créées', compte: a.creees },
        ]}
      />
      {volet === 'erreurs' ? (
        <DataTable
          libelle="Lignes en erreur"
          lignes={erreurs}
          colonnes={COL_ERREURS}
          cle={(l) => l.ligne}
          hauteur="fenetre"
          vide="Rien ici."
        />
      ) : null}
      {volet === 'modifiees' ? (
        <DataTable
          libelle="Champs modifiés"
          lignes={champsModifies(a.lignes)}
          colonnes={COL_MODIFIEES}
          cle={(l) => l.cle}
          hauteur="fenetre"
          vide="Rien ici."
        />
      ) : null}
      {volet === 'creees' ? (
        <DataTable
          libelle="Matières créées"
          lignes={creees}
          colonnes={COL_CREEES}
          cle={(l) => l.ligne}
          hauteur="fenetre"
          vide="Rien ici."
        />
      ) : null}
    </>
  )
}
