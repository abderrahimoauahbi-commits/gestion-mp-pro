/**
 * Les colonnes du plan de production : la qualité (et, modifiée, « Enregistrer » · « Annuler »),
 * la base mensuelle (saisie seule : les mois ne la changent jamais), les douze mois de l'année
 * (coefficients ou m², l'un donnant l'autre sur la base), le total de l'année, l'état.
 * Un coefficient hors de 0 à 20 est dit dans sa cellule et grise « Enregistrer » avec la raison.
 */
import { Link } from 'react-router'

import { Badge } from '../../composants/retour/Badge'
import { Bouton } from '../../composants/saisie/Bouton'
import { Nombre } from '../../composants/saisie/Nombre'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { nombre } from '../../lib/format'
import { Double } from '../stock/cellules'
import styles from './production.module.css'
import {
  COEF_MAX,
  COEF_MIN,
  depuisM2,
  etatAuPlan,
  horsBornes,
  MOIS_CALENDAIRES,
  SANS_BASE,
  somme,
  type QualitePlan,
  type SaisiePlan,
} from './plan'

export type ModePlan = 'coef' | 'm2'

export interface ContextePlan {
  mode: ModePlan
  modifiable: boolean
  valeurs: (q: QualitePlan) => SaisiePlan
  modifiee: (q: QualitePlan) => boolean
  modifier: (q: QualitePlan, s: SaisiePlan) => void
  enregistrer: (q: QualitePlan) => Promise<void>
  annuler: (q: QualitePlan) => void
  occupe: boolean
  moisCourant: number
}

const RAISON_BORNES = `Un coefficient reste entre ${COEF_MIN} et ${COEF_MAX} : corriger les cellules en rouge.`

function Qualite({ q, c }: { q: QualitePlan; c: ContextePlan }) {
  const v = c.valeurs(q)
  return (
    <span className={styles.qualite}>
      <Double haut={q.code} bas={q.nom} />
      {c.modifiable && c.modifiee(q) ? (
        <span className={styles.gestes}>
          <Bouton
            taille="petit"
            variante="principal"
            grise={horsBornes(v) ? RAISON_BORNES : undefined}
            occupe={c.occupe}
            titre={`Enregistrer le plan de ${q.code}`}
            onClick={() => c.enregistrer(q)}
          >
            Enregistrer
          </Bouton>
          <Bouton taille="petit" variante="fantome" onClick={() => c.annuler(q)}>
            Annuler
          </Bouton>
        </span>
      ) : null}
    </span>
  )
}

function Mois({ q, i, c }: { q: QualitePlan; i: number; c: ContextePlan }) {
  const v = c.valeurs(q)
  const coef = v.saisonnalite[i] ?? 1
  const m2 = coef * v.base_mensuelle
  if (!c.modifiable)
    return (
      <span title={c.mode === 'coef' ? `${nombre(m2)} m²` : `coefficient ${nombre(coef, 2)}`}>
        {c.mode === 'coef' ? nombre(coef, 2) : nombre(m2)}
      </span>
    )
  if (c.mode === 'm2')
    return (
      <span title={v.base_mensuelle > 0 ? `coefficient ${nombre(coef, 2)}` : SANS_BASE}>
        <Nombre
          className={styles.cellule}
          valeur={Math.round(m2)}
          min={0}
          decimales={0}
          desactive={v.base_mensuelle <= 0}
          libelle={`${q.code}, ${MOIS_CALENDAIRES[i]} (m²)`}
          onChange={(x) => c.modifier(q, depuisM2(v, i, Math.max(0, x ?? 0)))}
        />
      </span>
    )
  return (
    <Nombre
      className={styles.cellule}
      valeur={Math.round(coef * 1000) / 1000}
      min={COEF_MIN}
      max={COEF_MAX}
      decimales={6}
      libelle={`${q.code}, coefficient de ${MOIS_CALENDAIRES[i]}`}
      onChange={(x) =>
        c.modifier(q, { ...v, saisonnalite: v.saisonnalite.map((y, j) => (j === i ? (x ?? 0) : y)) })
      }
    />
  )
}

function Etat({ q, c }: { q: QualitePlan; c: ContextePlan }) {
  const etat = etatAuPlan(q, c.valeurs(q))
  if (etat === 'recette_incomplete' || etat === 'sans_recette')
    return (
      <Link to={`/qualites/${q.id}?onglet=recette`} title="Ouvrir la recette de la qualité">
        <Badge famille="qualite_plan" valeur={etat} />
      </Link>
    )
  return <Badge famille="qualite_plan" valeur={etat} />
}

function colonnesMois(c: ContextePlan): Colonne<QualitePlan>[] {
  return MOIS_CALENDAIRES.map((m, i) => ({
    cle: `m${i}`,
    titre: i === c.moisCourant ? `${m} ●` : m,
    aide: `${m} : ${c.mode === 'coef' ? 'coefficient' : 'm²'}${i === c.moisCourant ? ' (mois en cours)' : ''}`,
    droite: true,
    triable: false,
    valeur: (q) => c.valeurs(q).saisonnalite[i] ?? null,
    rendu: (q) => <Mois q={q} i={i} c={c} />,
  }))
}

function Base({ q, c }: { q: QualitePlan; c: ContextePlan }) {
  const v = c.valeurs(q)
  if (!c.modifiable) return <>{nombre(v.base_mensuelle)}</>
  return (
    <Nombre
      className={styles.cellule}
      valeur={v.base_mensuelle}
      min={0}
      decimales={2}
      libelle={`${q.code}, base mensuelle (m²)`}
      onChange={(x) => c.modifier(q, { ...v, base_mensuelle: Math.max(0, x ?? 0) })}
    />
  )
}

function Annuel({ v }: { v: SaisiePlan }) {
  const moyenne = somme(v.saisonnalite) / 12
  return (
    <Double
      haut={nombre(somme(v.saisonnalite.map((k) => k * v.base_mensuelle)))}
      bas={
        v.base_mensuelle > 0 && Math.abs(moyenne - 1) > 0.05 ? `coef. moyen ${nombre(moyenne, 2)}` : undefined
      }
    />
  )
}

export function colonnesPlan(c: ContextePlan): Colonne<QualitePlan>[] {
  return [
    {
      cle: 'code',
      titre: 'Qualité',
      valeur: (q) => q.code,
      recherche: (q) => [q.nom],
      rendu: (q) => <Qualite q={q} c={c} />,
    },
    {
      cle: 'base',
      titre: 'Base / mois (m²)',
      aide: 'Les m² d’un mois ordinaire (coefficient 1) : ils ne changent que si vous les saisissez',
      droite: true,
      valeur: (q) => c.valeurs(q).base_mensuelle,
      rendu: (q) => <Base q={q} c={c} />,
    },
    ...colonnesMois(c),
    {
      cle: 'annuel',
      titre: 'Total / an (m²)',
      droite: true,
      valeur: (q) => somme(c.valeurs(q).saisonnalite.map((k) => k * c.valeurs(q).base_mensuelle)),
      rendu: (q) => <Annuel v={c.valeurs(q)} />,
    },
    {
      cle: 'etat',
      titre: 'État',
      valeur: (q) => etatAuPlan(q, c.valeurs(q)),
      rendu: (q) => <Etat q={q} c={c} />,
    },
  ]
}
