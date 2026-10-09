/**
 * Fiche dossier › Marchandises (ECRANS-PRO 5.8) : recherche dans l'adresse (`&q=`), cours par devise
 * et notes (`CoursDevises`), puis une ligne par marchandise : référence (vers sa fiche), lot, poids,
 * valeur facture, cours payé (saisi en quittant le champ ; vide = « cours du jour », `null`), achat,
 * charges hors TVA (détail par poste en infobulle), coût hors TVA et au kilo, observations ; une
 * réception se détache toute entière, une ligne saisie à la main se retire (blocages dits avant le
 * clic : des frais visés sur elles).
 */
import { Link } from 'react-router'

import { Badge } from '../../composants/retour/Badge'
import { dire } from '../../composants/retour/Messages'
import { Confirmer } from '../../composants/saisie/Confirmer'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { useRechercheAdresse } from '../../lib/adresse'
import { cours, kg, montant, montantPrecis, nombre, part, partSignee, prix, VIDE } from '../../lib/format'
import { NombreEnregistre, TexteEnregistre } from './champsEnregistres'
import { CoursDevises } from './CoursDevises'
import styles from './Importations.module.css'
import type { DossierFiche, LigneDossier } from './types'
import type { GestesDossier } from './useDossier'

const arreter = (e: { stopPropagation: () => void }) => e.stopPropagation()

interface Ctx {
  d: DossierFiche
  g: GestesDossier
  modifiable: boolean
  noter: () => void
}

/** Les frais visés sur ces marchandises (ils empêchent de les sortir du dossier). */
const fraisSur = (d: DossierFiche, ids: ReadonlySet<number>) =>
  d.frais.filter((f) => f.ligne_id != null && ids.has(f.ligne_id)).length

function Reference({ l }: { l: LigneDossier }) {
  return (
    <span className={styles.valeur}>
      <Link to={`/matieres/${l.matiere_id}`} onClick={arreter}>
        <strong className={styles.sansCoupure}>{l.reference}</strong>
      </Link>
      <span className={`${styles.note} ${styles.coupe}`} title={l.famille}>
        {l.famille}
        {l.facture ? ` · facture ${l.facture}` : ''}
        {l.reception_id ? (
          <>
            {' · '}
            <Link to={`/receptions/${l.reception_id}`} onClick={arreter}>
              {l.reception}
            </Link>
          </>
        ) : l.reception_ligne_id == null ? (
          ' · saisie à la main'
        ) : null}
      </span>
    </span>
  )
}

/** La note sous le cours : cours du jour, du bon, écart au cours du jour. */
function NoteCours({ l }: { l: LigneDossier }) {
  if (l.cours == null) return <span className={styles.note}>cours du jour * ({cours(l.cours_jour)})</span>
  if (l.cours_ecart != null && Math.abs(l.cours_ecart) > 0.05)
    return <span className={styles.rouge}>{partSignee(l.cours_ecart, 0)} / cours du jour</span>
  if (l.cours_bon != null && l.cours === l.cours_bon)
    return (
      <span className={styles.note}>
        cours du bon{' '}
        {l.bon_id ? (
          <Link to={`/commandes/${l.bon_id}`} onClick={arreter}>
            {l.bon}
          </Link>
        ) : (
          l.bon
        )}
      </span>
    )
  if (l.cours_origine === 'clos_au_jour')
    return <span className={styles.note}>cours du jour figé à la clôture</span>
  return null
}

function CoursPaye({ l, c }: { l: LigneDossier; c: Ctx }) {
  if (l.devise === 'MAD') return <>{VIDE}</>
  if (!c.modifiable) {
    return (
      <span className={styles.valeur} title={l.cours == null ? 'cours du jour (réglages)' : 'cours payé'}>
        <span>
          {cours(l.cours_applique)}
          {l.cours == null || l.cours_origine === 'clos_au_jour' ? ' *' : ''}
        </span>
        <NoteCours l={l} />
      </span>
    )
  }
  return (
    <span className={styles.valeur}>
      <NombreEnregistre
        libelle={`Cours payé de ${l.reference}`}
        valeur={l.cours}
        decimales={4}
        min={0.0001}
        max={1000}
        placeholder={cours(l.cours_applique)}
        onEnregistrer={async (v) => {
          await c.g.ligne(l.id, { cours: v })
          c.noter()
        }}
      />
      <NoteCours l={l} />
    </span>
  )
}

function Geste({ l, c }: { l: LigneDossier; c: Ctx }) {
  const { d, g } = c
  if (!c.modifiable) return null
  if (l.reception_id != null) {
    const memes = d.lignes.filter((x) => x.reception_id === l.reception_id)
    if (memes[0]?.id !== l.id) return <span className={styles.note}>avec {l.reception}</span>
    const n = fraisSur(d, new Set(memes.map((x) => x.id)))
    return (
      <Confirmer
        taille="petit"
        variante="danger"
        question={`Détacher la réception ${l.reception ?? ''} (${nombre(memes.length)} ligne(s)) ? Sa marchandise attendra de nouveau son dossier ; les frais restent à celui-ci.`}
        oui="Oui, détacher"
        titre="Une marchandise reçue sort du dossier avec toute sa réception — pour annuler la réception ou corriger le numéro de sa facture. Les frais payés restent au dossier."
        blocages={
          n
            ? [
                `${nombre(n)} frais porte(nt) sur une marchandise de la réception ${l.reception ?? ''} : les affecter à tout le dossier (onglet Frais, « Porte sur ») avant de la détacher`,
              ]
            : []
        }
        onOui={async () => {
          await g.detacher(l.reception_id ?? 0)
          dire(
            `Réception ${l.reception ?? ''} détachée : sa marchandise attend de nouveau son dossier, les frais restent ici.`,
          )
        }}
      >
        Détacher la réception
      </Confirmer>
    )
  }
  const n = fraisSur(d, new Set([l.id]))
  return (
    <Confirmer
      taille="petit"
      variante="danger"
      question="Retirer cette ligne ?"
      oui="Oui, retirer"
      titre="Retirer cette marchandise du dossier"
      blocages={
        n
          ? [
              `${nombre(n)} frais porte(nt) sur cette seule marchandise : les affecter à tout le dossier, ou les retirer, avant de la retirer`,
            ]
          : []
      }
      onOui={async () => {
        await g.retirerLigne(l.id)
        dire(`${l.reference} retirée du dossier.`)
      }}
    >
      Retirer
    </Confirmer>
  )
}

type C = Colonne<LigneDossier>

const LOT: C = {
  cle: 'lot',
  titre: 'Lot',
  rendu: (l) =>
    l.lot_id != null ? (
      <Link to={`/lots/${l.lot_id}`} onClick={arreter} className={`${styles.mono} ${styles.sansCoupure}`}>
        {l.lot}
      </Link>
    ) : (
      l.lot || VIDE
    ),
}

const POIDS: C = {
  cle: 'quantite_kg',
  titre: 'Poids',
  droite: true,
  unite: 'kg',
  total: true,
  rendu: (l) => kg(l.quantite_kg),
}

const VALEUR: C = {
  cle: 'valeur_devise',
  titre: 'Valeur facture',
  droite: true,
  unite: (l) => l.devise,
  total: true,
  rendu: (l) => (
    <span className={styles.valeur}>
      <span>{montantPrecis(l.valeur_devise, l.devise)}</span>
      <span className={styles.note}>
        {l.quantite_kg ? `${nombre(l.valeur_devise / l.quantite_kg, 2, 4)} ${l.devise} / kg` : VIDE}
      </span>
    </span>
  ),
}

const CHARGES: C = {
  cle: 'charges_mad',
  titre: 'Charges hors TVA',
  aide: 'toutes les charges sauf la TVA ; le détail par poste en infobulle',
  droite: true,
  unite: 'MAD',
  total: true,
  rendu: (l) => {
    const detail = Object.entries(l.frais_par_poste)
      .map(([poste, m]) => `${poste} : ${montantPrecis(m, 'MAD')}`)
      .join(' · ')
    return (
      <span className={styles.valeur} title={detail || 'aucun frais'}>
        <span>{montant(l.charges_mad, 'MAD')}</span>
        <span className={styles.note}>{l.valeur_mad ? part(l.surcout) : VIDE}</span>
      </span>
    )
  },
}

const COUT: C = {
  cle: 'revient_mad',
  titre: 'Coût hors TVA',
  droite: true,
  unite: 'MAD',
  total: true,
  rendu: (l) => <strong>{montant(l.revient_mad, 'MAD')}</strong>,
}

const COUT_KG: C = {
  cle: 'revient_kg',
  titre: 'Coût hors TVA / kg',
  aide: 'Au kilo, le cuir, les franges et le ruban compris',
  droite: true,
  rendu: (l) => (
    <span className={styles.valeur}>
      <strong>{l.revient_kg == null ? VIDE : `${prix(l.revient_kg)} MAD`}</strong>
      <span className={styles.note}>achat {prix(l.valeur_kg)}</span>
      {l.negative ? <Badge ton="critique">négatif : un avoir de trop</Badge> : null}
      {l.aberrante ? <Badge ton="critique">frais hors norme</Badge> : null}
    </span>
  ),
}

function Observations({ l, c }: { l: LigneDossier; c: Ctx }) {
  if (!c.modifiable) return <>{l.commentaire || VIDE}</>
  return (
    <TexteEnregistre
      libelle={`Observations de ${l.reference}`}
      valeur={l.commentaire}
      max={300}
      placeholder="bobines abîmées, écart de poids…"
      onEnregistrer={async (v) => {
        await c.g.ligne(l.id, { commentaire: v })
        c.noter()
      }}
    />
  )
}

function colonnes(c: Ctx): C[] {
  const total = c.d.marchandise_mad
  return [
    {
      cle: 'reference',
      titre: 'Référence',
      recherche: (l) => [l.famille, l.facture, l.reception, l.fournisseur, l.commentaire],
      rendu: (l) => <Reference l={l} />,
    },
    LOT,
    POIDS,
    VALEUR,
    {
      cle: 'cours',
      titre: 'Cours payé',
      droite: true,
      valeur: (l) => l.cours_applique,
      rendu: (l) => <CoursPaye l={l} c={c} />,
    },
    {
      cle: 'valeur_mad',
      titre: 'Achat MAD',
      droite: true,
      unite: 'MAD',
      total: true,
      rendu: (l) => (
        <span title={total ? `${part(l.valeur_mad / total)} de la valeur du dossier` : undefined}>
          {montant(l.valeur_mad, 'MAD')}
        </span>
      ),
    },
    CHARGES,
    COUT,
    COUT_KG,
    { cle: 'commentaire', titre: 'Observations', rendu: (l) => <Observations l={l} c={c} /> },
    {
      cle: 'geste',
      titre: '',
      triable: false,
      exporte: false,
      valeur: () => '',
      rendu: (l) => <Geste l={l} c={c} />,
    },
  ]
}

export function VoletMarchandises(c: Ctx) {
  const [q, setQ] = useRechercheAdresse()
  return (
    <div className={styles.pile}>
      <CoursDevises d={c.d} g={c.g} modifiable={c.modifiable} />
      <DataTable
        libelle="Marchandises du dossier"
        lignes={c.d.lignes}
        colonnes={colonnes(c)}
        cle={(l) => l.id}
        recherche={{ valeur: q, onChange: setQ }}
        placeholder="Référence, lot, famille, facture, réception, observations…"
        hauteur="fenetre"
        vide="Aucune marchandise dans ce dossier."
      />
    </div>
  )
}
