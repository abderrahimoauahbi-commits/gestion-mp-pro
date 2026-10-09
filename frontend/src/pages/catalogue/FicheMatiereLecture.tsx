/**
 * La fiche matière lue par l'alimentation (R10) : classification, rôle, densité, fournisseur
 * (son nom seul), conditionnement et stock ; **aucun** prix, devise, minimum de commande ni pièce
 * jointe — les champs sont absents, pas remplacés par « — ». Pas de pied d'écriture.
 */
import { Definitions } from '../../composants/mise-en-page/Definitions'
import { kg, nombre } from '../../lib/format'
import { conditionnementLisible } from './colonnesMatieres'
import type { MatiereFiche } from './types'

export function VoletLectureClassification({ m }: { m: MatiereFiche }) {
  return (
    <Definitions
      items={[
        ['Référence', m.reference],
        ['Désignation', m.designation],
        ['Rôle dans le tapis', m.lineaire ? `${m.role} (au mètre)` : m.role],
        [
          'Composition',
          m.composition_libelle ? `${m.composition} — ${m.composition_libelle}` : m.composition,
        ],
        ['Type de fil', m.type_fil],
        ['Titrage', m.titrage],
        [
          'Couleur',
          m.couleur_libelle && m.couleur_libelle !== m.couleur
            ? `${m.couleur} — ${m.couleur_libelle}`
            : m.couleur,
        ],
        ['Code couleur', m.couleur_code],
        ['Densité', m.densite ? `${nombre(m.densite, 0, 6)} kg / ml` : ''],
        ['Fournisseur', m.fournisseur],
      ]}
    />
  )
}

export function VoletLectureConditionnement({ m }: { m: MatiereFiche }) {
  return (
    <Definitions
      items={[
        ['Se commande en', conditionnementLisible(m)],
        ['kg / bobine', m.poids_bobine ? kg(m.poids_bobine) : ''],
        ['Bobines par palette', m.bobines_palette ? nombre(m.bobines_palette) : ''],
        ['Stock minimum', m.stock_min ? kg(m.stock_min) : ''],
        ['Couverture minimum', m.couv_min_mois ? `${nombre(m.couv_min_mois, 0, 2)} mois` : ''],
        ['Groupe d’équivalence', m.groupe_equiv],
      ]}
    />
  )
}
