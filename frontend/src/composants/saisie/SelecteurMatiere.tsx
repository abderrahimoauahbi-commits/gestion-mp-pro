/**
 * Choisir une matière par ses critères (M22, M75) : composition, type, titrage, couleur,
 * fournisseur se cumulent, chacun ne proposant que les valeurs encore possibles (filtres liés),
 * puis la recherche à la frappe affine sur tout (référence, désignation, code, couleur…).
 *
 * Les matières viennent de la page (`GET matieres`, prix masqués pour l'alimentation) ; leur
 * type sera celui de l'OpenAPI dès qu'il sera publié (`Schema<'MatiereResume'>`).
 */
import { useMemo, useState } from 'react'

import { nombre } from '../../lib/format'
import { optionsLiees, passe, type Choix, type Filtre } from '../tableaux/filtrage'
import { Bouton } from './Bouton'
import { Selecteur, type OptionSelecteur } from './Selecteur'
import styles from './SelecteurMatiere.module.css'

export interface MatiereChoix {
  id: number
  reference: string
  designation?: string | null
  composition?: string | null
  type?: string | null
  titrage?: string | null
  couleur?: string | null
  fournisseur?: string | null
  /** Autres textes cherchés (code fournisseur, suffixe…). */
  recherche?: string | null
}

const CRITERES: readonly Filtre<MatiereChoix>[] = [
  { cle: 'composition', libelle: 'Composition', valeur: (m) => m.composition },
  { cle: 'type', libelle: 'Type', valeur: (m) => m.type },
  { cle: 'titrage', libelle: 'Titrage', valeur: (m) => m.titrage },
  { cle: 'couleur', libelle: 'Couleur', valeur: (m) => m.couleur },
  { cle: 'fournisseur', libelle: 'Fournisseur', valeur: (m) => m.fournisseur },
]

export interface SelecteurMatiereProps {
  matieres: readonly MatiereChoix[]
  valeur: number | null
  onChange: (id: number | null, matiere?: MatiereChoix) => void
  libelle?: string
  /** Critères posés d'avance (le fournisseur d'une commande). */
  criteres?: Choix
}

export function SelecteurMatiere({
  matieres,
  valeur,
  onChange,
  libelle = 'Matière',
  criteres = {},
}: SelecteurMatiereProps) {
  const [choix, setChoix] = useState<Choix>(criteres)
  const retenues = useMemo(() => matieres.filter((m) => passe(m, CRITERES, choix)), [matieres, choix])
  const options: OptionSelecteur[] = retenues.map((m) => ({
    id: m.id,
    titre: m.reference,
    sous: [m.designation, m.fournisseur].filter(Boolean).join(' · ') || undefined,
    recherche: [m.composition, m.type, m.titrage, m.couleur, m.recherche].filter(Boolean).join(' '),
  }))
  const poses = Object.values(choix).filter(Boolean).length
  return (
    <div className={styles.selecteurMatiere}>
      <div className={styles.criteres}>
        {CRITERES.map((f) => (
          <select
            key={f.cle}
            aria-label={f.libelle}
            className={styles.critere}
            value={choix[f.cle] ?? ''}
            onChange={(e) => setChoix({ ...choix, [f.cle]: e.target.value })}
          >
            <option value="">{f.libelle} : tous</option>
            {optionsLiees(matieres, CRITERES, choix, f).map((o) => (
              <option key={o.valeur} value={o.valeur}>
                {o.libelle} ({nombre(o.nombre)})
              </option>
            ))}
          </select>
        ))}
        {poses ? (
          <Bouton taille="petit" variante="fantome" onClick={() => setChoix({})}>
            Effacer les critères
          </Bouton>
        ) : null}
        <span className={styles.compte}>
          {nombre(retenues.length)} matière{retenues.length > 1 ? 's' : ''}
        </span>
      </div>
      <Selecteur
        valeur={valeur}
        options={options}
        libelle={libelle}
        placeholder="Référence, couleur, fournisseur… plusieurs mots"
        onChange={(id) =>
          onChange(
            id,
            matieres.find((m) => m.id === id),
          )
        }
      />
    </div>
  )
}
