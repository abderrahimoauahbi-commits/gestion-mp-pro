/**
 * Fiche commande › Suivi de l'expédition (ECRANS-PRO 4.10) : les étapes du voyage ; seule l'ETA est
 * une attente (elle remplace la livraison prévue dans le calcul du stock projeté), les autres sont
 * des faits constatés, bornés entre la date du bon et aujourd'hui. Un champ vidé s'efface (`null`).
 */
import { Grille } from '../../composants/mise-en-page/Grille'
import { Note } from '../../composants/retour/Note'
import { Champ } from '../../composants/saisie/Champ'
import { DateChamp } from '../../composants/saisie/DateChamp'
import { Saisie } from '../../composants/saisie/Saisie'
import styles from '../plan-achat/achats.module.css'
import { raison, type CommandeFiche, type ExpeditionEntree, type Jalons } from './types'
import type { FormeFiche } from './useFormeFiche'

export type FormeExpedition = Record<keyof Jalons, string>

const JALONS: readonly { cle: keyof Jalons; libelle: string; aide: string; attente?: true }[] = [
  { cle: 'proforma_le', libelle: 'Proforma reçue le', aide: 'la facture provisoire du fournisseur' },
  { cle: 'acompte_le', libelle: 'Acompte payé le', aide: 'le virement d’avance, s’il y en a un' },
  { cle: 'embarquee_le', libelle: 'Embarquée le', aide: 'date de départ (connaissement)' },
  {
    cle: 'eta',
    libelle: 'Arrivée prévue (ETA)',
    aide: 'remplace la livraison prévue dans le calcul',
    attente: true,
  },
  { cle: 'au_port_le', libelle: 'Arrivée au port le', aide: 'déchargement constaté' },
  { cle: 'dedouanee_le', libelle: 'Dédouanée le', aide: 'mainlevée de la douane' },
  { cle: 'arrivee_usine_le', libelle: 'Arrivée à l’usine le', aide: 'le camion à la bascule' },
]

const CLES: readonly (keyof Jalons)[] = [...JALONS.map((j) => j.cle), 'conteneur', 'navire']

/** Un seul champ changé. */
function un(cle: keyof Jalons, valeur: string): Partial<FormeExpedition> {
  const m: Partial<FormeExpedition> = {}
  m[cle] = valeur
  return m
}

export function versFormeExpedition(c: CommandeFiche): FormeExpedition {
  const e = c.expedition
  return {
    proforma_le: e.proforma_le ?? '',
    acompte_le: e.acompte_le ?? '',
    embarquee_le: e.embarquee_le ?? '',
    eta: e.eta ?? '',
    au_port_le: e.au_port_le ?? '',
    dedouanee_le: e.dedouanee_le ?? '',
    arrivee_usine_le: e.arrivee_usine_le ?? '',
    conteneur: e.conteneur,
    navire: e.navire,
  }
}

/** Seuls les champs changés partent (un champ absent garde sa valeur, A-16) ; vidé : `null`. */
export function corpsExpedition(
  f: FormeExpedition,
  initiale: FormeExpedition,
  version: number,
): ExpeditionEntree {
  const corps: ExpeditionEntree = { version }
  for (const cle of CLES) {
    if (f[cle] === initiale[cle]) continue
    corps[cle] = f[cle].trim() || null
  }
  return corps
}

export function VoletExpedition({ c, f }: { c: CommandeFiche; f: FormeFiche<FormeExpedition> }) {
  const refus = raison(c, 'expedition')
  if (!c.parti) return <Note>Ce bon n’est pas encore parti : son expédition se suivra après l’envoi.</Note>
  const lecture = Boolean(refus)
  return (
    <div className={styles.volet}>
      {refus ? <Note ton="attention">{refus}</Note> : null}
      <p className={styles.note}>
        Les étapes du voyage, à remplir au fil des nouvelles du fournisseur ou du transitaire. Seule l’arrivée
        prévue (ETA) est une attente : elle remplace la livraison prévue dans le calcul du stock projeté.
      </p>
      <Grille colonnes={4}>
        {JALONS.map((j) => (
          <Champ key={j.cle} libelle={j.libelle} aide={j.aide}>
            <DateChamp
              valeur={f.forme[j.cle]}
              onChange={(v) => f.maj(un(j.cle, v))}
              min={c.date_commande}
              raisonMin="un jalon ne précède pas la date du bon"
              futurPermis={j.attente}
              desactive={lecture}
            />
          </Champ>
        ))}
        <Champ libelle="N° de conteneur" aide="ex. MSCU1234567">
          <Saisie
            valeur={f.forme.conteneur}
            onChange={(conteneur) => f.maj({ conteneur })}
            max={60}
            desactive={lecture}
          />
        </Champ>
        <Champ libelle="Navire">
          <Saisie
            valeur={f.forme.navire}
            onChange={(navire) => f.maj({ navire })}
            max={80}
            desactive={lecture}
          />
        </Champ>
      </Grille>
    </div>
  )
}
