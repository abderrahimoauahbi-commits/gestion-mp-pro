/**
 * Les colonnes de la liste des métiers : « CODE · Nom » (observations, dernier montage), laize,
 * densité, étages garnis, fils, bobines, « Sur les métiers (kg) » (an. 7), à voir, état. Tri au
 * clic, recherche sur les fils montés (champs cachés), pied de totaux.
 */
import { Badge } from '../../composants/retour/Badge'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { horodatage, nombre, VIDE } from '../../lib/format'
import { nomMetier } from '../atelier/commun'
import type { MetierFiche } from '../atelier/types'
import styles from './metiers.module.css'

/** Ce qui est à voir sur un métier, en étiquettes. */
export function aVoir(m: MetierFiche): { texte: string; ton: 'attention' | 'critique' }[] {
  const ecarts = m.fils.filter((f) => f.ecart_hors_tolerance).length
  const trop = m.etages_trop_larges
  return [
    m.densite_a_saisir ? { texte: 'densité à saisir', ton: 'attention' as const } : null,
    trop.length
      ? {
          texte: `étage${trop.length > 1 ? 's' : ''} ${trop.join(', ')} trop large${trop.length > 1 ? 's' : ''}`,
          ton: 'critique' as const,
        }
      : null,
    m.fils_sans_poids
      ? { texte: `${m.fils_sans_poids} fil(s) sans poids de bobine`, ton: 'critique' as const }
      : null,
    ecarts ? { texte: `${ecarts} bobine(s) mesurée(s) ≠ catalogue`, ton: 'attention' as const } : null,
  ].filter((x) => x != null)
}

export const COLONNES: Colonne<MetierFiche>[] = [
  {
    cle: 'metier',
    titre: 'Métier',
    valeur: (m) => nomMetier(m),
    rendu: (m) => (
      <>
        <span className={m.actif ? styles.code : `${styles.code} ${styles.eteint}`}>{nomMetier(m)}</span>
        <div className={styles.note}>
          {[
            m.commentaire,
            m.dernier_montage
              ? `monté par ${m.dernier_montage.par ?? VIDE} le ${horodatage(m.dernier_montage.quand)}`
              : '',
          ]
            .filter(Boolean)
            .join(' · ')}
        </div>
      </>
    ),
    recherche: (m) => [m.code, m.nom, m.commentaire],
  },
  {
    cle: 'laize',
    titre: 'Laize (m)',
    droite: true,
    valeur: (m) => m.laize,
    rendu: (m) => nombre(m.laize, 2),
  },
  {
    cle: 'densite',
    titre: 'Densité (bobines/m)',
    droite: true,
    valeur: (m) => m.bobines_par_metre,
    rendu: (m) => (m.bobines_par_metre ? nombre(m.bobines_par_metre, 1) : VIDE),
  },
  {
    cle: 'garnis',
    titre: 'Étages garnis',
    droite: true,
    valeur: (m) => m.etages_garnis,
    rendu: (m) => `${nombre(m.etages_garnis)} / ${nombre(m.etages)}`,
  },
  { cle: 'fils', titre: 'Fils montés', droite: true, valeur: (m) => m.fils.length },
  {
    cle: 'bobines',
    titre: 'Bobines',
    droite: true,
    valeur: (m) => m.bobines,
    rendu: (m) => nombre(m.bobines),
    total: true,
  },
  {
    cle: 'poids',
    titre: 'Sur les métiers (kg)',
    droite: true,
    unite: 'kg',
    valeur: (m) => m.sur_les_metiers,
    rendu: (m) => nombre(m.sur_les_metiers, 0, 2),
    total: true,
  },
  {
    cle: 'avoir',
    titre: 'À voir',
    triable: false,
    valeur: (m) =>
      aVoir(m)
        .map((x) => x.texte)
        .join(', '),
    rendu: (m) => (
      <span className={styles.badges}>
        {aVoir(m).map((x) => (
          <Badge key={x.texte} ton={x.ton}>
            {x.texte}
          </Badge>
        ))}
      </span>
    ),
  },
  {
    cle: 'etat',
    titre: 'État',
    valeur: (m) => (m.actif ? 'en service' : 'arrêté'),
    rendu: (m) => <Badge famille="metier" valeur={m.actif ? 'actif' : 'arrete'} />,
  },
]
