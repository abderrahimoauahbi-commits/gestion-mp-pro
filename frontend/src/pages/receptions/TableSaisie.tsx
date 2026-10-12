/**
 * Le tableau de la saisie d'un camion (ECRANS-PRO 4.16) : ligne par ligne, le lot (ou « Lot
 * interne »), le reste à livrer et l'excédent (tous lots ensemble), l'annonce du BL, la pesée et
 * son écart, les palettes et les bobines, le prix, le magasin, la qualité, les observations.
 */

import { Nombre } from '../../composants/saisie/Nombre'
import { Saisie } from '../../composants/saisie/Saisie'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { nombre } from '../../lib/format'
import styles from '../plan-achat/achats.module.css'
import cadre from './TableSaisie.module.css'
import { type LigneSaisie } from './calculSaisie'
import {
  Bobines,
  ChoixMagasin,
  Lot,
  Pese,
  Prix,
  QUALITES,
  Reference,
  Reste,
  type ContexteTable,
} from './CellulesSaisie'

export type { ContexteTable }

/** Un seul champ numérique changé. */
function un(cle: 'quantite_bl' | 'nb_palettes', v: number | null): Partial<LigneSaisie> {
  const m: Partial<LigneSaisie> = {}
  m[cle] = v
  return m
}

/** Un champ numérique de la ligne (annonce du BL, palettes). */
function champNombre(x: ContexteTable, cle: 'quantite_bl' | 'nb_palettes', libelle: string) {
  return (l: LigneSaisie) => (
    <Nombre
      valeur={l[cle]}
      onChange={(v) => x.modifier(l.cle, un(cle, v))}
      min={0}
      decimales={3}
      libelle={`${libelle} de ${l.reference}`}
      className={styles.champCourt}
    />
  )
}

function colonnes1(x: ContexteTable): Colonne<LigneSaisie>[] {
  return [
    { cle: 'reference', titre: 'Référence · bon', triable: false, rendu: (l) => <Reference l={l} x={x} /> },
    {
      cle: 'lot',
      titre: 'Lot',
      aide: 'Le n° de lot imprimé sur l’étiquette du fournisseur ; à défaut, « Lot interne »',
      triable: false,
      rendu: (l) => <Lot l={l} x={x} />,
    },
    {
      cle: 'attendu',
      titre: 'Reste (kg)',
      aide: 'Reste à livrer : ce que la commande attend encore, commandé moins déjà reçu',
      droite: true,
      triable: false,
      rendu: (l) => <Reste l={l} x={x} />,
    },
    {
      cle: 'quantite_bl',
      titre: 'Annoncé BL (kg)',
      aide: 'La quantité écrite sur le bon de livraison',
      droite: true,
      triable: false,
      unite: 'kg',
      total: true,
      rendu: champNombre(x, 'quantite_bl', 'Annoncé BL (kg)'),
    },
    {
      cle: 'quantite_pesee',
      titre: 'Pesé (kg)',
      aide: 'Le poids relevé à la bascule : c’est lui qui entre en stock',
      droite: true,
      triable: false,
      unite: 'kg',
      total: true,
      valeur: (l) => (l.qualite === 'refuse' ? 0 : (l.quantite_pesee ?? 0)),
      rendu: (l) => <Pese l={l} x={x} />,
    },
  ]
}

function colonnes2(x: ContexteTable): Colonne<LigneSaisie>[] {
  return [
    {
      cle: 'bobines',
      titre: 'Palettes · bobines',
      aide: 'Palettes complètes (le catalogue sait combien de bobines porte une palette), puis les bobines en plus ; dessous, le poids d’une bobine face au catalogue',
      droite: true,
      triable: false,
      rendu: (l) => (
        <span className={styles.cellule}>
          {l.bobinesPalette ? (
            <>
              {champNombre(x, 'nb_palettes', 'Palettes')(l)}
              <span className={styles.note}>palettes × {nombre(l.bobinesPalette)} bob.</span>
            </>
          ) : null}
          <Bobines l={l} x={x} />
        </span>
      ),
    },
    {
      cle: 'prix',
      titre: 'Prix / kg',
      aide: 'Le prix payé au kilo : celui du bon s’il est confirmé, sinon à saisir (proposé au prix du catalogue)',
      droite: true,
      triable: false,
      rendu: (l) => <Prix l={l} x={x} />,
    },
  ]
}

function colonnes3(x: ContexteTable): Colonne<LigneSaisie>[] {
  return [
    {
      cle: 'qualite',
      titre: 'Qualité · magasin',
      aide: 'Conforme : en stock ; sous réserve : en quarantaine, non utilisable ; refusé : n’entre pas. Dessous, le magasin de rangement',
      triable: false,
      rendu: (l) => (
        <span className={styles.cellule}>
          <select
            className={styles.choix}
            aria-label={`Qualité de ${l.reference}`}
            value={l.qualite}
            onChange={(e) => {
              const q = QUALITES.find((o) => o.valeur === e.target.value)
              if (q) x.modifier(l.cle, { qualite: q.valeur })
            }}
          >
            {QUALITES.map((q) => (
              <option key={q.valeur} value={q.valeur} title={q.titre}>
                {q.libelle}
              </option>
            ))}
          </select>
          <ChoixMagasin l={l} x={x} />
        </span>
      ),
    },
    {
      cle: 'observations',
      titre: 'Observations',
      triable: false,
      rendu: (l) => (
        <Saisie
          valeur={l.observations}
          onChange={(v) => x.modifier(l.cle, { observations: v })}
          placeholder={l.qualite === 'conforme' ? '' : 'motif…'}
          libelle={`Observations de ${l.reference}`}
          className={styles.champCourt}
        />
      ),
    },
  ]
}

function colonnes(x: ContexteTable): Colonne<LigneSaisie>[] {
  return [...colonnes1(x), ...colonnes2(x), ...colonnes3(x)]
}

export function TableSaisie(x: ContexteTable) {
  return (
    <div className={cadre.tableSaisie}>
      <DataTable<LigneSaisie>
        libelle="Lignes du camion"
        lignes={x.lignes}
        colonnes={colonnes(x)}
        cle={(l) => l.cle}
        recherche={false}
        hauteur="fenetre"
        vide="Choisissez les références arrivées du bon ci-dessus, ou ajoutez une matière hors commande."
      />
    </div>
  )
}
