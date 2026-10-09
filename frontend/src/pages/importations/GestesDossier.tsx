/**
 * La vie d'un dossier (ECRANS-PRO 5.6) : « Clôturer le dossier » et « Rouvrir pour corriger ».
 *
 * Clore se confirme dans une `FenetreConfirmation` (lecture longue, A3) qui **énumère les alertes
 * du serveur** (`alertes` de la fiche, dans l'ordre de ECRANS-PRO : cours vides, lignes au cours du
 * bon, cours multiples, frais hors norme, facture ≠ reçu, cours éloignés, fournisseurs, droits,
 * TVA) ; « Oui, clôturer » envoie `alertes_lues`. Si le serveur en voit d'autres entre-temps (refus
 * 422 `confirmation_requise`, qui les énumère), la fiche est relue : la fenêtre reste ouverte et
 * montre la liste à jour. Le bouton est grisé avec la raison du serveur (dossier vide, frais non
 * répartis…).
 */
import { useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { FenetreConfirmation } from '../../composants/mise-en-page/FenetreConfirmation'
import { dire } from '../../composants/retour/Messages'
import { Note } from '../../composants/retour/Note'
import { Bouton } from '../../composants/saisie/Bouton'
import { Confirmer } from '../../composants/saisie/Confirmer'
import { ErreurApi } from '../../lib/api'
import styles from './Importations.module.css'
import type { DossierFiche } from './types'
import type { GestesDossier } from './useDossier'

/** Le texte de la confirmation : les alertes à lire, puis l'effet de la clôture. */
export function TexteCloture({ alertes }: { alertes: readonly string[] }) {
  return (
    <div className={styles.pile}>
      {alertes.length ? (
        <>
          <p>Avant de clore, à lire ({alertes.length}) :</p>
          <ol aria-label="Alertes du dossier">
            {alertes.map((a) => (
              <li key={a}>{a}</li>
            ))}
          </ol>
        </>
      ) : null}
      <Note ton="info">
        Le coût hors TVA devient celui des lots en stock. Un dossier clos ne se modifie plus : il se rouvre si
        une facture de frais arrive en retard (c’est tracé).
      </Note>
    </div>
  )
}

export function Cloturer({ d, g }: { d: DossierFiche; g: GestesDossier }) {
  const [ouverte, setOuverte] = useState(false)
  const client = useQueryClient()
  const clore = async () => {
    try {
      await g.cloturer(true)
    } catch (e) {
      if (e instanceof ErreurApi && e.code === 'confirmation_requise')
        await client.invalidateQueries({ queryKey: [`/dossiers/${d.id}`] })
      throw e
    }
    dire('Dossier clôturé : son coût est figé.')
  }
  return (
    <>
      <Bouton
        variante="principal"
        taille="petit"
        blocages={d.actions.cloturer ? [d.actions.cloturer] : []}
        titre="Figer le coût hors TVA : un dossier clos ne se modifie plus (il se rouvre si une facture de frais arrive en retard, c’est tracé)"
        onClick={() => setOuverte(true)}
      >
        Clôturer le dossier
      </Bouton>
      {ouverte ? (
        <FenetreConfirmation
          titre={`Clore le dossier ${d.numero} ?`}
          texte={<TexteCloture alertes={d.alertes} />}
          oui="Oui, clôturer"
          onOui={clore}
          onFermer={() => setOuverte(false)}
        />
      ) : null}
    </>
  )
}

export function Rouvrir({ d, g }: { d: DossierFiche; g: GestesDossier }) {
  return (
    <Confirmer
      taille="petit"
      motif="facultatif"
      question="Rouvrir pour corriger ? La réouverture est tracée."
      oui="Oui, rouvrir"
      blocages={d.actions.rouvrir ? [d.actions.rouvrir] : []}
      titre="Rouvrir le dossier pour y ajouter un frais arrivé en retard, ou corriger"
      onOui={async (motif) => {
        await g.rouvrir(motif)
        dire('Dossier rouvert : il se modifie de nouveau.')
      }}
    >
      Rouvrir pour corriger
    </Confirmer>
  )
}
