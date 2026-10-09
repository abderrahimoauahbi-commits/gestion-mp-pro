/**
 * Le tableau de la préparation (ECRANS-PRO 4.4) : une ligne par matière, cochée pour être
 * commandée (décochée : à demi effacée), saisie dans son unité de commande **et** en kilos, l'écart
 * à la suggestion et le montant indicatif au prix du catalogue.
 */
import { Badge } from '../../composants/retour/Badge'
import { Nombre } from '../../composants/saisie/Nombre'
import { Bouton } from '../../composants/saisie/Bouton'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { arrondi, jours, metres, montant, nombre, partSignee, prixUnite, VIDE } from '../../lib/format'
import { cleStock } from '../../lib/statuts'
import styles from './achats.module.css'
import { deux } from './colonnesFournisseurs'
import { libelleUnite, quantiteEnUnite } from './libelles'
import { avertissement, changerUnite, ecart, type LigneSaisie } from './calculPreparation'

export interface Edition {
  modifier: (id: number, changement: Partial<LigneSaisie>) => void
  remplacer: (id: number, ligne: LigneSaisie) => void
  retirer: (id: number) => void
}

/** L'unité de commande de la ligne (« kg », « Palette (862,4 kg) »…), jamais « ml ». */
export function ChoixUnite({ l, onChange }: { l: LigneSaisie; onChange: (unite: string) => void }) {
  return (
    <select
      className={styles.choix}
      aria-label={`Unité de commande de ${l.reference}`}
      value={l.unite}
      onChange={(e) => onChange(e.target.value)}
    >
      {l.unites.map((u) => (
        <option key={u.unite} value={u.unite}>
          {libelleUnite(u.unite, u.contenance)}
        </option>
      ))}
    </select>
  )
}

function Ecart({ l }: { l: LigneSaisie }) {
  const e = ecart(l)
  if (e.genre === 'non_commandee') return <span className={styles.note}>non commandée</span>
  if (e.genre === 'hors_calcul') return <Badge ton="neutre">hors calcul</Badge>
  if (e.genre === 'suggestion') return <span className={styles.note}>suggestion</span>
  if (e.genre === 'aucun') return <>{VIDE}</>
  return <Badge ton={e.ton}>{partSignee(e.valeur, 0)}</Badge>
}

function Kilos({ l, ed }: { l: LigneSaisie; ed: Edition }) {
  const alerte = avertissement(l)
  return (
    <span className={styles.cellule}>
      <Nombre
        valeur={arrondi(l.quantite, 1)}
        onChange={(v) => ed.modifier(l.matiere_id, { quantite: Math.max(0, v ?? 0) })}
        min={0}
        decimales={3}
        libelle={`Kilos de ${l.reference}`}
        className={styles.champCourt}
      />
      {l.kgParMl ? <span className={styles.note}>{metres(l.quantite, l.kgParMl)}</span> : null}
      {alerte ? <span className={styles.attention}>{alerte}</span> : null}
    </span>
  )
}

function Unites({ l, ed }: { l: LigneSaisie; ed: Edition }) {
  const n = l.quantite / (l.contenance || 1)
  return (
    <Nombre
      valeur={arrondi(n, 2)}
      onChange={(v) =>
        ed.modifier(l.matiere_id, { quantite: arrondi(Math.max(0, v ?? 0) * (l.contenance || 1), 3) })
      }
      min={0}
      decimales={2}
      libelle={`Quantité de ${l.reference} en ${l.unite}`}
      className={styles.champCourt}
    />
  )
}

function Suggere({ l }: { l: LigneSaisie }) {
  if (!l.suggestion) return <>{l.enPreparation ? deux(VIDE, l.enPreparation) : VIDE}</>
  const unites =
    l.suggestion_unite && l.suggestion_unite !== 'kg'
      ? quantiteEnUnite(l.suggestion_unites, l.suggestion_unite)
      : ''
  return (
    <>
      {nombre(l.suggestion)}
      {unites ? <span className={styles.dessous}>{unites}</span> : null}
      {l.enPreparation ? <span className={styles.dessous}>{l.enPreparation}</span> : null}
    </>
  )
}

function colonnes1(ed: Edition): Colonne<LigneSaisie>[] {
  return [
    {
      cle: 'retenue',
      titre: 'Cmd.',
      aide: 'Cocher pour commander la ligne',
      triable: false,
      rendu: (l) => (
        <input
          type="checkbox"
          checked={l.retenue}
          aria-label={`Commander ${l.reference}`}
          onChange={(e) => ed.modifier(l.matiere_id, { retenue: e.target.checked })}
        />
      ),
    },
    {
      cle: 'reference',
      titre: 'Référence',
      rendu: (l) => (
        <span className={l.retenue ? undefined : styles.eteinte}>
          {deux(
            <span className={styles.ref} title={l.reference}>
              {l.reference}
            </span>,
            [l.nature, l.designation, l.devise].filter(Boolean).join(' · '),
          )}
        </span>
      ),
    },
  ]
}

function colonnes2(_ed: Edition): Colonne<LigneSaisie>[] {
  return [
    {
      cle: 'statut',
      titre: 'Statut',
      rendu: (l) =>
        deux(
          l.statut ? (
            <Badge famille="stock" valeur={cleStock(l.statut)} />
          ) : (
            <Badge ton="neutre">ajoutée</Badge>
          ),
          [
            l.classe_abc ? `classe ${l.classe_abc}` : '',
            l.couverture_jours == null ? '' : `couvre ${jours(l.couverture_jours)}`,
          ]
            .filter(Boolean)
            .join(' · ') || null,
        ),
    },
    {
      cle: 'stock_projete',
      titre: 'Stock projeté (kg)',
      aide: 'Le stock projeté ; dessous, la consommation d’un mois (kg)',
      droite: true,
      rendu: (l) =>
        deux(
          l.stock_projete == null ? VIDE : nombre(l.stock_projete),
          l.conso_mensuelle == null ? null : `conso ${nombre(l.conso_mensuelle)} / mois`,
        ),
    },
    {
      cle: 'suggestion',
      titre: 'Suggéré (kg)',
      aide: 'La quantité que le calcul propose, et la même dans l’unité de commande',
      droite: true,
      rendu: (l) => <Suggere l={l} />,
    },
  ]
}

function colonnes3(ed: Edition): Colonne<LigneSaisie>[] {
  return [
    {
      cle: 'unites',
      titre: 'Quantité',
      aide: 'La quantité dans l’unité où l’on commande, et cette unité (changer d’unité garde les kilos)',
      droite: true,
      triable: false,
      rendu: (l) => (
        <span className={styles.cellule}>
          <Unites l={l} ed={ed} />
          <ChoixUnite l={l} onChange={(u) => ed.remplacer(l.matiere_id, changerUnite(l, u))} />
        </span>
      ),
    },
    {
      cle: 'quantite',
      titre: 'Soit (kg)',
      droite: true,
      unite: 'kg',
      total: true,
      valeur: (l) => (l.retenue ? l.quantite : 0),
      rendu: (l) => <Kilos l={l} ed={ed} />,
    },
    {
      cle: 'ecart',
      titre: 'Écart',
      aide: 'Ce que vous commandez face à la suggestion du calcul',
      droite: true,
      triable: false,
      rendu: (l) => <Ecart l={l} />,
    },
    {
      cle: 'montant',
      titre: 'Montant indicatif',
      aide: 'Au prix du catalogue, avant confirmation par le fournisseur',
      droite: true,
      unite: (l) => l.devise,
      total: true,
      valeur: (l) => (l.retenue && l.prix ? l.quantite * l.prix : 0),
      rendu: (l) =>
        l.prix ? deux(montant(l.quantite * l.prix, l.devise), prixUnite(l.prix, l.devise, 'kg')) : VIDE,
    },
  ]
}

function colonnes4(ed: Edition): Colonne<LigneSaisie>[] {
  return [
    {
      cle: 'retirer',
      titre: '',
      triable: false,
      rendu: (l) =>
        l.ajoutee ? (
          <Bouton taille="petit" variante="danger" onClick={() => ed.retirer(l.matiere_id)}>
            Retirer
          </Bouton>
        ) : null,
    },
  ]
}

function colonnes(ed: Edition): Colonne<LigneSaisie>[] {
  return [...colonnes1(ed), ...colonnes2(ed), ...colonnes3(ed), ...colonnes4(ed)]
}

export function TablePreparation({ lignes, ed }: { lignes: readonly LigneSaisie[]; ed: Edition }) {
  return (
    <div className={styles.tableFenetre}>
      <DataTable<LigneSaisie>
        libelle="Lignes de la préparation"
        lignes={lignes}
        colonnes={colonnes(ed)}
        cle={(l) => l.matiere_id}
        recherche={false}
        hauteur="fenetre"
        vide="Rien à commander chez ce fournisseur selon le calcul. Ajoutez ci-dessus les matières que vous voulez commander quand même."
      />
    </div>
  )
}
