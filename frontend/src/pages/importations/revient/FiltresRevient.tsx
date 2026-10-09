/**
 * Les filtres de l'analyse (ECRANS-PRO 5.15), sur deux rangées compactes, tout écrit dans
 * l'adresse :
 * 1. statut du dossier, période d'arrivée, qualité, « + Ajouter une matière… » ;
 * 2. les cinq listes liées (composition, titrage, type de fil, couleur, fournisseur),
 *    « + Combinaison », « N critère(s) » et « Effacer les filtres » (dès deux critères) ;
 * puis, s'il y en a, les puces des matières choisies et des combinaisons retenues (« Réunion de »).
 *
 * La recherche texte est dans la barre du tableau ; l'axe (« Regrouper par ») aussi.
 */
import { Bouton } from '../../../composants/saisie/Bouton'
import { DateChamp } from '../../../composants/saisie/DateChamp'
import { Segments } from '../../../composants/saisie/Segments'
import { Selecteur, type OptionSelecteur } from '../../../composants/saisie/Selecteur'
import { classes } from '../../../composants/mise-en-page/classes'
import { nombre } from '../../../lib/format'
import type { OptionFiltre } from '../../../composants/tableaux/filtrage'
import {
  CLES_FILTRES,
  CRITERES,
  criteresVides,
  ecrireCombinaisons,
  ecrireMatieres,
  enCours,
  libelleCombinaison,
  nombreCriteres,
  type Critere,
  type EtatRevient,
  type Modifier,
  type Statut,
} from './etat'
import styles from './revient.module.css'

const STATUTS: readonly { valeur: Statut; libelle: string }[] = [
  { valeur: '', libelle: 'Ouverts et clos' },
  { valeur: 'clos', libelle: 'Dossiers clos' },
  { valeur: 'ouvert', libelle: 'Dossiers ouverts' },
]

/** « Du … au … » : la date d'arrivée du dossier (un dossier sans date n'est jamais exclu). */
export function Periode({ etat, modifier }: { etat: EtatRevient; modifier: Modifier }) {
  return (
    <span className={styles.periode} title="Date d’arrivée du dossier">
      <span>Du</span>
      <span className={styles.date}>
        <DateChamp
          libelle="Du"
          valeur={etat.du}
          max={etat.au || undefined}
          onChange={(v) => modifier({ du: v })}
        />
      </span>
      <span>au</span>
      <span className={styles.date}>
        <DateChamp
          libelle="Au"
          valeur={etat.au}
          min={etat.du || undefined}
          onChange={(v) => modifier({ au: v })}
        />
      </span>
    </span>
  )
}

/** Le choix d'une qualité (« CODE — nom »), dans l'adresse (`?qualite=`). */
export function ChoixQualite(p: {
  etat: EtatRevient
  modifier: Modifier
  options: readonly OptionSelecteur[]
  placeholder: string
  libelle: string
}) {
  return (
    <span className={styles.qualite} title={p.libelle}>
      <Selecteur
        valeur={p.etat.qualite}
        options={p.options}
        libelle={p.libelle}
        placeholder={p.placeholder}
        onChange={(id) => p.modifier({ qualite: id == null ? null : String(id) })}
      />
    </span>
  )
}

/** Les cinq listes liées, chacune avec le nombre de matières de chaque valeur. */
function ListesLiees({
  etat,
  modifier,
  options,
}: {
  etat: EtatRevient
  modifier: Modifier
  options: Record<Critere, OptionFiltre[]>
}) {
  return (
    <>
      {CRITERES.map((c) => {
        const pose = etat.criteres[c.cle]
        return (
          <select
            key={c.cle}
            aria-label={c.libelle}
            className={classes(styles.liste, pose && styles.pose)}
            value={pose}
            onChange={(e) => modifier({ [c.adresse]: e.target.value || null })}
          >
            <option value="">{c.tous}</option>
            {options[c.cle].map((o) => (
              <option key={o.valeur} value={o.valeur}>
                {o.libelle} ({nombre(o.nombre)})
              </option>
            ))}
          </select>
        )
      })}
    </>
  )
}

/** « + Combinaison », « N critère(s) », « Effacer les filtres ». */
function Gestes({ etat, modifier }: { etat: EtatRevient; modifier: Modifier }) {
  const courante = enCours(etat.criteres)
  const vide = Object.keys(courante).length === 0
  const n = nombreCriteres(etat)
  const effacer = () => modifier(Object.fromEntries(CLES_FILTRES.map((c) => [c, null])))
  return (
    <>
      <Bouton
        taille="petit"
        manque={vide ? ['Choisissez au moins un critère'] : undefined}
        titre="+ Ajouter cette combinaison : la retenir, puis en composer une autre ; le résultat les réunit"
        onClick={() =>
          modifier({ combinaisons: ecrireCombinaisons([...etat.combinaisons, courante]), ...criteresVides() })
        }
      >
        + Combinaison
      </Bouton>
      {n ? (
        <span className={styles.criteres}>
          {nombre(n)} critère{n > 1 ? 's' : ''}
        </span>
      ) : null}
      {n >= 2 ? (
        <Bouton taille="petit" variante="fantome" onClick={effacer}>
          Effacer les filtres
        </Bouton>
      ) : null}
    </>
  )
}

/** Une puce qu'on retire d'un clic sur ×. */
function Puce({ texte, retirer, titre }: { texte: string; retirer: () => void; titre: string }) {
  return (
    <span className={styles.puce}>
      {texte}
      <button
        type="button"
        className={styles.retirer}
        title={titre}
        aria-label={`${titre} : ${texte}`}
        onClick={retirer}
      >
        ×
      </button>
    </span>
  )
}

/** Les matières choisies et la réunion des combinaisons retenues. */
function Retenues({
  etat,
  modifier,
  reference,
}: {
  etat: EtatRevient
  modifier: Modifier
  reference: (id: number) => string
}) {
  const courante = libelleCombinaison(enCours(etat.criteres))
  if (!etat.matieres.length && !etat.combinaisons.length) return null
  return (
    <div className={styles.rangee}>
      {etat.matieres.length ? <span className={styles.note}>Matières :</span> : null}
      {etat.matieres.map((id) => (
        <Puce
          key={id}
          texte={reference(id)}
          titre="Retirer cette matière"
          retirer={() => modifier({ matieres: ecrireMatieres(etat.matieres.filter((x) => x !== id)) })}
        />
      ))}
      {etat.combinaisons.length ? <span className={styles.note}>Réunion de :</span> : null}
      {etat.combinaisons.map((c, i) => (
        <Puce
          key={`${i}-${libelleCombinaison(c)}`}
          texte={libelleCombinaison(c)}
          titre="Retirer cette combinaison"
          retirer={() =>
            modifier({ combinaisons: ecrireCombinaisons(etat.combinaisons.filter((_, j) => j !== i)) })
          }
        />
      ))}
      {etat.combinaisons.length && courante ? (
        <span className={styles.note}>+ en cours : {courante}</span>
      ) : null}
    </div>
  )
}

export interface FiltresRevientProps {
  etat: EtatRevient
  modifier: Modifier
  qualites: readonly OptionSelecteur[]
  matieres: readonly OptionSelecteur[]
  options: Record<Critere, OptionFiltre[]>
  reference: (id: number) => string
}

/** Les filtres des vues « Regroupé » et « Lot par lot ». */
export function FiltresRevient({
  etat,
  modifier,
  qualites,
  matieres,
  options,
  reference,
}: FiltresRevientProps) {
  const proposees = matieres.filter((m) => !etat.matieres.includes(m.id))
  return (
    <>
      <div className={styles.rangee}>
        <Segments<Statut>
          libelle="Statut du dossier"
          valeur={etat.statut}
          options={STATUTS}
          onChange={(v) => modifier({ statut: v || null })}
        />
        <Periode etat={etat} modifier={modifier} />
        <ChoixQualite
          etat={etat}
          modifier={modifier}
          options={qualites}
          placeholder="Toutes qualités"
          libelle="Ne garder que les fils de la recette d’une qualité"
        />
        <span
          className={styles.matiere}
          title="Ajouter une matière : l’analyse ne garde que les matières choisies"
        >
          <Selecteur<number>
            valeur={null}
            options={proposees}
            libelle="Ajouter une matière"
            placeholder="+ Ajouter une matière…"
            onChange={(id) => id != null && modifier({ matieres: ecrireMatieres([...etat.matieres, id]) })}
          />
        </span>
      </div>
      <div className={styles.rangee}>
        <ListesLiees etat={etat} modifier={modifier} options={options} />
        <Gestes etat={etat} modifier={modifier} />
      </div>
      <Retenues etat={etat} modifier={modifier} reference={reference} />
    </>
  )
}
