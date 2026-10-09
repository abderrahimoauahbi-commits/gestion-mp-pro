/**
 * Le pied de la fiche matière : gestes à place fixe. À gauche ce qui retire (Supprimer, confirmé,
 * grisé avec les traces que le serveur a comptées ; Désactiver confirmé ou Réactiver) ; à droite
 * l'état de la saisie, « Fermer » / « Abandonner les modifications » (gardés) et « Enregistrer »
 * ou « Créer la matière ». Aucun bouton n'est cliquable pour découvrir un refus (R6).
 */
import { useFermerFenetre } from '../../composants/mise-en-page/Fenetre'
import { Bouton } from '../../composants/saisie/Bouton'
import { Confirmer } from '../../composants/saisie/Confirmer'
import styles from './catalogue.module.css'
import { manqueLisible, type Manque } from './formeMatiere'
import type { FicheMatiereEtat } from './useFicheMatiere'

/** Ce qui interdit la suppression (les traces de la matière), en une phrase. */
export function blocagesSuppression(reference: string, usages: readonly string[]): string[] {
  return usages.length
    ? [`« ${reference} » figure dans ${usages.join(', ')} : la désactiver plutôt que la supprimer`]
    : []
}

function Gauche({ f }: { f: FicheMatiereEtat }) {
  const b = f.base
  if (!b) return null
  const enCours = f.sale ? 'Enregistrer d’abord les changements' : undefined
  return (
    <>
      <Confirmer
        variante="danger"
        question={`Supprimer définitivement « ${b.reference} » ?`}
        oui="Oui, supprimer"
        blocages={blocagesSuppression(b.reference, b.usages)}
        grise={enCours}
        titre="Supprimer une matière qui n’a jamais servi"
        onOui={f.supprimer}
      >
        Supprimer
      </Confirmer>
      {b.actif ? (
        <Confirmer
          variante="danger"
          question={`Désactiver « ${b.reference} » ? Elle ne sera plus proposée aux commandes ni aux recettes ; son historique et son stock restent.`}
          oui="Oui, désactiver"
          grise={enCours}
          titre="Ne plus la proposer"
          onOui={() => f.changerEtat(false)}
        >
          Désactiver
        </Confirmer>
      ) : (
        <Bouton
          grise={enCours}
          blocages={b.fournisseur_id ? undefined : ['Choisir d’abord son fournisseur (onglet Achat)']}
          titre="La remettre en service"
          attente="Réactivation…"
          onClick={() => f.changerEtat(true)}
        >
          Réactiver
        </Bouton>
      )}
    </>
  )
}

export function PiedMatiere({
  f,
  manque,
  doublon,
}: {
  f: FicheMatiereEtat
  manque: readonly Manque[]
  doublon: boolean
}) {
  const fermer = useFermerFenetre()
  const creation = !f.base
  return (
    <div className={styles.pied}>
      <Gauche f={f} />
      <span className={styles.pousse} />
      <span className={styles.etat} aria-live="polite">
        {f.sale ? 'Non enregistré.' : creation ? '' : 'Aucune modification.'}
      </span>
      <Bouton
        variante="fantome"
        titre={f.sale ? 'Fermer sans enregistrer : les modifications sont perdues' : undefined}
        onClick={fermer}
      >
        {f.sale ? 'Abandonner les modifications' : 'Fermer'}
      </Bouton>
      <Bouton
        variante="principal"
        manque={manqueLisible(manque)}
        blocages={doublon ? ['une autre matière porte déjà cette référence'] : undefined}
        grise={
          !creation && !f.sale
            ? 'Aucune modification.'
            : f.conflit
              ? 'Recharger d’abord la fiche.'
              : undefined
        }
        attente={creation ? 'Création…' : 'Enregistrement…'}
        onClick={creation ? f.creer : f.enregistrer}
      >
        {creation ? 'Créer la matière' : 'Enregistrer'}
      </Bouton>
    </div>
  )
}
