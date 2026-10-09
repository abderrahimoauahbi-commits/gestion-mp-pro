/**
 * Un code douanier en fenêtre (ECRANS-PRO 5.22) : `/reglages?onglet=codes&code=ID|nouveau`, volets
 * « Code » · « Historique » (`&volet=historique`). La direction crée, corrige (les matières qui le
 * portent suivent), désactive ou supprime un code qu'aucune matière ne porte ; les achats lisent.
 * Le taux se saisit en % et part en fraction (10 % → 0,1). Version périmée : « Recharger la fiche ».
 */
import { useQueryClient } from '@tanstack/react-query'

import { Historique } from '../../../composants/documents/Historique'
import { Fenetre, useFermerFenetre } from '../../../composants/mise-en-page/Fenetre'
import { Onglets } from '../../../composants/mise-en-page/Onglets'
import { dire } from '../../../composants/retour/Messages'
import { Bouton } from '../../../composants/saisie/Bouton'
import { Confirmer } from '../../../composants/saisie/Confirmer'
import { api, ErreurApi } from '../../../lib/api'
import { useEcriture } from '../../../lib/requetes'
import { BandeauConflit } from '../../catalogue/Conflit'
import { useFiche, type Fiche } from '../../catalogue/useFiche'
import type { CodeDouanier } from '../types'
import { ChampsCode, LectureCode } from './ChampsCode'
import type { VoletReglage } from './fenetreAdresse'
import {
  blocagesCode,
  corpsCode,
  egalCode,
  erreurCodeDouanier,
  manquesCode,
  versFormeCode,
  type FormeCode,
} from './formeCode'
import { PiedLecture } from './PiedLecture'
import styles from './reglages.module.css'

type FicheCode = Fiche<CodeDouanier, FormeCode>

/** Pourquoi « Enregistrer » est grisé hors des champs à renseigner, ou `undefined`. */
function raisonEnregistrer(f: FicheCode): string | undefined {
  if (f.conflit) return 'Recharger d’abord la fiche.'
  if (f.base && !f.sale) return 'Rien n’a changé.'
  return erreurCodeDouanier(f.forme.code) || undefined
}

/** Créer, enregistrer, supprimer : chaque geste dit ce qu'il a fait, puis la fenêtre se ferme. */
function useGestesCode(f: FicheCode, onFermer: () => void) {
  const client = useQueryClient()
  // Supprimer ferme d'abord la fenêtre, puis relit la liste (sans fiche « introuvable » entre-temps).
  const effacer = useEcriture(
    (c: CodeDouanier) => api.supprimer(`/codes-douaniers/${c.id}?version=${c.version}`),
    { invalider: false },
  )
  return {
    creer: async () => {
      const corps = corpsCode(f.forme)
      await f.executer(() => api.post<CodeDouanier>('/codes-douaniers', corps))
      dire(`Code douanier ${corps.code} créé.`)
      onFermer()
    },
    enregistrer: async () => {
      const c = f.base
      if (!c) return
      const corps = { ...corpsCode(f.forme), version: c.version }
      const rendu = await f.ecrire(() => api.put<CodeDouanier>(`/codes-douaniers/${c.id}`, corps), '')
      if (!rendu) return
      dire(`Code douanier ${rendu.code} enregistré.`)
      onFermer()
    },
    supprimer: async () => {
      const c = f.base
      if (!c) return
      await effacer.mutateAsync(c)
      onFermer()
      dire(`Code douanier ${c.code} supprimé.`)
      await client.invalidateQueries()
    },
  }
}

function PiedCode({ f, onFermer }: { f: FicheCode; onFermer: () => void }) {
  const fermer = useFermerFenetre()
  const gestes = useGestesCode(f, onFermer)
  const c = f.base
  return (
    <div className={styles.pied}>
      {c ? (
        <Confirmer
          variante="danger"
          question="Supprimer ce code ?"
          oui="Oui, supprimer"
          blocages={blocagesCode(c)}
          titre="Supprimer ce code, qu’aucune matière ne porte"
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
        manque={manquesCode(f.forme)}
        grise={raisonEnregistrer(f)}
        attente={c ? 'Enregistrement…' : 'Création…'}
        onClick={c ? gestes.enregistrer : gestes.creer}
      >
        {c ? 'Enregistrer' : 'Créer le code'}
      </Bouton>
    </div>
  )
}

/** Relire le code dans sa dernière version (après un conflit de version). */
async function relire(id: number): Promise<CodeDouanier> {
  const lu = (await api.get<CodeDouanier[]>('/codes-douaniers')).find((x) => x.id === id)
  if (!lu) throw new ErreurApi('Code douanier introuvable.', 404, 'introuvable')
  return lu
}

export function FenetreCode({
  code,
  ecrit,
  volet,
  onVolet,
  onFermer,
}: {
  code: CodeDouanier | null
  /** La direction écrit ; les achats lisent. */
  ecrit: boolean
  volet: VoletReglage
  onVolet: (v: VoletReglage) => void
  onFermer: () => void
}) {
  const f = useFiche<CodeDouanier, FormeCode>(code, versFormeCode, egalCode)
  const c = f.base
  const vue = c ? volet : 'fiche'
  return (
    <Fenetre
      titre={c ? `Code douanier ${c.code}` : 'Nouveau code douanier'}
      onFermer={onFermer}
      sale={ecrit && f.sale}
      pied={ecrit ? <PiedCode f={f} onFermer={onFermer} /> : <PiedLecture />}
    >
      <BandeauConflit
        message={f.conflit}
        onRecharger={() => (c ? f.recharger(() => relire(c.id)) : undefined)}
      />
      {c ? (
        <Onglets<VoletReglage>
          libelle="Volets du code douanier"
          actif={vue}
          onChange={onVolet}
          onglets={[
            { cle: 'fiche', libelle: 'Code', sale: ecrit && f.sale },
            { cle: 'historique', libelle: 'Historique' },
          ]}
        />
      ) : null}
      {vue === 'fiche' ? (
        <div className={styles.volet}>
          {ecrit || !c ? <ChampsCode forme={f.forme} maj={f.maj} code={c} /> : <LectureCode c={c} />}
        </div>
      ) : null}
      {vue === 'historique' && c ? <Historique objet="code_douanier" id={c.id} /> : null}
    </Fenetre>
  )
}
