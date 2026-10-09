/**
 * La fiche fournisseur en fenêtre (`/fournisseurs/:id`, `/fournisseurs/nouveau` ; direction,
 * achats), onglets `?onglet=fiche|pieces|historique`. Indicateurs (matières, délai et son écart
 * mesuré, OTIF, score — rapprochés par identifiant), liens vers ses matières et l'analyse ;
 * gestes : créer, enregistrer, recharger (R2), désactiver, réactiver, supprimer (grisé avec tout
 * ce qui l'empêche : matières, commandes, réceptions, lots, opérations, factures, pièces).
 */
import { Link } from 'react-router'

import { Historique } from '../../composants/documents/Historique'
import { PiecesJointes } from '../../composants/documents/PiecesJointes'
import { Fenetre } from '../../composants/mise-en-page/Fenetre'
import { Onglets } from '../../composants/mise-en-page/Onglets'
import { Badge } from '../../composants/retour/Badge'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { useOngletAdresse } from '../../lib/adresse'
import { nombre } from '../../lib/format'
import styles from './catalogue.module.css'
import { BlocApprovisionnement, BlocIdentite, BlocPaiement } from './ChampsFournisseur'
import { BandeauConflit } from './Conflit'
import { useDevises, useFournisseur, useFournisseurs } from './donnees'
import { IndicateursFournisseur } from './IndicateursFournisseur'
import { PiedFournisseur } from './PiedFournisseur'
import { estComplet, type Fournisseur } from './types'
import { useFicheFournisseur } from './useFicheFournisseur'

type Volet = 'fiche' | 'pieces' | 'historique'

function Liens({ f }: { f: Fournisseur }) {
  return (
    <div className={styles.rangee}>
      <span className={styles.note}>
        {nombre(f.nb_commandes)} commande(s) · {nombre(f.nb_receptions)} réception(s)
      </span>
      <span className={styles.pousse} />
      {f.nb_matieres ? (
        <Link className={styles.lien} to={`/catalogue?fournisseur=${f.id}`}>
          Voir ses matières
        </Link>
      ) : null}
      <Link className={styles.lien} to={`/analyse?onglet=fournisseurs&fournisseur=${f.id}`}>
        Voir l’analyse des fournisseurs
      </Link>
    </div>
  )
}

function Titre({ b }: { b: Fournisseur | null }) {
  if (!b) return <>Nouveau fournisseur</>
  return (
    <>
      {b.nom} {b.actif ? null : <Badge ton="neutre">désactivé</Badge>}
    </>
  )
}

function Pieces({ id }: { id: number }) {
  return (
    <>
      <p className={styles.note}>
        Contrat, coordonnées bancaires (RIB), certificats, catalogue du fournisseur : rangés avec sa fiche.
      </p>
      <PiecesJointes objet="fournisseur" id={id} />
    </>
  )
}

function Ecrite({
  fiche,
  pays,
  onFermer,
  onCree,
}: {
  fiche: Fournisseur | null
  pays: readonly string[]
  onFermer: () => void
  onCree: (id: number) => void
}) {
  const devises = useDevises(true)
  const f = useFicheFournisseur({ fiche, onCree, onSupprime: onFermer })
  const volets: Volet[] = f.base ? ['fiche', 'pieces', 'historique'] : ['fiche']
  const [volet, choisir] = useOngletAdresse(volets, 'fiche')
  const b = f.base
  const champs = { forme: f.forme, maj: f.maj, pays, devises: devises.data ?? [] }
  return (
    <Fenetre
      titre={<Titre b={b} />}
      onFermer={onFermer}
      sale={f.sale}
      taille="large"
      pied={<PiedFournisseur f={f} />}
    >
      {b ? <IndicateursFournisseur f={b} /> : null}
      {b ? <Liens f={b} /> : null}
      <BandeauConflit message={f.conflit} onRecharger={f.recharger} />
      {b ? (
        <Onglets<Volet>
          libelle="Volets de la fiche"
          actif={volet}
          onChange={choisir}
          onglets={[
            { cle: 'fiche', libelle: 'Fiche', sale: f.sale },
            { cle: 'pieces', libelle: 'Pièces jointes', compte: b.nb_pieces },
            { cle: 'historique', libelle: 'Historique' },
          ]}
        />
      ) : null}
      {volet === 'fiche' ? (
        <div className={styles.volet}>
          <strong>Identité et contact</strong>
          <BlocIdentite {...champs} />
          <strong>Approvisionnement</strong>
          <BlocApprovisionnement {...champs} />
          <strong>Paiement</strong>
          <BlocPaiement {...champs} />
        </div>
      ) : null}
      {volet === 'pieces' && b ? <Pieces id={b.id} /> : null}
      {volet === 'historique' && b ? <Historique objet="fournisseur" id={b.id} /> : null}
    </Fenetre>
  )
}

export function FicheFournisseur({
  id,
  onFermer,
  onCree,
}: {
  id: number | null
  onFermer: () => void
  onCree: (id: number) => void
}) {
  const fiche = useFournisseur(id)
  const tous = useFournisseurs()
  const pays = [...new Set((tous.data ?? []).map((f) => f.pays).filter(Boolean))].sort()
  if (fiche.isError)
    return (
      <Fenetre titre="Fiche fournisseur" onFermer={onFermer}>
        <Erreur erreur={fiche.error} onReessayer={() => void fiche.refetch()} />
      </Fenetre>
    )
  if (id != null && !fiche.data)
    return (
      <Fenetre titre="Fiche fournisseur" onFermer={onFermer}>
        <Chargement quoi="la fiche" />
      </Fenetre>
    )
  const lue = fiche.data && estComplet(fiche.data) ? fiche.data : null
  return <Ecrite fiche={lue} pays={pays} onFermer={onFermer} onCree={onCree} />
}
