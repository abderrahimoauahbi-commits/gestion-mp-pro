/**
 * Le panneau « Facture du fournisseur » d'une réception validée (ECRANS-PRO 4.17) : la facture ne
 * touche pas au stock, elle se complète ou se corrige même après la validation. Dans un dossier
 * d'importation, son numéro ne change plus ici (lien vers le dossier pour l'en détacher).
 */
import { Link } from 'react-router'

import { Grille } from '../../composants/mise-en-page/Grille'
import { Champ } from '../../composants/saisie/Champ'
import { DateChamp } from '../../composants/saisie/DateChamp'
import { Nombre } from '../../composants/saisie/Nombre'
import { Saisie } from '../../composants/saisie/Saisie'
import { nombre } from '../../lib/format'
import styles from '../plan-achat/achats.module.css'
import type { FormeFacture } from './calculFiche'
import type { ReceptionFiche } from './types'
import type { FormeFiche } from '../commandes/useFormeFiche'

export function PanneauFacture({ r, f }: { r: ReceptionFiche; f: FormeFiche<FormeFacture, ReceptionFiche> }) {
  const dossier = r.dossier
  const sans = !f.forme.numero.trim()
  const delai = r.delai_paiement_jours
  return (
    <div className={styles.panneau}>
      <strong>Facture du fournisseur ({r.devise})</strong>
      <Grille colonnes={4}>
        <Champ
          libelle="N° de facture"
          aide={
            dossier
              ? 'dans un dossier d’importation : pour le changer, l’en détacher d’abord (dossier › Marchandises)'
              : 'vide : détache la facture'
          }
        >
          <Saisie
            valeur={f.forme.numero}
            onChange={(numero) => f.maj({ numero })}
            max={60}
            desactive={Boolean(dossier)}
          />
        </Champ>
        <Champ libelle="Date de facture">
          <DateChamp valeur={f.forme.date} onChange={(date) => f.maj({ date })} desactive={sans} />
        </Champ>
        <Champ libelle={`Montant (${r.devise})`}>
          <Nombre
            valeur={f.forme.montant}
            onChange={(montant) => f.maj({ montant })}
            min={0}
            decimales={2}
            unite={r.devise}
            desactive={sans}
          />
        </Champ>
        <Champ
          libelle="Échéance"
          aide={delai ? `proposée : date + ${nombre(delai)} j` : 'délai de paiement non réglé'}
        >
          <DateChamp
            valeur={f.forme.echeance}
            onChange={(echeance) => f.maj({ echeance })}
            min={f.forme.date || undefined}
            futurPermis
            desactive={sans}
          />
        </Champ>
      </Grille>
      {dossier ? (
        <span className={styles.note}>
          Dans le dossier <Link to={`/dossiers/${dossier.id}?onglet=marchandises`}>{dossier.numero}</Link>.
        </span>
      ) : null}
      <span className={styles.note}>
        La facture ne touche pas au stock : elle se complète ou se corrige même après la validation.
      </span>
    </div>
  )
}
