/**
 * Les trois cartes de la fiche matière : l'approvisionnement, le classement et le risque, et où se
 * trouve la matière — cette dernière écrite comme une addition qui tombe juste (`addition.ts`) :
 * magasins + sur les métiers = Disponible ; Disponible + Commandé − Demande pendant le délai =
 * Stock projeté ; Disponible + quarantaine = Stock.
 */
import type { ReactNode } from 'react'

import { LienDocument } from '../../composants/documents/LienDocument'
import { Carte } from '../../composants/mise-en-page/Carte'
import { Badge } from '../../composants/retour/Badge'
import { SUR_LES_METIERS } from '../../lib/aide'
import { date, jours, montant, nombre, part, prixUnite, VIDE } from '../../lib/format'
import type { AffichageMatiere } from './addition'
import styles from './stock.module.css'
import type { LigneStock } from './types'

function Paire({
  libelle,
  children,
  note,
  total,
}: {
  libelle: ReactNode
  children: ReactNode
  note?: ReactNode
  total?: boolean
}) {
  return (
    <tr className={total ? styles.total : undefined}>
      <td>
        {libelle}
        {note ? <span className={styles.dessous}>{note}</span> : null}
      </td>
      <td className={styles.valeurPaire}>{children}</td>
    </tr>
  )
}

const kgFixe = (v: number) => nombre(v, 0, 2)
const n = (v: number | null | undefined) => v ?? 0

/**
 * Les bons pas encore partis qui portent déjà la matière : « BC-2026-0012 » (à approuver), ou un
 * brouillon (`BC-brouillon-{id}` du moteur), dit « Brouillon » et ouvert par son identifiant.
 */
function BonsEnPreparation({ bons }: { bons: readonly string[] }) {
  return (
    <>
      {bons.map((b, i) => {
        const brouillon = /^BC-brouillon-(\d+)$/.exec(b)
        return (
          <span key={b}>
            {i ? ', ' : ''}
            {brouillon ? <LienDocument genre="commande" id={Number(brouillon[1])} numero={null} /> : b}
          </span>
        )
      })}
    </>
  )
}

/** La consommation retenue : le plan, le réel, et le coefficient qui les relie (ou celui hérité). */
function noteRealisation(l: LigneStock): string | undefined {
  if (l.coefficient_realisation == null) return undefined
  const k = nombre(l.coefficient_realisation, 2)
  if (l.realisation_heritee?.length)
    return `plan ${nombre(l.conso_plan, 0, 2)} · corrigé × ${k}, le taux de réalisation de ${l.realisation_heritee.join(', ')} qu’il remplace`
  return `plan ${nombre(l.conso_plan, 0, 2)} · réel ${l.conso_reelle != null ? nombre(l.conso_reelle, 0, 2) : VIDE} · plan corrigé × ${k}`
}

/** Prix, déjà en préparation, montant à commander : direction et achats. */
function PairesAchats({ l }: { l: LigneStock }) {
  const devise = l.devise ?? 'MAD'
  return (
    <>
      {n(l.bc_en_preparation) > 0.0005 ? (
        <Paire
          libelle="Déjà en préparation"
          note={
            <>
              <BonsEnPreparation bons={l.bons_en_preparation ?? []} /> : déduit de la quantité à commander,
              pas encore attendu
            </>
          }
        >
          {nombre(l.bc_en_preparation, 0, 2)}
        </Paire>
      ) : null}
      <Paire
        libelle="Montant à commander"
        note={
          l.montant_a_commander && devise !== 'MAD' ? montant(l.montant_a_commander_mad, 'MAD') : undefined
        }
      >
        {l.montant_a_commander ? montant(l.montant_a_commander, devise) : VIDE}
      </Paire>
    </>
  )
}

function PaireStockMinimum({ l }: { l: LigneStock }) {
  const plafonne = n(l.stock_min_plafonne) < n(l.stock_min) - 0.5
  return (
    <Paire
      libelle="Stock minimum (catalogue)"
      note={
        plafonne
          ? `retenu : ${nombre(l.stock_min_plafonne, 0, 2)} — ramené à ce que la consommation justifie`
          : undefined
      }
    >
      {nombre(l.stock_min, 0, 2)}
    </Paire>
  )
}

export function CarteAppro({ l, voitPrix }: { l: LigneStock; voitPrix: boolean }) {
  const devise = l.devise ?? ''
  const auMetre = l.unite_achat === 'ml' && l.prix_unite
  return (
    <Carte titre="Approvisionnement">
      <table className={styles.paires}>
        <tbody>
          <Paire libelle="Fournisseur">{l.fournisseur || VIDE}</Paire>
          <Paire libelle="Délai">{jours(l.delai_jours)}</Paire>
          {voitPrix ? (
            <Paire
              libelle="Prix"
              note={auMetre ? `au catalogue : ${prixUnite(l.prix_unite, devise, 'ml')}` : undefined}
            >
              {prixUnite(l.prix_kg, devise, 'kg')}
            </Paire>
          ) : null}
          <PaireStockMinimum l={l} />
          <Paire
            libelle="Seuil d’alerte"
            note={`sécurité et stock minimum, soit ${jours(l.couverture_cible_jours)} de consommation — comparé au stock projeté`}
          >
            {nombre(l.stock_min_recalcule, 0, 2)}
          </Paire>
          <Paire libelle="Consommation retenue / mois" note={noteRealisation(l)}>
            {nombre(l.conso_mensuelle, 0, 2)}
          </Paire>
          <Paire
            libelle="Besoin annuel retenu"
            note={
              l.coefficient_realisation != null
                ? `le plan corrigé par le réel (× ${nombre(l.coefficient_realisation, 2)})`
                : undefined
            }
          >
            {nombre(l.besoin_annuel, 0, 2)}
          </Paire>
          {voitPrix ? <PairesAchats l={l} /> : null}
        </tbody>
      </table>
    </Carte>
  )
}

export function CarteClassement({ l, voitPrix }: { l: LigneStock; voitPrix: boolean }) {
  return (
    <Carte titre="Classement et risque">
      <table className={styles.paires}>
        <tbody>
          {voitPrix ? (
            <Paire
              libelle="Classe ABC"
              note={l.rang ? `rang ${l.rang}, ${part(l.pourcentage_cumule)} cumulés` : undefined}
            >
              <strong>{l.classe_abc || VIDE}</strong>
            </Paire>
          ) : null}
          {voitPrix ? (
            <Paire libelle="Valeur consommée / an">{montant(l.valeur_conso_annuelle_mad, 'MAD')}</Paire>
          ) : null}
          <Paire libelle="Classe XYZ" note={`coefficient de variation ${nombre(l.cv_demande, 2)}`}>
            <strong>{l.classe_xyz || VIDE}</strong>
          </Paire>
          <Paire
            libelle="Sourcing"
            note={
              l.nb_fournisseurs_groupe
                ? `${l.nb_fournisseurs_groupe} fournisseur(s) dans le groupe`
                : undefined
            }
          >
            {l.sourcing || VIDE}
          </Paire>
          <Paire libelle="Groupe d’équivalence">{l.groupe_equiv || VIDE}</Paire>
          <Paire libelle="Dernière sortie">{date(l.date_derniere_sortie)}</Paire>
          <Paire libelle="Sans mouvement depuis">
            {l.jours_sans_mouvement == null ? VIDE : jours(l.jours_sans_mouvement)}
          </Paire>
          <Paire libelle="Dormant">{l.dormant ? <Badge ton="neutre">oui</Badge> : 'non'}</Paire>
        </tbody>
      </table>
    </Carte>
  )
}

/** Magasins courants + sur les métiers = Disponible. */
function Disponible({ a }: { a: AffichageMatiere }) {
  return (
    <>
      {a.magasins
        .filter((m) => !m.quarantaine)
        .map((m, i) => (
          <Paire key={m.code} libelle={`${i ? '+ ' : ''}${m.code}`}>
            {kgFixe(m.kg)}
          </Paire>
        ))}
      <Paire libelle="+ Sur les métiers" note={SUR_LES_METIERS}>
        {kgFixe(a.metiers)}
      </Paire>
      <Paire
        libelle={<strong>= Disponible</strong>}
        note="le stock hors quarantaine : magasins et sur les métiers"
        total
      >
        {kgFixe(a.disponible)}
      </Paire>
    </>
  )
}

/** Disponible + quarantaine = Stock (détenu). */
function Detenu({ a }: { a: AffichageMatiere }) {
  const bloques = a.magasins.filter((m) => m.quarantaine)
  if (!bloques.length) return null
  return (
    <>
      <Paire libelle="Disponible">{kgFixe(a.disponible)}</Paire>
      {bloques.map((m) => (
        <Paire
          key={m.code}
          libelle={
            <>
              + <Badge ton="critique">{m.code}</Badge>
            </>
          }
          note="quarantaine : détenue, pas disponible"
        >
          {kgFixe(m.kg)}
        </Paire>
      ))}
      <Paire
        libelle={<strong>= Stock</strong>}
        note="magasins (quarantaine comprise) et sur les métiers"
        total
      >
        {kgFixe(a.stock)}
      </Paire>
    </>
  )
}

/** Disponible + Commandé (dans le délai) − Demande pendant le délai = Stock projeté. */
function Projete({ l, a }: { l: LigneStock; a: AffichageMatiere }) {
  return (
    <>
      <Paire libelle="Disponible">{kgFixe(a.disponible)}</Paire>
      <Paire libelle="+ Commandé, attendu dans le délai">{kgFixe(a.commande)}</Paire>
      <Paire
        libelle="− Demande pendant le délai"
        note={`ce que le plan consommera en ${jours(l.delai_jours)}`}
      >
        {kgFixe(a.demande)}
      </Paire>
      <Paire
        libelle={<strong>= Stock projeté à la livraison</strong>}
        note="disponible + commandé − demande pendant le délai"
        total
      >
        {kgFixe(a.projete)}
      </Paire>
      <Paire libelle="Commandé, attendu au-delà" note="ne compte pas dans le projeté">
        {kgFixe(a.auDela)}
      </Paire>
    </>
  )
}

export function CarteOu({ l, a }: { l: LigneStock; a: AffichageMatiere }) {
  return (
    <Carte
      titre="Où se trouve la matière"
      sous="En kilos ; chaque total est la somme exacte des lignes au-dessus."
    >
      <table className={styles.paires} aria-label="Où se trouve la matière">
        <tbody>
          <Disponible a={a} />
          <Detenu a={a} />
          <Projete l={l} a={a} />
        </tbody>
      </table>
    </Carte>
  )
}
