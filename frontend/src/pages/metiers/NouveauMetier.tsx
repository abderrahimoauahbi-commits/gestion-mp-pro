/**
 * Nouveau métier (`/metiers/nouveau`, direction) en fenêtre sur la liste : code, nom, laize,
 * densité, étages, en service, observations ; « Créer le métier » grisé avec sa raison (an. 9) ;
 * la fiche s'ouvre ensuite. Une saisie commencée ne se perd pas sans question (A4).
 */
import { useState } from 'react'

import { Fenetre, useFermerFenetre } from '../../composants/mise-en-page/Fenetre'
import { dire } from '../../composants/retour/Messages'
import { Note } from '../../composants/retour/Note'
import { Bouton } from '../../composants/saisie/Bouton'
import { api } from '../../lib/api'
import { useEcriture } from '../../lib/requetes'
import type { MetierFiche } from '../atelier/types'
import { ChampsMetier } from './ChampsMetier'
import { corpsReglage, egal, versForme, type FormeMetier } from './formeMetier'

/** Ce qui manque pour créer un métier. */
export function manqueCreation(f: FormeMetier): string[] {
  const manque: string[] = []
  if (!f.code.trim()) manque.push('le code')
  if (!(f.etages != null && Number.isInteger(f.etages) && f.etages >= 1 && f.etages <= 40))
    manque.push('un nombre d’étages de 1 à 40')
  return manque
}

function Pied({ f, sale, onCree }: { f: FormeMetier; sale: boolean; onCree: (id: number) => void }) {
  const fermer = useFermerFenetre()
  const creer = useEcriture((corps: unknown) => api.post<MetierFiche>('/metiers', corps))
  return (
    <>
      <Bouton onClick={fermer}>{sale ? 'Abandonner' : 'Annuler'}</Bouton>
      <Bouton
        variante="principal"
        manque={manqueCreation(f)}
        attente="Création…"
        onClick={async () => {
          const m = await creer.mutateAsync(corpsReglage(f))
          dire(`Métier ${m.code} créé.`)
          onCree(m.id)
        }}
      >
        Créer le métier
      </Bouton>
    </>
  )
}

export function NouveauMetier({ onFermer, onCree }: { onFermer: () => void; onCree: (id: number) => void }) {
  const [initiale] = useState(() => versForme(null))
  const [f, setF] = useState(initiale)
  const sale = !egal(f, initiale)
  return (
    <Fenetre
      titre="Nouveau métier"
      taille="large"
      sale={sale}
      onFermer={onFermer}
      pied={<Pied f={f} sale={sale} onCree={onCree} />}
    >
      <ChampsMetier f={f} maj={(m) => setF((avant) => ({ ...avant, ...m }))} />
      <Note>
        Une fois créé, le métier s’ouvre : l’alimentation y monte ensuite ses fils, étage par étage.
      </Note>
    </Fenetre>
  )
}
