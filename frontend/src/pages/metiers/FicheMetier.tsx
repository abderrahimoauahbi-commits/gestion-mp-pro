/**
 * La fiche d'un métier en fenêtre sur la liste (`/metiers/:id?onglet=fils|reglages|historique`).
 * Direction : réglage et fils, enregistrés ensemble ; alimentation : les fils ; achats : lecture.
 * « Enregistrer » se confirme avec le texte unique de l'effet sur le stock sur les métiers ((a))
 * et les alertes 30 jours ; une version périmée se recharge.
 */
import { Fenetre } from '../../composants/mise-en-page/Fenetre'
import { Onglets } from '../../composants/mise-en-page/Onglets'
import { Badge } from '../../composants/retour/Badge'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { Note } from '../../composants/retour/Note'
import { useOngletAdresse } from '../../lib/adresse'
import { horodatage, kg, nombre, nombreSigne } from '../../lib/format'
import { api } from '../../lib/api'
import { useLecture } from '../../lib/requetes'
import type { Role } from '../../lib/types'
import { nomMetier } from '../atelier/commun'
import type { MetierFiche } from '../atelier/types'
import { BandeauConflit } from '../catalogue/Conflit'
import { ChampsMetier } from './ChampsMetier'
import { OngletFils } from './OngletFils'
import { OngletHistorique } from './OngletHistorique'
import { PiedMetier } from './PiedMetier'
import { useFicheMetier, type FicheMetierEtat } from './useFicheMetier'

type Volet = 'fils' | 'reglages' | 'historique'
const VOLETS: readonly Volet[] = ['fils', 'reglages', 'historique']

/** « Laize 4,20 m par étage · densité 320 bobines par mètre · … Sur les métiers : 3 354 kg, 1 344 bobines. » */
export function noteMetier(e: FicheMetierEtat): string {
  const f = e.forme
  const densite = f.bobines_par_metre
    ? `densité ${nombre(f.bobines_par_metre)} bobines par mètre`
    : 'densité à saisir (réglages)'
  return (
    `Laize ${nombre(f.laize, 2)} m par étage · ${densite} · bobines = mètres × densité ; poids = bobines × kg / ` +
    `bobine pesé au lot (à défaut, le catalogue) × remplissage des bobines. Sur les métiers : ${kg(e.m.sur_les_metiers)}, ${nombre(e.m.bobines)} bobines.`
  )
}

function Lecture({ role }: { role: Role }) {
  if (role === 'achats')
    return <Note>Lecture seule : l’alimentation monte les fils, la direction règle le métier.</Note>
  if (role === 'alimentation') return <Note>Vous montez les fils ; la direction règle le métier.</Note>
  return null
}

function Contenu({ fiche, role, onFermer }: { fiche: MetierFiche; role: Role; onFermer: () => void }) {
  const direction = role === 'direction'
  const monteur = direction || role === 'alimentation'
  const e = useFicheMetier(fiche, direction, onFermer)
  const [volet, choisir] = useOngletAdresse(VOLETS, 'fils')
  const d = e.m.dernier_montage
  return (
    <Fenetre
      titre={
        <>
          Métier {nomMetier(e.m)} {e.m.actif ? null : <Badge famille="metier" valeur="arrete" />}
        </>
      }
      onFermer={onFermer}
      sale={monteur && e.sale}
      taille="tresLarge"
      pied={<PiedMetier e={e} direction={direction} monteur={monteur} />}
    >
      <Lecture role={role} />
      <BandeauConflit
        message={e.conflit}
        libelle="Recharger le métier"
        onRecharger={() => e.recharger(() => api.get<MetierFiche>(`/metiers/${e.m.id}`))}
      />
      <Note>
        {noteMetier(e)}
        {e.forme.actif ? '' : ' Métier arrêté : ce poids ne compte pas dans le stock.'}
        {d
          ? ` Dernier montage : ${d.par ?? '—'}, le ${horodatage(d.quand)} (${nombreSigne(d.effet_kg, 0, 2)} kg).`
          : ''}
      </Note>
      <Onglets<Volet>
        libelle="Volets du métier"
        actif={volet}
        onChange={choisir}
        onglets={[
          { cle: 'fils', libelle: 'Fils montés', compte: e.forme.fils.length, sale: e.filsChanges },
          { cle: 'reglages', libelle: 'Réglages du métier', sale: direction && e.sale && !e.filsChanges },
          { cle: 'historique', libelle: 'Historique' },
        ]}
      />
      {volet === 'fils' ? <OngletFils e={e} ecrit={monteur} lienMatiere={role !== 'alimentation'} /> : null}
      {volet === 'reglages' ? (
        <>
          <ChampsMetier f={e.forme} maj={e.maj} lecture={!direction} />
          <Note>
            Changer la densité change le stock sur les métiers. Réduire les étages ou la laize demande d’abord
            de retirer ou déplacer les fils qui dépasseraient.
            {e.m.ordres ? ` Nommé par ${nombre(e.m.ordres)} ordre(s) de fabrication.` : ''}
          </Note>
        </>
      ) : null}
      {volet === 'historique' ? <OngletHistorique id={e.m.id} /> : null}
    </Fenetre>
  )
}

export function FicheMetier({ id, role, onFermer }: { id: number; role: Role; onFermer: () => void }) {
  const fiche = useLecture<MetierFiche>(`/metiers/${id}`)
  if (fiche.isError)
    return (
      <Fenetre titre="Métier" onFermer={onFermer}>
        <Erreur erreur={fiche.error} onReessayer={() => void fiche.refetch()} />
      </Fenetre>
    )
  if (!fiche.data)
    return (
      <Fenetre titre="Métier" onFermer={onFermer}>
        <Chargement quoi="le métier" />
      </Fenetre>
    )
  return <Contenu fiche={fiche.data} role={role} onFermer={onFermer} />
}
