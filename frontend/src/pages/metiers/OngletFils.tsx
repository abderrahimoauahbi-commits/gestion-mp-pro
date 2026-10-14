/**
 * Onglet « Fils montés » de la fiche d'un métier (`/metiers/:id?onglet=fils`) : une ligne par
 * étage (occupé / laize, bobines, kilos) et ses fils (référence, mètres, remplissage des bobines
 * borné 0…100, bobines, poids, étage, observations) ; pied « Toute la machine » en largeur occupée (an. 13) ; ajout d'un
 * fil au poids de bobine retenu par le montage (an. 11). Lecture seule pour les achats.
 */
import { Fragment } from 'react'
import { Link } from 'react-router'

import { Badge } from '../../composants/retour/Badge'
import { Bouton } from '../../composants/saisie/Bouton'
import { Nombre } from '../../composants/saisie/Nombre'
import { Saisie } from '../../composants/saisie/Saisie'
import { Selecteur } from '../../composants/saisie/Selecteur'
import { CadreAgrandissable } from '../../composants/tableaux/Cadre'
import { kg, nombre, part, poidsBobine } from '../../lib/format'
import { bobinesDe, poidsRetenu } from '../atelier/calculMontage'
import { largeurs, type FilForme } from './formeMetier'
import styles from './metiers.module.css'
import { AjoutFil } from './AjoutFil'
import type { FicheMetierEtat } from './useFicheMetier'

interface Props {
  e: FicheMetierEtat
  ecrit: boolean
  /** Le lien « ouvrir la matière » (direction, achats). */
  lienMatiere: boolean
}

/** Le poids d'un fil monté : bobines × poids d'une bobine × remplissage des bobines / 100. */
const poidsFil = (bobines: number, poidsBobine: number, pourcentage: number | null) =>
  (bobines * poidsBobine * (pourcentage ?? 0)) / 100

/** Les étiquettes d'un fil : sans poids de bobine, ou pesé loin du catalogue. */
function Alertes({ e, f, poids }: { e: FicheMetierEtat; f: FilForme; poids: number }) {
  const lu = e.m.fils.find((x) => x.matiere_id === f.matiere_id && x.etage === f.etage)
  return (
    <span className={styles.badges}>
      {!poids ? (
        <Badge ton="critique">
          aucun poids de bobine (ni pesé, ni au catalogue) : ce fil ne pèse rien dans le stock
        </Badge>
      ) : null}
      {lu?.ecart_hors_tolerance && lu.ecart_mesure != null ? (
        <Badge ton="attention">{`pesé ${part(lu.ecart_mesure, 0)} au catalogue : le catalogue est à revoir`}</Badge>
      ) : null}
    </span>
  )
}

/** La référence d'un fil : désignation, poids de bobine retenu et d'où il vient, alertes, lien. */
function CelluleReference({ e, f, lienMatiere }: { e: FicheMetierEtat; f: FilForme; lienMatiere: boolean }) {
  const poids = poidsRetenu(e.m, e.matieres, f.matiere_id)
  const lu = e.matieres?.find((x) => x.matiere_id === f.matiere_id)
  return (
    <td>
      <strong>{f.reference}</strong>
      <div className={styles.note}>
        {[f.designation, poids ? poidsBobine(poids) : '', lu?.origine_poids ?? '']
          .filter(Boolean)
          .join(' · ')}
        {lu && lu.poids_bobine_catalogue !== poids
          ? ` (catalogue ${nombre(lu.poids_bobine_catalogue, 0, 2)} kg)`
          : ''}
      </div>
      <Alertes e={e} f={f} poids={poids} />
      {lienMatiere ? <Link to={`/matieres/${f.matiere_id}`}>ouvrir la matière</Link> : null}
    </td>
  )
}

/** Les mètres montés (0…1000) et le remplissage des bobines (0…100 %, borné à la frappe, an. 12). */
function CellulesLargeur({
  f,
  ecrit,
  changer,
}: {
  f: FilForme
  ecrit: boolean
  changer: (m: Partial<FilForme>) => void
}) {
  return (
    <>
      <td className={styles.etroit}>
        <Nombre
          libelle={`Mètres de ${f.reference}`}
          valeur={f.metres}
          min={0}
          max={1000}
          decimales={3}
          desactive={!ecrit}
          onChange={(metres) => changer({ metres })}
        />
      </td>
      <td className={styles.etroit}>
        <Nombre
          libelle={`Bobines pleines de ${f.reference} (%)`}
          valeur={f.pourcentage}
          min={0}
          max={100}
          decimales={2}
          desactive={!ecrit}
          onChange={(pourcentage) => changer({ pourcentage })}
        />
      </td>
    </>
  )
}

function LigneFil({ e, f, ecrit, lienMatiere, nbEtages }: Props & { f: FilForme; nbEtages: number }) {
  const changer = (m: Partial<FilForme>) =>
    e.maj({ fils: e.forme.fils.map((x) => (x.cle === f.cle ? { ...x, ...m } : x)) })
  const poids = poidsRetenu(e.m, e.matieres, f.matiere_id)
  const reglage = { actif: true, bobines_par_metre: e.forme.bobines_par_metre ?? 0 }
  const bobines = bobinesDe(reglage, {
    matiere_id: f.matiere_id,
    metres: f.metres ?? 0,
    pourcentage: f.pourcentage ?? 0,
  })
  const etages = Array.from({ length: Math.max(nbEtages, f.etage) }, (_, i) => i + 1)
  return (
    <tr className={(f.metres ?? 0) > 0 ? undefined : styles.filAlerte}>
      <CelluleReference e={e} f={f} lienMatiere={lienMatiere} />
      <CellulesLargeur f={f} ecrit={ecrit} changer={changer} />
      <td className={styles.droite}>{nombre(bobines)}</td>
      <td className={styles.droite}>{nombre(poidsFil(bobines, poids, f.pourcentage), 1)}</td>
      <td>
        <Selecteur
          libelle={`Étage de ${f.reference}`}
          valeur={f.etage}
          effacable={false}
          desactive={!ecrit}
          options={etages.map((n) => ({
            id: n,
            titre: n > nbEtages ? `Étage ${n} (hors machine)` : `Étage ${n}`,
          }))}
          onChange={(etage) => etage != null && changer({ etage })}
        />
      </td>
      <td>
        <Saisie
          libelle={`Observations de ${f.reference}`}
          valeur={f.commentaire}
          max={300}
          desactive={!ecrit}
          onChange={(commentaire) => changer({ commentaire })}
        />
      </td>
      <td>
        {ecrit ? (
          <Bouton
            taille="petit"
            variante="fantome"
            titre="Retirer ce fil du métier"
            onClick={() => e.maj({ fils: e.forme.fils.filter((x) => x.cle !== f.cle) })}
          >
            Retirer
          </Bouton>
        ) : null}
      </td>
    </tr>
  )
}

function LigneEtage({
  e,
  n,
  fils,
  nbEtages,
}: {
  e: FicheMetierEtat
  n: number
  fils: FilForme[]
  nbEtages: number
}) {
  const laize = e.forme.laize ?? 0
  const occupe = largeurs(e.forme).get(n) ?? 0
  const reglage = { actif: true, bobines_par_metre: e.forme.bobines_par_metre ?? 0 }
  const b = fils.reduce(
    (t, f) =>
      t + bobinesDe(reglage, { matiere_id: 0, metres: f.metres ?? 0, pourcentage: f.pourcentage ?? 0 }),
    0,
  )
  const p = fils.reduce(
    (t, f) =>
      t +
      poidsFil(
        bobinesDe(reglage, { matiere_id: 0, metres: f.metres ?? 0, pourcentage: f.pourcentage ?? 0 }),
        poidsRetenu(e.m, e.matieres, f.matiere_id),
        f.pourcentage,
      ),
    0,
  )
  const trop = laize > 0 && occupe > laize + 1e-6
  const texte = [
    fils.length ? `Étage ${n} · ${nombre(fils.length)} fil(s)` : `Étage ${n} · vide`,
    n > nbEtages ? '— au-delà du dernier étage' : '',
    trop ? '— plus large que la laize' : '',
  ].filter(Boolean)
  return (
    <tr className={trop || n > nbEtages ? `${styles.etage} ${styles.tropLarge}` : styles.etage}>
      <td>{texte.join(' ')}</td>
      <td colSpan={2} className={styles.droite}>{`${nombre(occupe, 2)} / ${nombre(laize, 2)} m`}</td>
      <td className={styles.droite}>{nombre(b)}</td>
      <td className={styles.droite}>{nombre(p, 0, 2)}</td>
      <td colSpan={3} />
    </tr>
  )
}

export function OngletFils(props: Props) {
  const { e } = props
  const nbEtages = e.forme.etages ?? 0
  const max = Math.max(nbEtages, ...e.forme.fils.map((f) => f.etage))
  const reglage = { actif: true, bobines_par_metre: e.forme.bobines_par_metre ?? 0 }
  const tous = e.forme.fils.map((f) => ({
    f,
    b: bobinesDe(reglage, { matiere_id: 0, metres: f.metres ?? 0, pourcentage: f.pourcentage ?? 0 }),
  }))
  const totalLargeur = [...largeurs(e.forme).values()].reduce((t, l) => t + l, 0)
  const totalPoids = tous.reduce((t, x) => t + poidsFil(x.b, poidsRetenu(e.m, e.matieres, x.f.matiere_id), x.f.pourcentage), 0) // prettier-ignore
  return (
    <>
      <CadreAgrandissable>
        <table className={styles.table} aria-label="Fils montés">
          <thead>
            <tr>
              <th>Référence</th>
              <th className={styles.droite}>Mètres</th>
              <th className={styles.droite} title="À quel pourcentage les bobines sont pleines">
                Bobines pleines (%)
              </th>
              <th className={styles.droite}>Bobines</th>
              <th className={styles.droite}>Poids (kg)</th>
              <th>Étage</th>
              <th>Observations</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {Array.from({ length: max }, (_, i) => i + 1).map((n) => {
              const fils = e.forme.fils.filter((f) => f.etage === n)
              return (
                <Fragment key={n}>
                  <LigneEtage e={e} n={n} fils={fils} nbEtages={nbEtages} />
                  {fils.map((f) => (
                    <LigneFil key={f.cle} {...props} f={f} nbEtages={nbEtages} />
                  ))}
                </Fragment>
              )
            })}
          </tbody>
          <tfoot>
            <tr className={styles.pied}>
              <td>Toute la machine</td>
              <td colSpan={2} className={styles.droite}>{`${nombre(totalLargeur, 2)} m occupés`}</td>
              <td className={styles.droite}>{nombre(tous.reduce((t, x) => t + x.b, 0))}</td>
              <td className={styles.droite}>{kg(totalPoids)}</td>
              <td colSpan={3} />
            </tr>
          </tfoot>
        </table>
      </CadreAgrandissable>
      {props.ecrit ? <AjoutFil e={e} /> : null}
    </>
  )
}
