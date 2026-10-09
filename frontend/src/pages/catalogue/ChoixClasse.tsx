/**
 * Choisir une valeur de la classification dans la fiche matière (reprise de `ChoixClasse` de
 * Gestion MP) : recherche à la frappe sur le code, le libellé, la famille, la composition
 * détaillée ; les valeurs actives, et l'actuelle même désactivée (elle se garde, elle ne se
 * pose pas). Une valeur qui manque s'ajoute **sur place** : le panneau d'ajout la crée dans la
 * classification et la choisit aussitôt pour cette matière.
 */
import { useState } from 'react'

import { Note } from '../../composants/retour/Note'
import { dire } from '../../composants/retour/Messages'
import { Bouton } from '../../composants/saisie/Bouton'
import { Selecteur, type OptionSelecteur } from '../../composants/saisie/Selecteur'
import { api } from '../../lib/api'
import { useEcriture } from '../../lib/requetes'
import { ChampsValeur, corpsValeur, versFormeValeur, type FormeValeur } from './ChampsValeur'
import styles from './catalogue.module.css'
import type { DefinitionListe, Valeur } from './types'

/** « PP — Polypropylène », et ce qui aide à la reconnaître dessous. */
export function optionValeur(v: Valeur): OptionSelecteur {
  const titre = v.libelle && v.libelle !== v.code ? `${v.code} — ${v.libelle}` : v.code
  const sous = [v.famille, v.composition_detaillee, v.actif ? '' : 'désactivée'].filter(Boolean).join(' · ')
  return {
    id: v.id,
    titre,
    sous: sous || undefined,
    recherche: [v.valeur, v.unite, v.commentaire].filter(Boolean).join(' '),
  }
}

/** Les valeurs proposées : les actives, et la valeur actuelle même désactivée. */
export function optionsListe(valeurs: readonly Valeur[], actuelle: number | null): OptionSelecteur[] {
  return valeurs
    .filter((v) => v.actif || v.id === actuelle)
    .sort((a, b) => a.code.localeCompare(b.code, 'fr', { numeric: true }))
    .map(optionValeur)
}

function PanneauAjout({
  d,
  onAjoutee,
  onAnnuler,
}: {
  d: DefinitionListe
  onAjoutee: (v: Valeur) => void
  onAnnuler: () => void
}) {
  const [forme, setForme] = useState<FormeValeur>(() => versFormeValeur(null))
  const ecriture = useEcriture((f: FormeValeur) =>
    api.post<Valeur>(`/classification/${d.liste}`, corpsValeur(d, f)),
  )
  const code = corpsValeur(d, forme).code
  const ajouter = async () => {
    const v = await ecriture.mutateAsync(forme)
    dire(`« ${v.code} » ajouté${d.feminin ? 'e' : ''} à la classification.`)
    onAjoutee(v)
  }
  return (
    <div className={styles.panneau} role="group" aria-label={`Ajouter ${d.un} à la classification`}>
      <strong>Ajouter {d.un} à la classification</strong>
      <ChampsValeur d={d} forme={forme} onChange={(m) => setForme((f) => ({ ...f, ...m }))} complet={false} />
      <Note>Elle rejoint la classification et se choisit aussitôt pour cette matière.</Note>
      <div className={styles.rangee}>
        <Bouton onClick={onAnnuler}>Annuler</Bouton>
        <Bouton
          variante="principal"
          manque={code ? undefined : ['le code']}
          attente="Ajout…"
          onClick={ajouter}
        >
          {code ? `Ajouter « ${code} »` : 'Ajouter'}
        </Bouton>
      </div>
    </div>
  )
}

export function ChoixClasse({
  d,
  valeurs,
  valeur,
  onChange,
  desactive,
}: {
  d: DefinitionListe
  valeurs: readonly Valeur[]
  valeur: number | null
  onChange: (id: number | null) => void
  desactive?: boolean
}) {
  const [ajout, setAjout] = useState(false)
  const actives = valeurs.filter((v) => v.actif).length
  return (
    <>
      <Selecteur<number>
        valeur={valeur}
        options={optionsListe(valeurs, valeur)}
        onChange={(id) => onChange(id)}
        placeholder={d.placeholder}
        vide={actives ? 'Rien ne correspond.' : 'Aucune valeur.'}
        limite={60}
        desactive={desactive}
      />
      {desactive ? null : ajout ? (
        <PanneauAjout
          d={d}
          onAnnuler={() => setAjout(false)}
          onAjoutee={(v) => {
            setAjout(false)
            onChange(v.id)
          }}
        />
      ) : (
        <span>
          <Bouton taille="petit" variante="fantome" icone="plus" onClick={() => setAjout(true)}>
            Ajouter {d.un}
          </Bouton>
        </span>
      )}
    </>
  )
}
