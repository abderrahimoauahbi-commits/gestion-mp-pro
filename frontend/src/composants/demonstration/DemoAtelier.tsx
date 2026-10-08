/** Démonstration de l'atelier : un écran de téléphone (375 px), tuiles, compteur, blocages, résumé collant. */
import { useState } from 'react'

import type { Unite } from '../../lib/unites'
import { BandeauBlocages } from '../atelier/BandeauBlocages'
import { EcranAtelier } from '../atelier/EcranAtelier'
import { ResumeValidation } from '../atelier/ResumeValidation'
import { useSaisieGardee } from '../atelier/saisieGardee'
import { ScanQR } from '../atelier/ScanQR'
import { Tuile, Tuiles } from '../atelier/Tuile'
import { Carte } from '../mise-en-page/Carte'
import { dire } from '../retour/Messages'
import { Bouton } from '../saisie/Bouton'
import { Confirmer } from '../saisie/Confirmer'
import { Quantite } from '../saisie/Quantite'
import styles from './Demonstration.module.css'

function Resume() {
  return (
    <ResumeValidation
      lignes={[
        ['Date', 'hier 07/10'],
        ['Magasin', 'Principal'],
        ['Métier', 'M3'],
      ]}
    >
      <Bouton taille="atelier" variante="principal" bloc grise="1 ligne dépasse ce qui est parti.">
        Remettre 52,4 kg en stock
      </Bouton>
    </ResumeValidation>
  )
}

export function DemoAtelier() {
  const [kg, setKg] = useSaisieGardee<number | null>('demonstration', 52.4)
  const [unite, setUnite] = useState<Unite>('kg')
  return (
    <div className={styles.telephone}>
      <EcranAtelier
        titre="Retour des machines"
        retour="/demonstration"
        enTete={
          <BandeauBlocages
            blocages={[
              'L’inventaire INV-2026-0003 (Principal, du 08/10/2026) compte « PP Rouge » : ses mouvements y sont suspendus jusqu’à sa validation.',
            ]}
          />
        }
        pied={<Resume />}
      >
        <Tuiles>
          <Tuile
            titre="Envoyer aux machines"
            detail="2 brouillons"
            vers="/atelier/envoyer"
            icone="envoyer"
            ton="attention"
          />
          <Tuile titre="Retour des machines" vers="/atelier/retour" icone="retour" />
          <Tuile titre="Trouver un lot" vers="/atelier/chercher" icone="lots" />
          <Tuile titre="Signaler un besoin" vers="/atelier/signaler" icone="attention" />
        </Tuiles>
        <Carte titre="OF-2026-0118 · PP Rouge" ton="attention">
          <Quantite
            libelle="Rendu"
            tactile
            kg={kg}
            onChange={setKg}
            unite={unite}
            onUnite={setUnite}
            poidsBobine={2.4952}
            bobinesPalette={40}
            borne={60}
          />
        </Carte>
        <ScanQR onLot={(id) => dire(`Lot ${id} lu.`)} />
        <Confirmer
          taille="atelier"
          question="Se déconnecter de l’atelier ?"
          oui="Oui, se déconnecter"
          onOui={() => dire('Déconnecté.', 'info')}
        >
          Se déconnecter
        </Confirmer>
      </EcranAtelier>
    </div>
  )
}
