/**
 * Fiche de lot (`/lots/:id`, fenêtre sur `/stock?onglet=lots`) : la fiche unique d'un lot (Partie 1
 * et Partie 2 d'ECRANS-PRO) — reste, disponible, entré et sorti (net des retours), kg par bobine,
 * entrée ; la réception d'où il vient ; ses soldes par magasin et les ordres servis ; la libération
 * de quarantaine (direction, achats) ; ses mouvements, le plus récent d'abord ; l'étiquette.
 */
import { useState } from 'react'
import { Link } from 'react-router'

import { BoutonImprimer } from '../../composants/documents/BoutonImprimer'
import { Historique } from '../../composants/documents/Historique'
import { LienDocument } from '../../composants/documents/LienDocument'
import { Fenetre, useFermerFenetre } from '../../composants/mise-en-page/Fenetre'
import { Indicateurs } from '../../composants/mise-en-page/Indicateurs'
import { Badge } from '../../composants/retour/Badge'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { Kpi } from '../../composants/retour/Kpi'
import { Bouton } from '../../composants/saisie/Bouton'
import { ErreurApi } from '../../lib/api'
import { formule } from '../../lib/aide'
import { date, kgEtMetres, nombre, VIDE } from '../../lib/format'
import { permis } from '../../lib/droits'
import { useSession } from '../../lib/session'
import { statut } from '../../lib/statuts'
import type { Suivi } from './donnees'
import { useLot } from './donnees'
import { Liberation } from './Liberation'
import { MouvementsDuLot } from './MouvementsDuLot'
import styles from './stock.module.css'
import { estQuarantaine, POUSSIERE, type LotFiche } from './types'

/** « Fermer », gardé par la saisie en cours (la question de la fenêtre). */
function BoutonFermer() {
  const fermer = useFermerFenetre()
  return <Bouton onClick={fermer}>Fermer</Bouton>
}

function IndicateursLot({ l }: { l: LotFiche }) {
  return (
    <Indicateurs libelle="Indicateurs du lot">
      <Kpi
        titre="Reste"
        valeur={kgEtMetres(l.quantite, l.kg_par_ml)}
        detail={l.bobines != null ? `${nombre(l.bobines)} bobines` : undefined}
        ton={l.quarantaine > POUSSIERE ? 'attention' : undefined}
        formule={formule('reste_lot')}
      />
      <Kpi
        titre="Disponible"
        valeur={kgEtMetres(l.disponible, l.kg_par_ml)}
        detail={statut('lot', l.statut).libelle}
        formule={formule('stock_detenu')}
      />
      <Kpi
        titre="Entré"
        valeur={kgEtMetres(l.historique.entre, l.kg_par_ml)}
        detail={
          l.historique.dernier_mouvement
            ? `dernier mouvement le ${date(l.historique.dernier_mouvement)}`
            : undefined
        }
        formule={formule('entre_sorti_lot')}
      />
      <Kpi
        titre="Sorti"
        valeur={kgEtMetres(l.historique.sorti, l.kg_par_ml)}
        detail="net des retours des machines"
        formule={formule('entre_sorti_lot')}
      />
      <Kpi
        titre="kg / bobine"
        valeur={l.poids_bobine ? nombre(l.poids_bobine, 2, 4) : VIDE}
        detail={l.bobines_palette ? `${nombre(l.bobines_palette)} bobines / palette` : undefined}
        formule={formule('poids_bobine')}
      />
      <Kpi
        titre="Entré le"
        valeur={date(l.entre_le)}
        detail={l.fournisseur}
        formule={formule('entree_lot')}
      />
    </Indicateurs>
  )
}

function Origine({ l }: { l: LotFiche }) {
  const { role } = useSession()
  const r = l.reception
  if (!r) return null
  const lien = permis(role, `/receptions/${r.id}`)
  return (
    <p className={styles.note}>
      Réception {lien ? <LienDocument genre="reception" id={r.id} numero={r.numero} /> : r.numero} du{' '}
      {date(r.date)}
      {r.bl ? ` · BL ${r.bl}` : ''}
      {r.facture ? ` · facture ${r.facture}` : ''} · pesé {kgEtMetres(r.pesee, l.kg_par_ml)}
    </p>
  )
}

function Soldes({ l, onSuivre }: { l: LotFiche; onSuivre: (s: Suivi) => void }) {
  return (
    <div className={styles.rangee}>
      {l.magasins.map((s) => (
        <span key={s.magasin_id}>
          {estQuarantaine(s.type) ? <Badge ton="critique">{s.magasin}</Badge> : <strong>{s.magasin}</strong>}{' '}
          {kgEtMetres(s.quantite, l.kg_par_ml)}
        </span>
      ))}
      {l.historique.ordres.length ? (
        <span className={styles.note}>
          Ordres servis :{' '}
          {l.historique.ordres.map((o, i) => (
            <span key={o.id}>
              {i ? ', ' : ''}
              <Link to={`/ordres/${o.id}`}>{o.numero}</Link>
            </span>
          ))}
        </span>
      ) : null}
      <span className={styles.pousse} />
      <Bouton
        titre="D’où vient ce lot, quels ordres de fabrication il a servis, et quand"
        onClick={() => onSuivre({ lot: l.lot_id })}
      >
        Où ce lot est-il allé ?
      </Bouton>
    </div>
  )
}

export function FicheLot({
  id,
  onFermer,
  onSuivre,
}: {
  id: number
  onFermer: () => void
  onSuivre: (s: Suivi) => void
}) {
  const { role } = useSession()
  const fiche = useLot(id)
  const [sale, setSale] = useState(false)
  const l = fiche.data
  const titre = l ? `${l.reference} — lot ${l.lot}` : 'Lot'
  const sous = l ? (
    <>
      {[l.reference, l.role, l.fournisseur].filter(Boolean).join(' · ')}{' '}
      <Badge famille="lot" valeur={l.statut} />
    </>
  ) : undefined
  const introuvable = fiche.error instanceof ErreurApi && fiche.error.statut === 404
  const pied = (
    <>
      <BoutonImprimer
        route="/documents/etiquettes"
        parametres={{ lots: String(id) }}
        libelle="Imprimer l’étiquette"
      />
      <span className={styles.pousse} />
      <BoutonFermer />
    </>
  )
  return (
    <Fenetre titre={titre} sous={sous} taille="tresLarge" onFermer={onFermer} pied={pied} sale={sale}>
      {fiche.isPending ? <Chargement quoi="le lot" /> : null}
      {introuvable ? <Erreur erreur="Lot introuvable." /> : null}
      {fiche.isError && !introuvable ? (
        <Erreur erreur={fiche.error} onReessayer={() => void fiche.refetch()} />
      ) : null}
      {l ? (
        <>
          <IndicateursLot l={l} />
          <Origine l={l} />
          <Soldes l={l} onSuivre={onSuivre} />
          {role !== 'alimentation' &&
          l.magasins.some((s) => estQuarantaine(s.type) && s.quantite > POUSSIERE) ? (
            <Liberation l={l} onSale={setSale} />
          ) : null}
          <MouvementsDuLot l={l} />
          {role !== 'alimentation' ? <Historique objet="lot" id={l.lot_id} /> : null}
        </>
      ) : null}
    </Fenetre>
  )
}
