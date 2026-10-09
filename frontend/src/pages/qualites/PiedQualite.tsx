/**
 * Le pied de la fiche qualité. Direction : Supprimer (confirmé ; grisé si des ordres l'ont
 * fabriquée), l'état de la saisie (« À corriger avant d'enregistrer : Poil, Ruban. »,
 * « Non enregistré : la fiche et la recette. », « Aucune modification. »), « Annuler les
 * modifications » / « Fermer » (gardés), « Enregistrer ». Achats et alimentation : « Fermer »
 * seulement (P7-30).
 */
import { useFermerFenetre } from '../../composants/mise-en-page/Fenetre'
import { Bouton } from '../../composants/saisie/Bouton'
import { Confirmer } from '../../composants/saisie/Confirmer'
import { nombre } from '../../lib/format'
import styles from '../catalogue/catalogue.module.css'
import type { FicheQualiteEtat } from './useFicheQualite'

/** L'état de la saisie, dit dans le pied. */
export function etatSaisie(corriger: readonly string[], sale: boolean, disparues: boolean): string {
  if (corriger.length) return `À corriger avant d’enregistrer : ${corriger.join(', ')}.`
  if (sale || disparues) return 'Non enregistré : la fiche et la recette.'
  return 'Aucune modification.'
}

function SupprimerQualite({ f }: { f: FicheQualiteEtat }) {
  const q = f.base
  if (!q) return null
  const fabriquee = q.fabrications
    ? [
        `Fabriquée par ${nombre(q.fabrications)} ordre(s) : elle appartient à l’historique. La désactiver plutôt (fiche)`,
      ]
    : []
  return (
    <Confirmer
      variante="danger"
      question={`Supprimer la qualité ${q.code}, sa recette et son plan ?`}
      oui="Oui, supprimer"
      blocages={fabriquee}
      grise={f.sale ? 'Enregistrer ou abandonner d’abord la saisie en cours' : undefined}
      titre="Supprimer une qualité qui n’a jamais été fabriquée"
      onOui={f.supprimer}
    >
      Supprimer
    </Confirmer>
  )
}

export function PiedQualite({
  f,
  ecrit,
  corriger,
}: {
  f: FicheQualiteEtat
  ecrit: boolean
  corriger: readonly string[]
}) {
  const fermer = useFermerFenetre()
  const q = f.base
  if (!ecrit || !q)
    return (
      <div className={styles.pied}>
        <span className={styles.pousse} />
        <Bouton onClick={fermer}>Fermer</Bouton>
      </div>
    )
  const disparues = f.forme.lignes.some((l) => l.disparue)
  return (
    <div className={styles.pied}>
      <SupprimerQualite f={f} />
      <span className={styles.pousse} />
      <span className={styles.etat} aria-live="polite">
        {etatSaisie(corriger, f.sale, disparues)}
      </span>
      <Bouton variante="fantome" onClick={fermer}>
        {f.sale ? 'Annuler les modifications' : 'Fermer'}
      </Bouton>
      <Bouton
        variante="principal"
        manque={f.forme.code.trim() ? undefined : ['le code']}
        blocages={
          corriger.length
            ? [
                `Dans chaque rôle, la recette doit faire 100 % et nommer ses matières : ${corriger.join(', ')}`,
              ]
            : undefined
        }
        grise={
          !f.sale && !disparues
            ? 'Aucune modification.'
            : f.conflit
              ? 'Recharger d’abord la qualité.'
              : undefined
        }
        attente="Enregistrement…"
        onClick={f.enregistrer}
      >
        Enregistrer
      </Bouton>
    </div>
  )
}
