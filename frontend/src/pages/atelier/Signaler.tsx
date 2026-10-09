/**
 * Signaler un besoin (`/atelier/signaler`) : une matière (facultative), le besoin, l'urgence →
 * les achats le voient sur leur accueil. La saisie est gardée jusqu'à l'envoi (an. 17). « Mes
 * signalements » : ceux du compte connecté, filtrés au serveur par identifiant (an. 25), 40 puis
 * « charger les suivants » ; une coupure dit « Pas de réseau ».
 */
import { useState } from 'react'

import { EcranAtelier } from '../../composants/atelier/EcranAtelier'
import { SegmentsTactiles } from '../../composants/atelier/SegmentsTactiles'
import { useSaisieGardee } from '../../composants/atelier/saisieGardee'
import { versChoix } from '../../composants/coque/SignalerBesoin'
import { Badge } from '../../composants/retour/Badge'
import { dire } from '../../composants/retour/Messages'
import { Vide } from '../../composants/retour/Vide'
import { Bouton } from '../../composants/saisie/Bouton'
import { Champ } from '../../composants/saisie/Champ'
import { SelecteurMatiere } from '../../composants/saisie/SelecteurMatiere'
import { Zone } from '../../composants/saisie/Zone'
import { api } from '../../lib/api'
import { horodatage, date } from '../../lib/format'
import { useEcriture, useLecture } from '../../lib/requetes'
import { useSession } from '../../lib/session'
import type { MatiereResumee, SignalementCreation } from '../../lib/types-provisoires'
import { attente, Fiche, NoteAtelier } from './briques'
import styles from './atelier.module.css'
import { ChargerSuivants } from './Ordres'
import type { PageSignalements, SignalementFiche } from './types'

const PAGE_SIGNALEMENTS = 40

const vide = (): SignalementCreation => ({ matiere_id: null, texte: '', urgence: 'normale' })

/** Le statut d'un signalement : traité, urgent en attente, en attente. */
export const etatSignalement = (x: SignalementFiche) =>
  x.traite_le ? 'traite' : x.urgence === 'urgente' ? 'urgent' : 'en_attente'

function MesSignalements({ moi, matieres }: { moi: number; matieres: readonly MatiereResumee[] }) {
  const lus = useLecture<PageSignalements>('/signalements', { mes: true }, { refetchInterval: 60_000 })
  const [nb, setNb] = useState(PAGE_SIGNALEMENTS)
  const miens = (lus.data?.elements ?? []).filter((x) => x.par_id === moi)
  const reference = (x: SignalementFiche) =>
    x.reference ?? matieres.find((m) => m.id === x.matiere_id)?.reference ?? 'Sans matière précise'
  return (
    <section className={styles.pile} aria-label="Mes signalements">
      <h2 className={styles.titreFiche}>Mes signalements</h2>
      {attente([lus], 'vos signalements') ?? (
        <>
          {!miens.length ? <Vide>Aucun signalement pour l’instant.</Vide> : null}
          {miens.slice(0, nb).map((x) => (
            <Fiche
              key={x.id}
              titre={x.matiere_id ? reference(x) : 'Sans matière précise'}
              ton={etatSignalement(x) === 'urgent' ? 'alerte' : undefined}
            >
              <Badge famille="signalement" valeur={etatSignalement(x)} />
              <span>{x.texte}</span>
              <NoteAtelier>Signalé le {horodatage(x.quand)}</NoteAtelier>
              {x.traite_le ? (
                <NoteAtelier>
                  <strong>Réponse de {x.traite_par ?? '—'}</strong> le {date(x.traite_le)} :{' '}
                  {x.reponse || '—'}
                </NoteAtelier>
              ) : null}
            </Fiche>
          ))}
          <ChargerSuivants
            montres={Math.min(nb, miens.length)}
            total={miens.length}
            onCharger={() => setNb(nb + PAGE_SIGNALEMENTS)}
          />
        </>
      )}
    </section>
  )
}

export default function Signaler() {
  const { moi } = useSession()
  const matieres = useLecture<MatiereResumee[]>('/matieres', { actif: true })
  const [s, setS, oublier] = useSaisieGardee<SignalementCreation>('signaler', vide())
  const poser = (m: Partial<SignalementCreation>) => setS((avant) => ({ ...avant, ...m }))
  const envoi = useEcriture((corps: SignalementCreation) => api.post('/signalements', corps))
  const envoyer = async () => {
    await envoi.mutateAsync({ ...s, texte: s.texte.trim() })
    oublier()
    setS(vide())
    dire('Signalé : les achats le voient sur leur accueil.')
  }
  return (
    <EcranAtelier titre="Signaler un besoin" retour="/atelier">
      <div className={styles.pile}>
        {attente([matieres], 'les matières')}
        <SelecteurMatiere
          libelle="Matière (facultatif)"
          matieres={(matieres.data ?? []).map(versChoix)}
          valeur={s.matiere_id}
          onChange={(id) => poser({ matiere_id: id })}
        />
        <Champ libelle="Quel besoin ?" obligatoire>
          <Zone
            valeur={s.texte}
            onChange={(texte) => poser({ texte })}
            max={500}
            lignes={4}
            placeholder="Plus que deux palettes de beige, la série 8F commence lundi…"
          />
        </Champ>
        <Champ groupe libelle="Urgence">
          <SegmentsTactiles
            libelle="Urgence"
            valeur={s.urgence}
            options={[
              { valeur: 'normale', libelle: 'Normal' },
              { valeur: 'urgente', libelle: 'Urgent' },
            ]}
            onChange={(urgence) => poser({ urgence })}
          />
        </Champ>
        <Bouton
          taille="atelier"
          variante="principal"
          bloc
          grise={s.texte.trim().length >= 2 ? undefined : 'Écrire le besoin (2 caractères au moins)'}
          attente="Envoi…"
          onClick={envoyer}
        >
          Signaler aux achats
        </Bouton>
        <MesSignalements moi={moi.id} matieres={matieres.data ?? []} />
      </div>
    </EcranAtelier>
  )
}
