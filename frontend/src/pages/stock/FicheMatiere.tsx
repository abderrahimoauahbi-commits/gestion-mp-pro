/**
 * Fiche matière (`/stock/matieres/:id`, fenêtre sur `/stock`) : ses indicateurs, ses trois cartes
 * (approvisionnement, classement et risque, où se trouve la matière), puis ses besoins du plan mois
 * par mois et d'où ils viennent, ses lots, ce qui est monté sur les métiers. Les chiffres des
 * indicateurs et de la carte « Où se trouve la matière » sont lus une seule fois (`addition.ts`).
 */
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router'

import { Historique } from '../../composants/documents/Historique'
import { Bascule } from '../../composants/mise-en-page/Bascule'
import { Fenetre } from '../../composants/mise-en-page/Fenetre'
import { Indicateurs } from '../../composants/mise-en-page/Indicateurs'
import { Badge } from '../../composants/retour/Badge'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { Kpi, type KpiProps } from '../../composants/retour/Kpi'
import { Note } from '../../composants/retour/Note'
import { Bouton } from '../../composants/saisie/Bouton'
import { formule } from '../../lib/aide'
import { jours, metres, nombre, VIDE } from '../../lib/format'
import { cleStock, statut } from '../../lib/statuts'
import { affichageMatiere, type AffichageMatiere } from './addition'
import { CarteAppro, CarteClassement, CarteOu } from './CartesMatiere'
import { aCommander } from './colonnesMatieres'
import { useFicheStock, useMagasins, useMatieres } from './donnees'
import type { Suivi } from './donnees'
import { BesoinsDuPlan, LotsDeLaMatiere, SurLesMetiers } from './VuesMatiere'
import styles from './stock.module.css'
import type { FicheStockMatiere, LigneStock } from './types'

type VueFiche = 'besoins' | 'lots' | 'metiers' | 'historique'

const kgTexte = (v: number) => `${nombre(v, 1)}`

function aCommanderDetail(l: LigneStock): string {
  const q = l.quantite_a_commander ?? 0
  if (l.kg_par_ml && q > 0.0005) return `kg · ${metres(q, l.kg_par_ml)}, à titre indicatif`
  if (l.unite_commande && l.unite_commande !== 'kg' && l.unites_a_commander)
    return `kg · ${nombre(l.unites_a_commander, 1)} ${l.unite_commande} de ${nombre(l.contenance_commande)} kg`
  return `kg · ${nombre(l.palettes_a_commander, 1)} palette(s)`
}

/** Les indicateurs de la fiche : les mêmes chiffres que la carte « Où se trouve la matière ». */
export function kpisMatiere(l: LigneStock, a: AffichageMatiere): KpiProps[] {
  const ton = statut('stock', cleStock(l.statut)).ton
  const sansConso = l.couverture_jours == null
  return [
    {
      titre: 'Stock',
      valeur: kgTexte(a.stock),
      unite: 'kg',
      detail: `magasins et sur les métiers${l.kg_par_ml ? ` · ${metres(a.stock, l.kg_par_ml)}` : ''}`,
      formule: formule('stock_detenu'),
    },
    {
      titre: 'Sur les métiers',
      valeur: kgTexte(a.metiers),
      unite: 'kg',
      detail: 'monté, pas encore tissé',
      formule: formule('sur_les_metiers'),
    },
    {
      titre: 'Disponible',
      valeur: kgTexte(a.disponible),
      unite: 'kg',
      detail: 'stock hors quarantaine (magasins et métiers)',
      formule: formule('stock_detenu'),
    },
    {
      titre: 'Demande pendant le délai',
      valeur: kgTexte(a.demande),
      unite: 'kg',
      detail: `${jours(l.delai_jours)} de délai ; puis ${nombre(l.sorties_prevues, 1)} sur la période que couvre une commande`,
      formule: formule('demande_delai'),
    },
    {
      titre: 'Stock projeté',
      valeur: kgTexte(a.projete),
      unite: 'kg',
      ton,
      detail: 'à la livraison d’une commande passée aujourd’hui',
      formule: formule('stock_projete'),
    },
    {
      titre: 'Couverture',
      valeur: sansConso ? VIDE : jours(l.couverture_jours),
      detail: sansConso
        ? 'sans consommation prévue'
        : `après le délai ; seuil d’alerte : ${jours(l.couverture_cible_jours)}`,
      ton: sansConso ? undefined : ton,
      formule: formule('couverture'),
    },
  ]
}

function IndicateursMatiere({ l, a, voitPrix }: { l: LigneStock; a: AffichageMatiere; voitPrix: boolean }) {
  return (
    <Indicateurs libelle="Indicateurs de la matière">
      {kpisMatiere(l, a).map((k) => (
        <Kpi key={k.titre} {...k} />
      ))}
      {voitPrix && l.quantite_a_commander != null ? (
        <Kpi
          titre="À commander"
          valeur={nombre(l.quantite_a_commander, 1)}
          detail={aCommanderDetail(l)}
          ton={aCommander(l) ? 'attention' : undefined}
          formule={formule('quantite_a_commander')}
        />
      ) : null}
    </Indicateurs>
  )
}

function Gestes({
  l,
  voitPrix,
  fournisseur,
  onSuivre,
}: {
  l: LigneStock
  voitPrix: boolean
  fournisseur: number | null
  onSuivre: (s: Suivi) => void
}) {
  const navigate = useNavigate()
  const id = l.matiere_id ?? 0
  return (
    <div className={styles.rangee}>
      <Bouton
        variante={(l.stock_net ?? 0) > 0.0005 ? 'principal' : 'neutre'}
        titre="Les lots de cette matière, et ce qui leur reste (cocher « épuisés » pour l’historique)"
        onClick={() => navigate(`/stock?onglet=lots&matiere=${id}`)}
      >
        Voir les lots →
      </Bouton>
      <Bouton
        titre="Tous les mouvements de cette matière, lot par lot : où elle est allée, et quand"
        onClick={() => onSuivre({ matiere: id })}
      >
        Où cette matière est-elle allée ?
      </Bouton>
      <Bouton
        titre="Les mouvements de stock de cette matière"
        onClick={() => navigate(`/stock?onglet=mouvements&q=${encodeURIComponent(l.reference ?? '')}`)}
      >
        Ses mouvements
      </Bouton>
      <span className={styles.pousse} />
      {voitPrix && aCommander(l) && fournisseur ? (
        <Bouton
          variante="principal"
          titre="Ce que le calcul propose de commander chez ce fournisseur"
          onClick={() => navigate(`/plan-achat/preparer/${fournisseur}`)}
        >
          Préparer la commande
        </Bouton>
      ) : null}
    </div>
  )
}

function Bas({
  fiche,
  voitPrix,
}: {
  fiche: NonNullable<ReturnType<typeof useFicheStock>['data']>
  voitPrix: boolean
}) {
  const [vue, setVue] = useState<VueFiche>('besoins')
  const vues = [
    { cle: 'besoins' as const, libelle: 'Besoins du plan, mois par mois' },
    { cle: 'lots' as const, libelle: `Lots (${fiche.lots.length})` },
    { cle: 'metiers' as const, libelle: `Sur les métiers (${fiche.sur_les_metiers.length})` },
    ...(voitPrix ? [{ cle: 'historique' as const, libelle: 'Historique' }] : []),
  ]
  return (
    <>
      <Bascule vues={vues} valeur={vue} onChange={setVue} libelle="Détail de la matière" />
      {vue === 'besoins' ? <BesoinsDuPlan l={fiche.ligne} qualites={fiche.besoins_par_qualite} /> : null}
      {vue === 'lots' ? <LotsDeLaMatiere lots={fiche.lots} /> : null}
      {vue === 'metiers' ? <SurLesMetiers fils={fiche.sur_les_metiers} /> : null}
      {vue === 'historique' && fiche.ligne.matiere_id ? (
        <Historique objet="matiere" id={fiche.ligne.matiere_id} />
      ) : null}
    </>
  )
}

function Contenu({
  fiche,
  a,
  voitPrix,
  fournisseur,
  onSuivre,
}: {
  fiche: FicheStockMatiere
  a: AffichageMatiere
  voitPrix: boolean
  fournisseur: number | null
  onSuivre: (s: Suivi) => void
}) {
  const l = fiche.ligne
  return (
    <>
      <div className={styles.rangee}>
        <Badge famille="stock" valeur={cleStock(l.statut)} />
      </div>
      <Gestes l={l} voitPrix={voitPrix} fournisseur={fournisseur} onSuivre={onSuivre} />
      <IndicateursMatiere l={l} a={a} voitPrix={voitPrix} />
      <div className={styles.grille3}>
        <CarteAppro l={l} voitPrix={voitPrix} />
        <CarteClassement l={l} voitPrix={voitPrix} />
        <CarteOu l={l} a={a} />
      </div>
      {voitPrix && l.sans_achat ? (
        <Note>Rien ne se rachète pour cette matière ({l.sans_achat}), même sous son stock minimum.</Note>
      ) : null}
      {l.substituts?.length ? (
        <Note>Substituts disponibles dans le même groupe : {l.substituts.join(' · ')}</Note>
      ) : null}
      <Bas fiche={fiche} voitPrix={voitPrix} />
    </>
  )
}

/** « rôle · désignation · composition · type de fil · couleur · titrage » */
function sousTitre(l: LigneStock, role: string | undefined): string {
  const titrage = l.titrage ? `${l.titrage}${l.titrage_unite ? ` ${l.titrage_unite}` : ''}` : ''
  return [
    role,
    l.designation !== l.reference ? l.designation : '',
    l.composition,
    l.type_fil,
    l.couleur,
    titrage,
  ]
    .filter(Boolean)
    .join(' · ')
}

export function FicheMatiere({
  id,
  voitPrix,
  onFermer,
  onSuivre,
}: {
  id: number
  voitPrix: boolean
  onFermer: () => void
  onSuivre: (s: Suivi) => void
}) {
  const fiche = useFicheStock(id)
  const magasins = useMagasins()
  const matieres = useMatieres()
  const types = useMemo(() => new Map((magasins.data ?? []).map((g) => [g.code, g.type])), [magasins.data])
  const l = fiche.data?.ligne
  const a = useMemo(() => (l ? affichageMatiere(l, types) : null), [l, types])
  const catalogue = matieres.data?.find((m) => m.id === id)
  return (
    <Fenetre
      titre={l?.reference ?? 'Fiche matière'}
      sous={l ? sousTitre(l, catalogue?.role) : undefined}
      taille="tresLarge"
      onFermer={onFermer}
    >
      {fiche.isPending ? <Chargement quoi="la fiche de la matière" /> : null}
      {fiche.isError ? <Erreur erreur={fiche.error} onReessayer={() => void fiche.refetch()} /> : null}
      {fiche.data && a ? (
        <Contenu
          fiche={fiche.data}
          a={a}
          voitPrix={voitPrix}
          fournisseur={l?.fournisseur_id ?? null}
          onSuivre={onSuivre}
        />
      ) : null}
    </Fenetre>
  )
}
