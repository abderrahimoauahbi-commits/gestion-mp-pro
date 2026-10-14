/**
 * Fiche commande › Prix du fournisseur (ECRANS-PRO 4.9) : réservé aux bons **partis** (le cours ne
 * se fige plus avant l'envoi, anom. 4.8) ; les prix confirmés dans la devise du bon — au kilo, ou
 * **au mètre** pour une matière dont la fiche est au mètre (décision U2 : le serveur reçoit
 * `unite: 'ml'` et ramène au kilo par la densité ; l'écran dit l'équivalent au kilo) —, la date
 * promise que le fournisseur confirme avec eux (anom. 4.7), et le report au catalogue.
 */
import { Badge } from '../../composants/retour/Badge'
import { Note } from '../../composants/retour/Note'
import { Champ } from '../../composants/saisie/Champ'
import { DateChamp } from '../../composants/saisie/DateChamp'
import { Interrupteur } from '../../composants/saisie/Interrupteur'
import { Nombre } from '../../composants/saisie/Nombre'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import {
  arrondi,
  horodatage,
  metres,
  montant,
  nombre,
  partSignee,
  prix,
  prixUnite,
  VIDE,
} from '../../lib/format'
import { aujourdhui } from '../../lib/heure'
import styles from '../plan-achat/achats.module.css'
import { deux } from '../plan-achat/colonnesFournisseurs'
import { raison, type CommandeFiche, type ConfirmationPrix, type LigneCommande } from './types'
import type { FormeFiche } from './useFormeFiche'

export interface FormePrix {
  /** Le prix saisi par ligne, dans l'unité de la ligne (`uniteDe`). */
  prix: Record<string, number | null>
  catalogue: boolean
  livraison: string
}

export type UnitePrix = 'kg' | 'ml'

/** L'unité où le prix de cette ligne se confirme : au mètre quand la fiche est au mètre (U2). */
export function uniteDe(l: Pick<LigneCommande, 'unite_prix' | 'kg_par_ml'>): UnitePrix {
  return l.unite_prix === 'ml' && l.kg_par_ml > 0 ? 'ml' : 'kg'
}

/** Un prix saisi dans l'unité de la ligne, ramené au kilo (÷ densité au mètre). */
export function enKg(l: LigneCommande, v: number): number {
  return uniteDe(l) === 'ml' ? v / l.kg_par_ml : v
}

/** Un prix au kilo (serveur, catalogue) dans l'unité de la ligne (× densité au mètre). */
export function depuisKg(l: LigneCommande, v: number): number {
  return uniteDe(l) === 'ml' ? arrondi(v * l.kg_par_ml, 6) : v
}

export function versFormePrix(c: CommandeFiche): FormePrix {
  return {
    prix: Object.fromEntries(
      c.lignes.map((l) => [String(l.id), l.prix_confirme && l.prix > 0 ? depuisKg(l, l.prix) : null]),
    ),
    catalogue: true,
    livraison: '',
  }
}

/** Les prix saisis (> 0), ligne par ligne, chacun dans son unité. */
export const saisis = (c: CommandeFiche, f: FormePrix) =>
  c.lignes
    .filter((l) => (f.prix[String(l.id)] ?? 0) > 0)
    .map((l) => ({ ligne_id: l.id, prix: f.prix[String(l.id)] ?? 0, unite: uniteDe(l) }))

/** Les références dont le prix du catalogue changera (comparé au kilo). */
export function changeantAuCatalogue(c: CommandeFiche, f: FormePrix): string[] {
  return c.lignes
    .filter((l) => {
      const v = f.prix[String(l.id)]
      return v != null && v > 0 && Math.abs(enKg(l, v) - l.prix_catalogue) > 0.0005
    })
    .map((l) => l.reference)
}

export function corpsPrix(c: CommandeFiche, f: FormePrix, version: number): ConfirmationPrix {
  const corps: ConfirmationPrix = {
    version,
    lignes: saisis(c, f),
    mettre_a_jour_catalogue: f.catalogue,
  }
  if (f.livraison) corps.date_livraison_prevue = f.livraison
  return corps
}

/** « Reprendre les prix du catalogue » : les prix vides prennent celui du catalogue (même devise). */
export function reprendreCatalogue(c: CommandeFiche, f: FormePrix): FormePrix {
  const p = { ...f.prix }
  for (const l of c.lignes) {
    const cat = l.devise_catalogue === c.devise ? l.prix_catalogue : 0
    if (p[String(l.id)] == null && cat > 0) p[String(l.id)] = depuisKg(l, cat)
  }
  return { ...f, prix: p }
}

/** La question de la confirmation. */
export function questionPrix(c: CommandeFiche, f: FormePrix): string {
  const changent = changeantAuCatalogue(c, f)
  const suite = f.catalogue
    ? changent.length
      ? `Le prix du catalogue changera pour : ${changent.join(', ')}.`
      : 'Aucun prix du catalogue ne change.'
    : 'Le catalogue garde ses prix.'
  return `Confirmer ${nombre(saisis(c, f).length)} prix ? ${suite}`
}

function Ecart({ l, v, devise }: { l: LigneCommande; v: number | null; devise: string }) {
  if (!v || !l.prix_catalogue || l.devise_catalogue !== devise) return <>{VIDE}</>
  const e = enKg(l, v) / l.prix_catalogue - 1
  if (Math.abs(e) < 0.005) return <span className={styles.note}>identique</span>
  return <Badge ton={e > 0 ? 'attention' : 'ok'}>{partSignee(e)}</Badge>
}

/** Le prix du catalogue dans l'unité de la ligne, et son équivalent dans l'autre unité. */
function Catalogue({ l }: { l: LigneCommande }) {
  if (!l.prix_catalogue) return <>{VIDE}</>
  if (uniteDe(l) === 'ml')
    return deux(
      prixUnite(depuisKg(l, l.prix_catalogue), l.devise_catalogue, 'ml'),
      `soit ${prix(l.prix_catalogue)} / kg`,
    )
  return deux(
    prixUnite(l.prix_catalogue, l.devise_catalogue, 'kg'),
    l.kg_par_ml ? `soit ${prix(l.prix_catalogue * l.kg_par_ml)} / ml` : null,
  )
}

function colonnes1(_c: CommandeFiche, _f: FormeFiche<FormePrix>): Colonne<LigneCommande>[] {
  return [
    {
      cle: 'reference',
      titre: 'Référence',
      rendu: (l) => deux(<span className={styles.ref}>{l.reference}</span>, l.designation),
    },
    {
      cle: 'quantite',
      titre: 'Quantité (kg)',
      droite: true,
      rendu: (l) => deux(nombre(l.quantite), l.kg_par_ml ? metres(l.quantite, l.kg_par_ml) : null),
    },
    {
      cle: 'prix_catalogue',
      titre: 'Prix catalogue',
      droite: true,
      rendu: (l) => <Catalogue l={l} />,
    },
  ]
}

function colonnes2(c: CommandeFiche, f: FormeFiche<FormePrix>): Colonne<LigneCommande>[] {
  const v = (l: LigneCommande) => f.forme.prix[String(l.id)] ?? null
  return [
    {
      cle: 'saisi',
      titre: 'Prix confirmé',
      droite: true,
      triable: false,
      rendu: (l) => (
        <span className={styles.cellule}>
          <Nombre
            valeur={v(l)}
            onChange={(n) => f.maj({ prix: { ...f.forme.prix, [String(l.id)]: n && n > 0 ? n : null } })}
            min={0}
            decimales={uniteDe(l) === 'ml' ? 6 : 4}
            unite={`${c.devise} / ${uniteDe(l)}`}
            placeholder="à saisir"
            libelle={`Prix confirmé de ${l.reference} (${c.devise} / ${uniteDe(l)})`}
          />
          {v(l) && uniteDe(l) === 'ml' ? (
            <span className={styles.note}>soit {prix(enKg(l, v(l) ?? 0))} / kg</span>
          ) : null}
        </span>
      ),
    },
    {
      cle: 'ecart',
      titre: 'Écart',
      droite: true,
      triable: false,
      rendu: (l) => <Ecart l={l} v={v(l)} devise={c.devise} />,
    },
    {
      cle: 'montant',
      titre: 'Montant',
      droite: true,
      rendu: (l) => (v(l) ? montant(enKg(l, v(l) ?? 0) * l.quantite, c.devise) : VIDE),
    },
  ]
}

function colonnes3(_c: CommandeFiche, _f: FormeFiche<FormePrix>): Colonne<LigneCommande>[] {
  return [
    {
      cle: 'etat',
      titre: 'État',
      rendu: (l) =>
        deux(
          <Badge famille="prix" valeur={l.prix_confirme ? 'confirme' : 'a_confirmer'} />,
          l.prix_confirme && (l.confirme_par || l.confirme_le)
            ? [
                l.confirme_par ? `par ${l.confirme_par}` : '',
                l.confirme_le ? `le ${horodatage(l.confirme_le)}` : '',
              ]
                .filter(Boolean)
                .join(' ')
            : null,
        ),
    },
  ]
}

function colonnes(c: CommandeFiche, f: FormeFiche<FormePrix>): Colonne<LigneCommande>[] {
  return [...colonnes1(c, f), ...colonnes2(c, f), ...colonnes3(c, f)]
}

export function VoletPrix({ c, f }: { c: CommandeFiche; f: FormeFiche<FormePrix> }) {
  const refus = raison(c, 'prix')
  if (!c.parti)
    return <Note>Le bon n’est pas encore parti : les prix se confirment au retour du fournisseur.</Note>
  const auMetre = c.lignes.some((l) => uniteDe(l) === 'ml')
  return (
    <div className={styles.volet}>
      {refus ? <Note ton="attention">{refus}</Note> : null}
      <p className={styles.note}>
        Recopiez les prix que le fournisseur a confirmés (proforma, courriel), <strong>en {c.devise}</strong>,
        tels qu’il les annonce : au kilo
        {auMetre ? (
          <>
            , ou <strong>au mètre</strong> pour une matière dont la fiche est au mètre (le logiciel ramène au
            kilo par la densité ; l’équivalent au kilo s’affiche sous la saisie)
          </>
        ) : null}
        . Ce sont eux que la réception retiendra comme prix payé. Quand tous les prix d’un bon envoyé sont
        confirmés, il passe à « Confirmée » ; le cours de la devise se fige à la première confirmation, avec
        la livraison promise.
      </p>
      <div className={styles.rangee}>
        {c.confirme_le ? null : (
          <Champ libelle="Livraison prévue confirmée par le fournisseur" aide="vide : la date du bon reste">
            <DateChamp
              valeur={f.forme.livraison}
              onChange={(livraison) => f.maj({ livraison })}
              min={aujourdhui()}
              futurPermis
            />
          </Champ>
        )}
        <Interrupteur
          valeur={f.forme.catalogue}
          onChange={(catalogue) => f.maj({ catalogue })}
          libelle="Mettre aussi à jour le prix du catalogue (conseillé : c’est le prix du moment)"
        />
      </div>
      <div className={styles.tableFenetre}>
        <DataTable<LigneCommande>
          libelle="Prix du fournisseur"
          lignes={c.lignes}
          colonnes={colonnes(c, f)}
          cle={(l) => l.id}
          recherche={false}
          hauteur="fenetre"
        />
      </div>
    </div>
  )
}
