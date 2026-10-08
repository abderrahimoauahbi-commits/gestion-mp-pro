/**
 * Changer son code (PUT /moi/code, route 14) : l'ancien est exigé ; la règle du rôle est dite à la
 * frappe (alimentation : exactement 4 chiffres ; achats et direction : 8 caractères au moins ;
 * administrateur technique : 12) ; les autres sessions du compte sont fermées.
 */
import { useState } from 'react'

import { useGardeSaisie } from '../../composants/coque/garde'
import { Grille } from '../../composants/mise-en-page/Grille'
import { dire } from '../../composants/retour/Messages'
import { Bouton } from '../../composants/saisie/Bouton'
import { Champ, erreurDuChamp } from '../../composants/saisie/Champ'
import { Saisie } from '../../composants/saisie/Saisie'
import { api } from '../../lib/api'
import { useEcriture } from '../../lib/requetes'
import { useSession } from '../../lib/session'
import type { Role } from '../../lib/types'
import styles from './MonCompte.module.css'

/** La règle du code de ce rôle (ARCHITECTURE § 5.1). */
export function regleDuCode(role: Role): string {
  if (role === 'alimentation') return 'Exactement 4 chiffres.'
  if (role === 'administrateur') return '12 caractères au moins.'
  return '8 caractères au moins.'
}

/** Le nouveau code respecte-t-il la règle du rôle ? */
export function codeValable(role: Role, code: string): boolean {
  if (role === 'alimentation') return /^\d{4}$/.test(code)
  return code.length >= (role === 'administrateur' ? 12 : 8)
}

/** Ce qui manque avant de changer de code. */
export function manqueCode(role: Role, ancien: string, nouveau: string, confirmation: string): string[] {
  const manque: string[] = []
  if (!ancien) manque.push('le code actuel')
  if (!codeValable(role, nouveau))
    manque.push(`un nouveau code valable (${regleDuCode(role).toLowerCase().replace(/\.$/, '')})`)
  else if (confirmation !== nouveau) manque.push('le nouveau code retapé à l’identique')
  return manque
}

export function ChangerCode() {
  const { role } = useSession()
  const [ancien, setAncien] = useState('')
  const [nouveau, setNouveau] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const ecriture = useEcriture(
    (corps: { ancien: string; nouveau: string }) => api.put<void>('/moi/code', corps),
    {
      invalider: false,
    },
  )
  useGardeSaisie(Boolean(ancien || nouveau || confirmation))
  const changer = async () => {
    await ecriture.mutateAsync({ ancien, nouveau })
    setAncien('')
    setNouveau('')
    setConfirmation('')
    dire('Code changé : vos autres sessions sont fermées.')
  }
  return (
    <Grille colonnes={1}>
      <Champ libelle="Code actuel" erreur={erreurDuChamp(ecriture.error, 'ancien')}>
        <Saisie valeur={ancien} onChange={setAncien} type="password" autoComplete="current-password" />
      </Champ>
      <Champ
        libelle="Nouveau code"
        aide={regleDuCode(role)}
        erreur={erreurDuChamp(ecriture.error, 'nouveau')}
      >
        <Saisie valeur={nouveau} onChange={setNouveau} type="password" autoComplete="new-password" />
      </Champ>
      <Champ libelle="Nouveau code, encore une fois">
        <Saisie
          valeur={confirmation}
          onChange={setConfirmation}
          type="password"
          autoComplete="new-password"
        />
      </Champ>
      <div className={styles.gestes}>
        <Bouton
          variante="principal"
          manque={manqueCode(role, ancien, nouveau, confirmation)}
          attente="Changement…"
          titre="Change votre code ; vos autres sessions sont fermées."
          onClick={changer}
        >
          Changer mon code
        </Bouton>
      </div>
    </Grille>
  )
}
