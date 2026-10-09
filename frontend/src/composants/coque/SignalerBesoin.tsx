/**
 * « Signaler un besoin » depuis le bureau (menu du compte, rôles métier) : une matière
 * (facultative), le besoin, l'urgence → POST /signalements (route 222). Les achats le voient sur
 * leur accueil. La saisie est gardée : fermer avec un texte demande d'abord.
 */
import { useState } from 'react'

import { api } from '../../lib/api'
import { useEcriture, useLecture } from '../../lib/requetes'
import type { Schema } from '../../lib/types'
import { Fenetre } from '../mise-en-page/Fenetre'
import { Grille } from '../mise-en-page/Grille'
import { Erreur } from '../retour/Erreur'
import { dire } from '../retour/Messages'
import { Bouton } from '../saisie/Bouton'
import { Champ } from '../saisie/Champ'
import { Segments } from '../saisie/Segments'
import { SelecteurMatiere, type MatiereChoix } from '../saisie/SelecteurMatiere'
import { Zone } from '../saisie/Zone'

type SignalementCreation = Schema<'SignalementCreation'>
type Urgence = SignalementCreation['urgence']
type MatiereResume = Schema<'MatiereResume'>

/** Ce que la fenêtre lit d'une matière de `GET /matieres` (route 70). */
type MatiereLue = Pick<
  MatiereResume,
  'id' | 'reference' | 'designation' | 'composition' | 'type_fil' | 'titrage' | 'couleur' | 'fournisseur'
>

/** Ce que le sélecteur de matière lit d'une matière. */
export function versChoix(m: MatiereLue): MatiereChoix {
  return {
    id: m.id,
    reference: m.reference,
    designation: m.designation,
    composition: m.composition,
    type: m.type_fil,
    titrage: m.titrage,
    couleur: m.couleur,
    fournisseur: m.fournisseur,
  }
}

/** Ce qui manque avant d'envoyer. */
export function manqueSignalement(texte: string): string[] {
  return texte.trim().length >= 2 ? [] : ['le besoin (2 caractères au moins)']
}

export function SignalerBesoin({ onFermer }: { onFermer: () => void }) {
  const matieres = useLecture<MatiereResume[]>('/matieres', { actif: true })
  const [matiere, setMatiere] = useState<number | null>(null)
  const [texte, setTexte] = useState('')
  const [urgence, setUrgence] = useState<Urgence>('normale')
  const envoi = useEcriture((s: SignalementCreation) => api.post('/signalements', s))
  const envoyer = async () => {
    await envoi.mutateAsync({ matiere_id: matiere, texte: texte.trim(), urgence })
    dire('Signalé : les achats le voient sur leur accueil.')
    onFermer()
  }
  return (
    <Fenetre
      titre="Signaler un besoin"
      sous="Un fil qui manque, une palette qui finit : les achats le voient sur leur accueil."
      onFermer={onFermer}
      sale={texte.trim() !== '' || matiere != null}
      pied={
        <Bouton variante="principal" manque={manqueSignalement(texte)} attente="Envoi…" onClick={envoyer}>
          Signaler aux achats
        </Bouton>
      }
    >
      <Grille colonnes={1}>
        <Erreur erreur={matieres.error} onReessayer={() => void matieres.refetch()} />
        <SelecteurMatiere
          libelle="Matière (facultatif)"
          matieres={(matieres.data ?? []).map(versChoix)}
          valeur={matiere}
          onChange={(id) => setMatiere(id)}
        />
        <Champ libelle="Quel besoin ?" obligatoire>
          <Zone
            valeur={texte}
            onChange={setTexte}
            max={500}
            lignes={4}
            placeholder="Plus que deux palettes de beige, la série 8F commence lundi…"
          />
        </Champ>
        <Champ libelle="Urgence" groupe>
          <Segments
            valeur={urgence}
            onChange={setUrgence}
            options={[
              { valeur: 'normale', libelle: 'Normal' },
              { valeur: 'urgente', libelle: 'Urgent' },
            ]}
          />
        </Champ>
      </Grille>
    </Fenetre>
  )
}
