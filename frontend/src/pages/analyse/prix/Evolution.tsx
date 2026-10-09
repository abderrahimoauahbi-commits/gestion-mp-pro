/**
 * Fenêtre « Évolution des prix payés, matière par matière » (sur la Matrice, les Prix payés et
 * les Opportunités) : huit matières au plus sur une même courbe, le prix moyen du mois dans la
 * monnaie de la facture — un panneau par devise, jamais deux devises sur un axe —, à la couleur
 * du fil (un trait différent à teinte égale). Bascule « Résumé par matière » / « Chaque achat ».
 * L'évolution est en « forte hausse » au-delà du réglage `seuil_hausse_forte` (P8-4).
 */
import { useState } from 'react'

import { Courbes } from '../../../composants/graphiques/Courbes'
import type { Serie } from '../../../composants/graphiques/echelle'
import { Bascule } from '../../../composants/mise-en-page/Bascule'
import { Fenetre } from '../../../composants/mise-en-page/Fenetre'
import { Badge } from '../../../composants/retour/Badge'
import { Note } from '../../../composants/retour/Note'
import type { Colonne } from '../../../composants/tableaux/colonnes'
import { DataTable } from '../../../composants/tableaux/DataTable'
import { date, kg, moisCourt, nombre, partSignee, prix, prixUnite, VIDE } from '../../../lib/format'
import { stylesDesFils } from '../../../lib/teintes'
import styles from '../analyse.module.css'
import { useHistoriquePrix, useMatrice } from '../donnees'
import type { LigneMatrice, PrixPaye } from '../types'
import { MOUVEMENTS, mouvement, seuilsDe, type Seuils } from './commun'

/** Huit matières au plus : au-delà, les courbes ne se lisent plus. */
export const MAX_COURBES = 8

export interface MatiereComparee {
  reference: string
  matiere_id: number | null
}

interface Resume {
  cle: string
  reference: string
  fournisseur: string
  devise: string
  achats: number
  premier: PrixPaye | null
  dernier: PrixPaye | null
  mini: number | null
  maxi: number | null
}

const memeMatiere = (m: MatiereComparee, x: { reference: string; matiere_id?: number | null }) =>
  m.matiere_id != null && x.matiere_id != null ? m.matiere_id === x.matiere_id : m.reference === x.reference

/** Le résumé par (matière, fournisseur, devise) des achats, du premier au dernier. */
export function resumer(matieres: readonly MatiereComparee[], achats: readonly PrixPaye[]): Resume[] {
  const groupes = new Map<string, Resume>()
  for (const m of matieres) {
    const siens = achats
      .filter((a) => memeMatiere(m, a))
      .sort((a, b) => (a.date_bc ?? '').localeCompare(b.date_bc ?? ''))
    if (!siens.length) {
      groupes.set(m.reference, {
        cle: m.reference,
        reference: m.reference,
        fournisseur: '',
        devise: '',
        achats: 0,
        premier: null,
        dernier: null,
        mini: null,
        maxi: null,
      })
    }
    for (const a of siens) {
      const cle = `${a.reference}|${a.fournisseur}|${a.devise}`
      const g = groupes.get(cle) ?? {
        cle,
        reference: a.reference,
        fournisseur: a.fournisseur,
        devise: a.devise,
        achats: 0,
        premier: a,
        dernier: a,
        mini: a.prix_achat,
        maxi: a.prix_achat,
      }
      g.achats += 1
      g.dernier = a
      g.mini = Math.min(g.mini ?? a.prix_achat, a.prix_achat)
      g.maxi = Math.max(g.maxi ?? a.prix_achat, a.prix_achat)
      groupes.set(cle, g)
    }
  }
  return [...groupes.values()]
}

function colonnesResume(seuils: Seuils): Colonne<Resume>[] {
  const evolution = (r: Resume) =>
    r.premier && r.dernier && r.achats > 1
      ? (r.dernier.prix_achat - r.premier.prix_achat) / r.premier.prix_achat
      : null
  return [
    { cle: 'reference', titre: 'Référence', rendu: (r) => <span className={styles.ref}>{r.reference}</span> },
    { cle: 'fournisseur', titre: 'Fournisseur' },
    {
      cle: 'achats',
      titre: 'Achats',
      droite: true,
      rendu: (r) => (r.achats ? nombre(r.achats) : 'jamais acheté'),
    },
    {
      cle: 'premier',
      titre: 'Premier prix',
      droite: true,
      valeur: (r) => r.premier?.prix_achat,
      rendu: (r) => (r.premier ? prixUnite(r.premier.prix_achat, r.devise, 'kg') : VIDE),
    },
    {
      cle: 'premier_le',
      titre: 'Le',
      valeur: (r) => r.premier?.date_bc,
      rendu: (r) => date(r.premier?.date_bc),
    },
    {
      cle: 'dernier',
      titre: 'Dernier prix',
      droite: true,
      valeur: (r) => r.dernier?.prix_achat,
      rendu: (r) => (r.dernier ? prixUnite(r.dernier.prix_achat, r.devise, 'kg') : VIDE),
    },
    {
      cle: 'dernier_le',
      titre: 'Le',
      valeur: (r) => r.dernier?.date_bc,
      rendu: (r) => date(r.dernier?.date_bc),
    },
    {
      cle: 'evolution',
      titre: 'Évolution',
      droite: true,
      valeur: evolution,
      rendu: (r) => {
        const e = evolution(r)
        return e == null ? VIDE : <Badge ton={MOUVEMENTS[mouvement(e, seuils)].ton}>{partSignee(e)}</Badge>
      },
    },
    {
      cle: 'mini',
      titre: 'Mini – maxi',
      droite: true,
      rendu: (r) => (r.mini == null ? VIDE : `${prix(r.mini)} – ${prix(r.maxi)} ${r.devise}`),
    },
  ]
}

type Achat = PrixPaye & { rang: number }

const COLONNES_ACHATS: readonly Colonne<Achat>[] = [
  { cle: 'date_bc', titre: 'Date', rendu: (a) => date(a.date_bc) },
  { cle: 'reference', titre: 'Référence' },
  { cle: 'fournisseur', titre: 'Fournisseur' },
  { cle: 'numero_bc', titre: 'Bon' },
  { cle: 'quantite', titre: 'Quantité (kg)', droite: true, rendu: (a) => kg(a.quantite) },
  {
    cle: 'prix_achat',
    titre: 'Prix payé',
    droite: true,
    rendu: (a) => prixUnite(a.prix_achat, a.devise, 'kg'),
  },
  { cle: 'montant_mad', titre: 'Contre-valeur (MAD)', droite: true, rendu: (a) => nombre(a.montant_mad) },
]

/** Les séries des courbes : une par ligne de matrice (matière × devise), à la couleur du fil. */
function series(lignes: readonly LigneMatrice[]): Serie[] {
  const styleDe = stylesDesFils(
    lignes.map((l) => ({ cle: `${l.reference}|${l.devise}`, couleur: l.couleur })),
  )
  return lignes.map((l) => {
    const s = styleDe.get(`${l.reference}|${l.devise}`)
    return {
      nom: `${l.reference} — ${l.fournisseur}`,
      valeurs: l.prix,
      unite: l.devise,
      couleur: s?.couleur,
      trait: s?.trait,
    }
  })
}

function Avertissements({ laissees, jamais }: { laissees: number; jamais: readonly string[] }) {
  return (
    <>
      {laissees > 0 ? (
        <Note>{`${MAX_COURBES} matières au plus sur une même courbe : les ${laissees} suivantes sont laissées de côté.`}</Note>
      ) : null}
      {jamais.length ? (
        <Note ton="attention">
          {`Jamais achetée, donc sans courbe : ${jamais.join(', ')}. Seul un prix de catalogue existe pour ${jamais.length > 1 ? 'ces matières' : 'cette matière'}, et il n’a pas de date.`}
        </Note>
      ) : null}
    </>
  )
}

interface TablesProps {
  retenues: readonly MatiereComparee[]
  achats: readonly Achat[]
  devises: readonly string[]
  seuils: Seuils
}

/** « Résumé par matière » ou « Chaque achat ». */
function Tables({ retenues, achats, devises, seuils }: TablesProps) {
  const [vue, setVue] = useState<'resume' | 'achats'>('resume')
  return (
    <>
      <div className={styles.rangee}>
        <Bascule
          libelle="Vue des prix"
          vues={[
            { cle: 'resume', libelle: 'Résumé par matière' },
            { cle: 'achats', libelle: `Chaque achat (${nombre(achats.length)})` },
          ]}
          valeur={vue}
          onChange={setVue}
        />
        <span className={styles.note}>
          Prix payés, au kilo, dans la monnaie de la facture.
          {devises.length > 1 ? ` Deux monnaies : un panneau par monnaie (${devises.join(', ')}).` : ''}
        </span>
      </div>
      {vue === 'resume' ? (
        <DataTable<Resume>
          libelle="Résumé par matière"
          lignes={resumer(retenues, achats)}
          colonnes={colonnesResume(seuils)}
          cle={(r) => r.cle}
          recherche={false}
          hauteur="fenetre"
        />
      ) : (
        <DataTable<Achat>
          libelle="Chaque achat"
          lignes={achats}
          colonnes={COLONNES_ACHATS}
          cle={(a) => a.rang}
          recherche={false}
          hauteur="fenetre"
          triInitial={{ cle: 'date_bc', sens: -1 }}
          vide="Aucun achat pour ces matières."
        />
      )}
    </>
  )
}

export function Evolution({
  matieres,
  onFermer,
}: {
  matieres: readonly MatiereComparee[]
  onFermer: () => void
}) {
  const m = useMatrice().data
  const h = useHistoriquePrix().data
  const retenues = matieres.slice(0, MAX_COURBES)
  const lignes = (m?.lignes ?? []).filter((l) => retenues.some((r) => memeMatiere(r, l)))
  const achats = (h?.lignes ?? []).flatMap((a, rang) =>
    retenues.some((r) => memeMatiere(r, a)) ? [{ ...a, rang }] : [],
  )
  const jamais = retenues.filter((r) => !lignes.some((l) => memeMatiere(r, l))).map((r) => r.reference)
  const devises = [...new Set(lignes.map((l) => l.devise))]
  return (
    <Fenetre titre="Évolution des prix payés, matière par matière" taille="tresLarge" onFermer={onFermer}>
      <Avertissements laissees={matieres.length - retenues.length} jamais={jamais} />
      {lignes.length ? (
        <Courbes
          libelle="Prix payés par mois"
          etiquettes={(m?.mois ?? []).map(moisCourt)}
          series={series(lignes)}
          hauteur={260}
          format={(v) => prix(v)}
        />
      ) : null}
      <Tables retenues={retenues} achats={achats} devises={devises} seuils={seuilsDe(m?.seuils)} />
    </Fenetre>
  )
}
