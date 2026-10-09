/**
 * Cockpit › Évolution (`/cockpit?onglet=evolution&vue=…`) : une photo des indicateurs par jour
 * (prise par le serveur, route 231), en quatre vues — valeur et achats, alertes, couverture, OTIF —
 * et la liste des photos, la plus récente d'abord. « Photographier aujourd'hui » prend celle du
 * jour tout de suite (route 232, direction).
 */
import { Bascule, useVueAdresse } from '../../composants/mise-en-page/Bascule'
import { Carte } from '../../composants/mise-en-page/Carte'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { dire } from '../../composants/retour/Messages'
import { Note } from '../../composants/retour/Note'
import { Bouton } from '../../composants/saisie/Bouton'
import { Courbes } from '../../composants/graphiques/Courbes'
import type { Serie } from '../../composants/graphiques/echelle'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { api } from '../../lib/api'
import { date, jours, montant, nombre, part } from '../../lib/format'
import { useEcriture, useLecture } from '../../lib/requetes'
import { useSession } from '../../lib/session'
import type { Schema } from '../../lib/types'
import styles from './cockpit.module.css'

type Photo = Schema<'IndicateurJour'>
type Vue = 'argent' | 'alertes' | 'couverture' | 'otif'
const VUES: readonly { cle: Vue; libelle: string }[] = [
  { cle: 'argent', libelle: 'Valeur et achats' },
  { cle: 'alertes', libelle: 'Alertes' },
  { cle: 'couverture', libelle: 'Couverture' },
  { cle: 'otif', libelle: 'OTIF' },
]

/** Les séries d'une vue ; une unité par série (jamais deux unités sur un axe). */
export function series(vue: Vue, photos: readonly Photo[]): Serie[] {
  const de = (f: (p: Photo) => number | null) => photos.map(f)
  if (vue === 'argent')
    return [
      { nom: 'Valeur du stock', valeurs: de((p) => p.valeur_stock_mad), unite: 'MAD' },
      { nom: 'À commander', valeurs: de((p) => p.a_commander_mad), unite: 'MAD' },
      { nom: 'Commandé, à livrer', valeurs: de((p) => p.commandes_en_cours_mad), unite: 'MAD' },
    ]
  if (vue === 'alertes')
    return [
      { nom: 'RUPTURE', valeurs: de((p) => p.ruptures), unite: 'matières' },
      { nom: 'CRITIQUE', valeurs: de((p) => p.critiques), unite: 'matières' },
      { nom: 'URGENT', valeurs: de((p) => p.urgents), unite: 'matières' },
    ]
  if (vue === 'couverture')
    return [{ nom: 'Couverture pondérée', valeurs: de((p) => p.couverture_jours), unite: 'j' }]
  return [
    { nom: 'OTIF moyen', valeurs: de((p) => (p.otif_moyen == null ? null : p.otif_moyen * 100)), unite: '%' },
  ]
}

const COLONNES: Colonne<Photo>[] = [
  { cle: 'jour', titre: 'Jour', rendu: (p) => date(p.jour) },
  {
    cle: 'valeur_stock_mad',
    titre: 'Valeur',
    aide: 'Valeur du stock (magasins et sur les métiers, au coût moyen)',
    droite: true,
    unite: 'MAD',
    rendu: (p) => montant(p.valeur_stock_mad, 'MAD'),
  },
  {
    cle: 'couverture_jours',
    titre: 'Couv.',
    aide: 'Couverture pondérée par la valeur',
    droite: true,
    rendu: (p) => jours(p.couverture_jours),
  },
  {
    cle: 'alertes',
    titre: 'R · C · U',
    aide: 'Matières en RUPTURE, CRITIQUE, URGENT ce jour-là',
    droite: true,
    valeur: (p) => `${p.ruptures} · ${p.critiques} · ${p.urgents}`,
    triable: false,
  },
  {
    cle: 'a_commander_mad',
    titre: 'À cmd.',
    aide: 'À commander selon le plan d’achat',
    droite: true,
    unite: 'MAD',
    rendu: (p) => montant(p.a_commander_mad, 'MAD'),
  },
  { cle: 'otif_moyen', titre: 'OTIF', droite: true, rendu: (p) => part(p.otif_moyen, 0) },
]

/** La courbe de la vue, ou ce qui manque pour la dessiner (moins de deux photos). */
function Graphique({ photos, vue, direction }: { photos: readonly Photo[]; vue: Vue; direction: boolean }) {
  const format = vue === 'argent' ? (v: number) => `${nombre(v / 1e6, 2)} M` : (v: number) => nombre(v, 0, 1)
  return (
    <>
      {photos.length < 2 ? (
        <Note>
          L’évolution repose sur <strong>une photo par jour</strong> des indicateurs, prise par le serveur
          depuis sa mise en service.{' '}
          {photos.length
            ? 'Une seule photo pour l’instant : la courbe se dessinera dès la photo de demain.'
            : 'Aucune photo encore.'}{' '}
          {direction ? '« Photographier aujourd’hui » prend celle du jour tout de suite.' : ''}
        </Note>
      ) : null}
      {photos.length ? (
        <Courbes
          etiquettes={photos.map((p) => date(p.jour).slice(0, 5))}
          series={series(vue, photos)}
          libelle={`Évolution : ${VUES.find((v) => v.cle === vue)?.libelle ?? ''}`}
          format={format}
        />
      ) : null}
    </>
  )
}

export function OngletEvolution() {
  const { role } = useSession()
  const lues = useLecture<Photo[]>('/indicateurs/historique')
  const [vue, choisir] = useVueAdresse<Vue>(
    VUES.map((v) => v.cle),
    'argent',
  )
  const photographier = useEcriture(() => api.post('/indicateurs/photographier'))
  const direction = role === 'direction'
  const prendre = async () => {
    await photographier.mutateAsync()
    dire('La photo d’aujourd’hui est prise.')
  }
  if (lues.isPending) return <Chargement quoi="l’historique des indicateurs" />
  if (lues.isError) return <Erreur erreur={lues.error} onReessayer={() => void lues.refetch()} />
  const photos = lues.data
  return (
    <div className={`${styles.deux} ${styles.etroit}`}>
      <Carte
        titre="Les indicateurs jour après jour"
        actions={
          direction ? (
            <Bouton
              titre="Prendre tout de suite la photo du jour (le serveur la prend aussi seul, chaque jour)"
              attente="Photo…"
              onClick={prendre}
            >
              Photographier aujourd’hui
            </Bouton>
          ) : null
        }
      >
        <div className={styles.aGauche}>
          <Bascule<Vue> vues={VUES} valeur={vue} onChange={choisir} libelle="Vue de l’évolution" />
        </div>
        <Graphique photos={photos} vue={vue} direction={direction} />
      </Carte>
      <Carte titre={`Les photos, la plus récente d’abord (${nombre(photos.length)})`} serre>
        <DataTable
          lignes={[...photos].reverse()}
          colonnes={COLONNES}
          cle={(p) => p.jour}
          recherche={false}
          libelle="Les photos des indicateurs"
          vide="Aucune photo."
          exporter={{ fichier: 'photos-des-indicateurs' }}
        />
      </Carte>
    </div>
  )
}
