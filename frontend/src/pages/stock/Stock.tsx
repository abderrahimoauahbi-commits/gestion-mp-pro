/**
 * « Stock, lots & mouvements » (`/stock?onglet=matieres|lots|mouvements|ordres|a-valider`) : le
 * stock par matière, lot par lot, chaque mouvement de stock, les ordres de fabrication, et ce qui
 * attend d'être validé. Les fiches s'ouvrent en fenêtre par-dessus la liste, à adresse stable :
 * `/stock/matieres/:id`, `/lots/:id`, `/tracabilite?lot=|ordre=|matiere=` (A5) ; fermer rend la
 * liste avec son onglet, sa recherche et ses filtres.
 *
 * Direction, achats, alimentation ; l'alimentation ne voit ni prix, ni montant, ni conseil d'achat
 * (le serveur les retire, l'écran n'en a pas les colonnes : H-03).
 */
import { useEffect } from 'react'
import { useLocation, useNavigate, useSearchParams } from 'react-router'

import { EnTete } from '../../composants/coque/EnTete'
import { Onglets } from '../../composants/mise-en-page/Onglets'
import { Page } from '../../composants/mise-en-page/Page'
import { useSession } from '../../lib/session'
import { useBrouillons } from './donnees'
import { FicheLot } from './FicheLot'
import { FicheMatiere } from './FicheMatiere'
import { ONGLETS_STOCK, ongletSous, ouvertDe, useNavigationStock, type OngletStock } from './navigation'
import { OngletAValider } from './OngletAValider'
import { OngletLots } from './OngletLots'
import { OngletMatieres } from './OngletMatieres'
import { OngletMouvements } from './OngletMouvements'
import { OngletOrdres } from './OngletOrdres'
import { Tracabilite } from './Tracabilite'

const LIBELLES: Record<OngletStock, string> = {
  matieres: 'Par matière',
  lots: 'Lots',
  mouvements: 'Mouvements de stock',
  ordres: 'Ordres de fabrication',
  'a-valider': 'À valider',
}

/** Les anciennes adresses de Gestion MP : `?volet=`, `?onglet=tracabilite`, `?article=`, `?lot_id=`. */
export function adresseAncienne(params: URLSearchParams): string | null {
  const lot = params.get('lot_id')
  if (lot) return `/tracabilite?lot=${lot}`
  if (params.get('article')) return `/stock?onglet=lots&matiere=${params.get('article')}`
  if (params.get('volet')) return `/stock?onglet=${params.get('volet')}`
  return params.get('onglet') === 'tracabilite' ? '/stock?onglet=ordres' : null
}

export default function Stock() {
  const { role } = useSession()
  const { pathname } = useLocation()
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const ouvert = ouvertDe(pathname, params)
  const onglet = ongletSous(ouvert, params)
  const nav = useNavigationStock(onglet)
  const brouillons = useBrouillons()
  const voitPrix = role !== 'alimentation'
  const ancienne = pathname === '/stock' ? adresseAncienne(params) : null
  useEffect(() => {
    if (ancienne) navigate(ancienne, { replace: true })
  }, [ancienne, navigate])
  const nbBrouillons = brouillons.data?.nombre
  return (
    <Page titre="Stock, lots & mouvements">
      <EnTete
        titre="Stock, lots & mouvements"
        sous="Par matière, lot par lot, chaque mouvement de stock, les ordres de fabrication, et ce qui attend d'être validé."
        aide="stock"
      />
      <Onglets<OngletStock>
        libelle="Onglets du stock"
        actif={onglet}
        onChange={nav.choisir}
        onglets={ONGLETS_STOCK.map((cle) => ({
          cle,
          libelle: LIBELLES[cle],
          compte: cle === 'a-valider' && nbBrouillons ? nbBrouillons : undefined,
        }))}
      />
      {onglet === 'matieres' ? <OngletMatieres voitPrix={voitPrix} onOuvrir={nav.ouvrirMatiere} /> : null}
      {onglet === 'lots' ? <OngletLots onOuvrir={nav.ouvrirLot} onSuivre={nav.suivre} /> : null}
      {onglet === 'mouvements' ? <OngletMouvements voitPrix={voitPrix} onOuvrirLot={nav.ouvrirLot} /> : null}
      {onglet === 'ordres' ? <OngletOrdres onSuivre={nav.suivre} /> : null}
      {onglet === 'a-valider' ? <OngletAValider /> : null}
      {ouvert?.genre === 'matiere' ? (
        <FicheMatiere
          key={ouvert.id}
          id={ouvert.id}
          voitPrix={voitPrix}
          onFermer={nav.fermer}
          onSuivre={nav.suivre}
        />
      ) : null}
      {ouvert?.genre === 'lot' ? (
        <FicheLot key={ouvert.id} id={ouvert.id} onFermer={nav.fermer} onSuivre={nav.suivre} />
      ) : null}
      {ouvert?.genre === 'suivi' ? <Tracabilite suivi={ouvert.suivi} /> : null}
    </Page>
  )
}
