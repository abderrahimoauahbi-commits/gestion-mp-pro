/**
 * Administration › Technique (`/administration?onglet=technique`) et le geste commun des réglages
 * techniques (famille « Technique » de la route 24 : `adresse_publique`, `courriel_destinataires` ;
 * direction et administrateur). Contrôlés à la frappe avec la phrase du serveur ; écrits seuls, à
 * la version globale lue (409 si un autre poste a changé un réglage entre-temps).
 */
import { useState } from 'react'

import { Carte } from '../../composants/mise-en-page/Carte'
import { dire } from '../../composants/retour/Messages'
import { Note } from '../../composants/retour/Note'
import { Bouton } from '../../composants/saisie/Bouton'
import { Champ } from '../../composants/saisie/Champ'
import { Saisie } from '../../composants/saisie/Saisie'
import { api } from '../../lib/api'
import { useEcriture, useLecture } from '../../lib/requetes'
import { refusDuChamp, type Reglage } from '../reglages/parametres/logique'
import styles from './administration.module.css'

/** Un réglage technique lu (avec la version globale, pour l'écrire). */
export function useReglageTechnique(cle: string) {
  const lu = useLecture<Reglage[]>('/parametres')
  return { lu, reglage: lu.data?.find((r) => r.cle === cle) }
}

interface ChampTechniqueProps {
  r: Reglage
  placeholder?: string
  /** Le message dit après l'enregistrement, selon la valeur enregistrée. */
  message: (valeur: string) => string
}

/** Le champ, « Annuler » (si modifié) et « Enregistrer ». */
export function ChampTechnique({ r, placeholder, message }: ChampTechniqueProps) {
  const [saisie, setSaisie] = useState(r.valeur)
  const modifie = saisie.trim() !== r.valeur
  const refus = refusDuChamp(r, saisie)
  const ecrire = useEcriture(() =>
    api.put<Reglage[]>('/parametres', {
      valeurs: { [r.cle]: saisie.trim() },
      version_globale: r.version_globale,
    }),
  )
  return (
    <div className={styles.colonne}>
      <Champ libelle={r.libelle} aide={r.aide} erreur={refus || null}>
        <Saisie
          valeur={saisie}
          max={r.cle === 'adresse_publique' ? 200 : 500}
          placeholder={placeholder}
          onChange={setSaisie}
        />
      </Champ>
      <div className={styles.rangee}>
        {modifie ? <Bouton onClick={() => setSaisie(r.valeur)}>Annuler</Bouton> : null}
        <Bouton
          variante="principal"
          grise={modifie ? undefined : 'Aucune modification'}
          blocages={refus ? [refus] : []}
          attente="Enregistrement…"
          onClick={async () => {
            await ecrire.mutateAsync()
            dire(message(saisie.trim()))
          }}
        >
          Enregistrer
        </Bouton>
      </div>
    </div>
  )
}

export function Technique() {
  const { lu, reglage } = useReglageTechnique('adresse_publique')
  return (
    <Carte titre="Réglages techniques" remplir>
      <Note>
        L’adresse que portent les QR des étiquettes et des téléphones. Vide : l’adresse du serveur sur le
        réseau de l’usine. Les autres réglages du serveur (base, port, HTTPS, sauvegardes) se changent dans
        son fichier de lancement, pas ici.
      </Note>
      {reglage ? (
        <ChampTechnique
          key={reglage.version}
          r={reglage}
          placeholder="http://mac-usine:8050"
          message={() => 'Adresse des téléphones enregistrée.'}
        />
      ) : lu.isPending ? null : (
        <Note ton="critique">Le réglage « Adresse du serveur pour les téléphones » est introuvable.</Note>
      )}
    </Carte>
  )
}
