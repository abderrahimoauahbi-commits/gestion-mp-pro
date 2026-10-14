/**
 * L'accueil de l'atelier (`/atelier`) : ce que l'atelier a sorti aujourd'hui (net des retours,
 * an. 22), sept tuiles dans l'ordre du travail de l'homme de l'atelier (Mohamed, 14/10/2026) :
 * envoyer, retour, transfert, montage, stock des fils, puis ordres et signaler (« Envoyer aux
 * machines » sur toute la largeur, les six autres par deux, aux
 * détails courts : elles tiennent toutes à 360 × 640), une astuce, « Se déconnecter » loin des tuiles et confirmé. Les compteurs
 * des signalements sont ceux du compte connecté (filtrés au serveur par identifiant, an. 25).
 */
import { EcranAtelier } from '../../composants/atelier/EcranAtelier'
import { Tuile, Tuiles } from '../../composants/atelier/Tuile'
import { Confirmer } from '../../composants/saisie/Confirmer'
import { nombre } from '../../lib/format'
import { aujourdhui } from '../../lib/heure'
import { useLecture } from '../../lib/requetes'
import { useSession } from '../../lib/session'
import { attente, NoteAtelier } from './briques'
import { qte } from './commun'
import styles from './atelier.module.css'
import type { OrdreResume, PageSignalements } from './types'

/** Les compteurs de « Signaler un besoin » : mes besoins en attente, et ceux qui ont une réponse. */
export function compteSignalements(page: PageSignalements | undefined, moi: number): string {
  const miens = (page?.elements ?? []).filter((x) => x.par_id === moi)
  const attente = miens.filter((x) => !x.traite_le).length
  const reponses = miens.filter((x) => x.traite_le).length
  if (!attente && !reponses) return 'Fil qui manque, palette qui finit.'
  return `${nombre(attente)} en attente · ${nombre(reponses)} réponse(s)`
}

/** L'astuce : en http, l'appli ne s'installe pas, on n'en promet qu'un raccourci (H-05). */
export function astuce(securise = window.isSecureContext): string {
  const debut = securise
    ? 'Astuce : « Ajouter à l’écran d’accueil » installe Gestion MP sur ce téléphone.'
    : 'Astuce : « Ajouter à l’écran d’accueil » crée un raccourci vers Gestion MP.'
  return `${debut} L’appareil photo lit les étiquettes QR : il ouvre la fiche du lot.`
}

function Resume({ nom }: { nom: string }) {
  const jour = aujourdhui()
  const ordres = useLecture<OrdreResume[]>('/ordres/ouverts', { statut: 'valide', du: jour, au: jour })
  const enAttente = attente([ordres], 'les sorties du jour')
  if (enAttente) return enAttente
  const liste = ordres.data ?? []
  const net = liste.reduce((t, o) => t + o.net, 0)
  return (
    <p className={styles.note}>
      Bonjour {nom}. Aujourd’hui, pour tout l’atelier : {nombre(liste.length)} ordre(s) validé(s), {qte(net)}{' '}
      sortis net.
    </p>
  )
}

function TuilesAtelier({ moi }: { moi: number }) {
  const brouillons = useLecture<OrdreResume[]>('/ordres/ouverts', { statut: 'brouillon' })
  const signalements = useLecture<PageSignalements>(
    '/signalements',
    { mes: true },
    { refetchInterval: 60_000, retry: false },
  )
  const nb = brouillons.data?.length ?? 0
  return (
    <Tuiles>
      <Tuile
        titre="Envoyer aux machines"
        icone="envoyer"
        vers="/atelier/envoyer"
        ton="accent"
        principale
        detail="Qualité et m² à fabriquer : fils et lots proposés."
      />
      <Tuile
        titre="Retour des machines"
        icone="retour"
        vers="/atelier/retour"
        detail="Ce qui revient, lot par lot."
      />
      <Tuile
        titre="Transfert entre magasins"
        icone="lots"
        vers="/atelier/deplacer"
        detail="D’un magasin à un autre."
      />
      <Tuile
        titre="Montage des machines"
        icone="usine"
        vers="/atelier/montage"
        detail="Fils montés et leur %, étage par étage."
      />
      <Tuile
        titre="Stock des fils"
        icone="recherche"
        vers="/atelier/chercher"
        detail="Où est un fil : magasins et atelier."
      />
      <Tuile
        titre="Ordres"
        icone="document"
        vers="/atelier/ordres"
        ton={nb ? 'attention' : undefined}
        detail={nb ? `${nombre(nb)} brouillon(s) à finir` : 'Les sorties récentes'}
      />
      <Tuile
        titre="Signaler un besoin"
        icone="signaler"
        vers="/atelier/signaler"
        detail={compteSignalements(signalements.data, moi)}
      />
    </Tuiles>
  )
}

export default function Accueil() {
  const { moi, deconnecter } = useSession()
  return (
    <EcranAtelier titre="Atelier" retour={false}>
      <Resume nom={moi.nom} />
      <TuilesAtelier moi={moi.id} />
      <NoteAtelier>{astuce()}</NoteAtelier>
      <div className={styles.gestes}>
        <Confirmer
          taille="atelier"
          question={`Se déconnecter (${moi.nom}) ?`}
          oui="Oui, se déconnecter"
          onOui={deconnecter}
        >
          Se déconnecter
        </Confirmer>
      </div>
    </EcranAtelier>
  )
}
