/**
 * Le pied de la fiche fournisseur, gestes à place fixe : Supprimer (confirmé ; grisé avec tout
 * ce que le serveur a compté), Désactiver (confirmé) ou Réactiver, puis l'état de la saisie,
 * « Fermer » / « Abandonner les modifications » (gardés), « Enregistrer » ou « Créer le
 * fournisseur ».
 */
import { useFermerFenetre } from '../../composants/mise-en-page/Fenetre'
import { Bouton } from '../../composants/saisie/Bouton'
import { Confirmer } from '../../composants/saisie/Confirmer'
import styles from './catalogue.module.css'
import { manquesFournisseur } from './formeFournisseur'
import type { FicheFournisseurEtat } from './useFicheFournisseur'

/** Ce qui empêche la suppression, en une phrase (« Il a 3 matière(s), 2 commande(s)… »). */
export function blocagesFournisseur(empechements: readonly string[]): string[] {
  return empechements.length ? [`Il a ${empechements.join(', ')} : le désactiver plutôt`] : []
}

function Gauche({ f }: { f: FicheFournisseurEtat }) {
  const b = f.base
  if (!b) return null
  const enCours = f.sale ? 'Enregistrer d’abord les changements' : undefined
  return (
    <>
      <Confirmer
        variante="danger"
        question={`Supprimer définitivement « ${b.nom} » ?`}
        oui="Oui, supprimer"
        blocages={blocagesFournisseur(b.empechements)}
        grise={enCours}
        titre="Supprimer un fournisseur qui n’a jamais servi"
        onOui={f.supprimer}
      >
        Supprimer
      </Confirmer>
      {b.actif ? (
        <Confirmer
          variante="danger"
          question={`Désactiver « ${b.nom} » ? Il ne sera plus proposé pour une commande ni une matière ; son historique reste.`}
          oui="Oui, désactiver"
          grise={enCours}
          titre="Ne plus le proposer"
          onOui={() => f.changerEtat(false)}
        >
          Désactiver
        </Confirmer>
      ) : (
        <Bouton
          grise={enCours}
          titre="Le proposer de nouveau"
          attente="Réactivation…"
          onClick={() => f.changerEtat(true)}
        >
          Réactiver
        </Bouton>
      )}
    </>
  )
}

export function PiedFournisseur({ f }: { f: FicheFournisseurEtat }) {
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
        manque={manquesFournisseur(f.forme)}
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
        {creation ? 'Créer le fournisseur' : 'Enregistrer'}
      </Bouton>
    </div>
  )
}
