/**
 * Un poste de frais en fenêtre (ECRANS-PRO 5.20) : `/reglages?onglet=postes&poste=ID|nouveau`,
 * volets « Poste » · « Historique » (`&volet=historique`). La direction crée, modifie, supprime ;
 * les achats lisent (champs grisés, « Fermer » seul). Le code ne change plus après la création ;
 * la nature (« récupérable ») est figée pour un poste système ou porté par un dossier clos ;
 * changer la clé dit d'avance ce que deviennent les dossiers ouverts et clos, puis le toast dit
 * ce que le serveur a fait (anomalie 5.12). Version périmée : bandeau « Recharger la fiche ».
 */
import { useQueryClient } from '@tanstack/react-query'

import { Historique } from '../../../composants/documents/Historique'
import { Fenetre, useFermerFenetre } from '../../../composants/mise-en-page/Fenetre'
import { Onglets } from '../../../composants/mise-en-page/Onglets'
import { dire } from '../../../composants/retour/Messages'
import { Bouton } from '../../../composants/saisie/Bouton'
import { Confirmer } from '../../../composants/saisie/Confirmer'
import { messageNombre } from '../../../composants/saisie/Nombre'
import { api, ErreurApi } from '../../../lib/api'
import { useEcriture } from '../../../lib/requetes'
import { BandeauConflit } from '../../catalogue/Conflit'
import { useFiche, type Fiche } from '../../catalogue/useFiche'
import type { PosteFiche } from '../types'
import { ChampsPoste, LecturePoste } from './ChampsPoste'
import type { VoletReglage } from './fenetreAdresse'
import {
  blocagesPoste,
  corpsCreation,
  corpsModification,
  egalPoste,
  erreurCodePoste,
  manquesPoste,
  messageEnregistre,
  versFormePoste,
  type FormePoste,
} from './formePoste'
import { PiedLecture } from './PiedLecture'
import styles from './reglages.module.css'

type FichePoste = Fiche<PosteFiche, FormePoste>

const BORNES_ORDRE = { min: 0, max: 999, decimales: 0 }

/** Pourquoi « Enregistrer » est grisé hors des champs à renseigner, ou `undefined`. */
function raisonEnregistrer(f: FichePoste): string | undefined {
  if (f.conflit) return 'Recharger d’abord la fiche.'
  if (f.base && !f.sale) return 'Rien n’a changé.'
  const code = f.base ? '' : erreurCodePoste(f.forme.code)
  const ordre = messageNombre(f.forme.ordre, BORNES_ORDRE)
  return [code, ordre && `Ordre : ${ordre}`].filter(Boolean).join(' ') || undefined
}

/** Créer, enregistrer, supprimer : chaque geste dit ce qu'il a fait, puis la fenêtre se ferme. */
function useGestesPoste(f: FichePoste, onFermer: () => void) {
  const client = useQueryClient()
  // Supprimer ferme d'abord la fenêtre, puis relit la liste (sans fiche « introuvable » entre-temps).
  const effacer = useEcriture(
    (p: PosteFiche) => api.supprimer(`/postes-frais/${p.id}?version=${p.version}`),
    {
      invalider: false,
    },
  )
  return {
    creer: async () => {
      const corps = corpsCreation(f.forme)
      await f.executer(() => api.post<PosteFiche>('/postes-frais', corps))
      dire(`Poste ${corps.code} créé.`)
      onFermer()
    },
    enregistrer: async () => {
      const p = f.base
      if (!p) return
      const rendu = await f.ecrire(
        () => api.put<PosteFiche>(`/postes-frais/${p.id}`, corpsModification(f.forme, p)),
        '',
      )
      if (!rendu) return
      dire(messageEnregistre(p, rendu))
      onFermer()
    },
    supprimer: async () => {
      const p = f.base
      if (!p) return
      await effacer.mutateAsync(p)
      onFermer()
      dire(`Poste ${p.code} supprimé.`)
      await client.invalidateQueries()
    },
  }
}

function PiedPoste({ f, onFermer }: { f: FichePoste; onFermer: () => void }) {
  const fermer = useFermerFenetre()
  const gestes = useGestesPoste(f, onFermer)
  const p = f.base
  return (
    <div className={styles.pied}>
      {p ? (
        <Confirmer
          variante="danger"
          question="Supprimer ce poste ?"
          oui="Oui, supprimer"
          blocages={blocagesPoste(p)}
          titre="Supprimer ce poste, qui ne porte aucun frais"
          attente="Suppression…"
          onOui={gestes.supprimer}
        >
          Supprimer
        </Confirmer>
      ) : null}
      <span className={styles.pousse} />
      <span className={styles.etat} aria-live="polite">
        {f.sale ? 'Non enregistré.' : ''}
      </span>
      <Bouton variante="fantome" onClick={fermer}>
        {f.sale ? 'Abandonner les modifications' : 'Fermer'}
      </Bouton>
      <Bouton
        variante="principal"
        manque={manquesPoste(f.forme)}
        grise={raisonEnregistrer(f)}
        attente={p ? 'Enregistrement…' : 'Création…'}
        onClick={p ? gestes.enregistrer : gestes.creer}
      >
        {p ? 'Enregistrer' : 'Créer le poste'}
      </Bouton>
    </div>
  )
}

/** Relire le poste dans sa dernière version (après un conflit de version). */
async function relire(id: number): Promise<PosteFiche> {
  const lu = (await api.get<PosteFiche[]>('/postes-frais')).find((x) => x.id === id)
  if (!lu) throw new ErreurApi('Poste de frais introuvable.', 404, 'introuvable')
  return lu
}

export function FenetrePoste({
  poste,
  ecrit,
  volet,
  onVolet,
  onFermer,
}: {
  poste: PosteFiche | null
  /** La direction écrit ; les achats lisent. */
  ecrit: boolean
  volet: VoletReglage
  onVolet: (v: VoletReglage) => void
  onFermer: () => void
}) {
  const f = useFiche<PosteFiche, FormePoste>(poste, versFormePoste, egalPoste)
  const p = f.base
  const vue = p ? volet : 'fiche'
  return (
    <Fenetre
      titre={p ? `Poste ${p.code} — ${p.libelle}` : 'Nouveau poste de frais'}
      onFermer={onFermer}
      sale={ecrit && f.sale}
      pied={ecrit ? <PiedPoste f={f} onFermer={onFermer} /> : <PiedLecture />}
    >
      <BandeauConflit
        message={f.conflit}
        onRecharger={() => (p ? f.recharger(() => relire(p.id)) : undefined)}
      />
      {p ? (
        <Onglets<VoletReglage>
          libelle="Volets du poste"
          actif={vue}
          onChange={onVolet}
          onglets={[
            { cle: 'fiche', libelle: 'Poste', sale: ecrit && f.sale },
            { cle: 'historique', libelle: 'Historique' },
          ]}
        />
      ) : null}
      {vue === 'fiche' ? (
        <div className={styles.volet}>
          {ecrit || !p ? <ChampsPoste forme={f.forme} maj={f.maj} poste={p} /> : <LecturePoste poste={p} />}
        </div>
      ) : null}
      {vue === 'historique' && p ? <Historique objet="poste_frais" id={p.id} /> : null}
    </Fenetre>
  )
}
