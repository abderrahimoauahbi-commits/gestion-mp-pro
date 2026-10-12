/**
 * Une unité de titrage en fenêtre (vue « Unités de titrage » de la classification ; direction,
 * achats) : l'ajouter (« Ajouter une unité ») ou la modifier (« Unité « Dtex » »). Le code
 * s'écrit comme dans les références (« Dtex », « lbs ») ; employée par un titrage, l'unité garde
 * son code (sa casse seule se corrige) : on ajoute la nouvelle et on désactive l'ancienne.
 */
import { Fenetre, useFermerFenetre } from '../../composants/mise-en-page/Fenetre'
import { Grille } from '../../composants/mise-en-page/Grille'
import { dire } from '../../composants/retour/Messages'
import { Note } from '../../composants/retour/Note'
import { Bouton } from '../../composants/saisie/Bouton'
import { Champ } from '../../composants/saisie/Champ'
import { Confirmer } from '../../composants/saisie/Confirmer'
import { Interrupteur } from '../../composants/saisie/Interrupteur'
import { Nombre } from '../../composants/saisie/Nombre'
import { Saisie } from '../../composants/saisie/Saisie'
import { api, ErreurApi } from '../../lib/api'
import { nombre } from '../../lib/format'
import { LONGUEURS } from './bornes'
import styles from './catalogue.module.css'
import { BandeauConflit } from './Conflit'
import type { Classification, UniteTitrage } from './types'
import { useFiche, type Fiche } from './useFiche'

/** La longueur d'une unité : celle de `titrage.unite`. */
export const UNITE_MAX = 16

export interface FormeUnite {
  code: string
  libelle: string
  ordre: number | null
  actif: boolean
}

const versForme = (u: UniteTitrage | null): FormeUnite => ({
  code: u?.code ?? '',
  libelle: u?.libelle ?? '',
  ordre: u?.ordre ?? null,
  actif: u?.actif ?? true,
})
const egal = (a: FormeUnite, b: FormeUnite) => JSON.stringify(a) === JSON.stringify(b)

/** Le corps de `POST`/`PUT /classification/unites-titrage` (ordre vide : après la dernière). */
export function corpsUnite(f: FormeUnite) {
  return { code: f.code.trim(), libelle: f.libelle.trim(), ordre: f.ordre, actif: f.actif }
}

/** Ce qui empêche de supprimer une unité : la raison du serveur (titrages qui l'écrivent). */
export function blocagesUnite(u: UniteTitrage | null): string[] {
  return u?.raison_garder ? [u.raison_garder] : []
}

function ChampsUnite({ f, employee }: { f: Fiche<UniteTitrage, FormeUnite>; employee: boolean }) {
  return (
    <Grille colonnes={2}>
      <Champ
        libelle="Code"
        obligatoire
        aide={
          employee ? 'employée : sa casse seule se corrige' : 'comme dans les références : « Dtex », « lbs »'
        }
      >
        <Saisie valeur={f.forme.code} onChange={(v) => f.maj({ code: v })} max={UNITE_MAX} autoFocus />
      </Champ>
      <Champ libelle="Libellé" aide="facultatif : « numéro anglais (coton) »">
        <Saisie valeur={f.forme.libelle} onChange={(v) => f.maj({ libelle: v })} max={LONGUEURS.LIBELLE} />
      </Champ>
      <Champ libelle="Ordre" aide="l’ordre de la liste ; vide : après la dernière">
        <Nombre
          valeur={f.forme.ordre}
          onChange={(v) => f.maj({ ordre: v })}
          min={0}
          max={9999}
          decimales={0}
        />
      </Champ>
      <Champ libelle="État" groupe>
        <Interrupteur
          valeur={f.forme.actif}
          onChange={(v) => f.maj({ actif: v })}
          libelle="Active (proposée, et lue dans les références)"
        />
      </Champ>
    </Grille>
  )
}

function PiedUnite({
  f,
  ecrire,
  onFermer,
}: {
  f: Fiche<UniteTitrage, FormeUnite>
  ecrire: () => Promise<void>
  onFermer: () => void
}) {
  const fermer = useFermerFenetre()
  const u = f.base
  const supprimer = async () => {
    if (!u) return
    await f.executer(() => api.supprimer(`/classification/unites-titrage/${u.id}?version=${u.version}`))
    dire(`Unité « ${u.code} » supprimée.`)
    onFermer()
  }
  return (
    <div className={styles.pied}>
      {u ? (
        <Confirmer
          variante="danger"
          question={`Supprimer l’unité « ${u.code} » ?`}
          oui="Oui, supprimer"
          blocages={blocagesUnite(u)}
          titre="Supprimer cette unité, qu’aucun titrage n’écrit"
          onOui={supprimer}
        >
          Supprimer
        </Confirmer>
      ) : null}
      <span className={styles.pousse} />
      <Bouton variante="fantome" onClick={fermer}>
        {f.sale ? 'Abandonner les modifications' : 'Fermer'}
      </Bouton>
      <Bouton
        variante="principal"
        manque={f.forme.code.trim() ? undefined : ['le code']}
        grise={u && !f.sale ? 'Aucune modification.' : f.conflit ? 'Recharger d’abord la fiche.' : undefined}
        attente="Enregistrement…"
        onClick={ecrire}
      >
        {u ? 'Enregistrer' : 'Ajouter'}
      </Bouton>
    </div>
  )
}

/** Ajouter ou enregistrer l'unité, puis fermer ; le conflit de version reste sur la fiche. */
function useEcrireUnite(f: Fiche<UniteTitrage, FormeUnite>, onFermer: () => void) {
  return async () => {
    const u = f.base
    const corps = corpsUnite(f.forme)
    if (!u) {
      await f.executer(() => api.post<UniteTitrage>('/classification/unites-titrage', corps))
      dire(`Unité « ${corps.code} » ajoutée : elle se choisit pour un titrage et se lit dans les références.`)
      return onFermer()
    }
    const envoi = () =>
      api.put<UniteTitrage>(`/classification/unites-titrage/${u.id}`, { ...corps, version: u.version })
    const rendue = await f.ecrire(envoi, '')
    if (!rendue) return
    if (rendue.avertissement) dire(rendue.avertissement, 'attention')
    else dire(`Unité « ${rendue.code} » enregistrée.`)
    onFermer()
  }
}

export function FenetreUnite({ unite, onFermer }: { unite: UniteTitrage | null; onFermer: () => void }) {
  const f = useFiche<UniteTitrage, FormeUnite>(unite, versForme, egal)
  const u = f.base
  const ecrire = useEcrireUnite(f, onFermer)
  const recharger = () =>
    f.recharger(async () => {
      const lue = (await api.get<Classification>('/classification')).unites_titrage.find(
        (x) => x.id === u?.id,
      )
      if (!lue) throw new ErreurApi('Unité de titrage introuvable.', 404, 'introuvable')
      return lue
    })
  return (
    <Fenetre
      titre={u ? `Unité « ${u.code} »` : 'Ajouter une unité de titrage'}
      onFermer={onFermer}
      sale={f.sale}
      pied={<PiedUnite f={f} ecrire={ecrire} onFermer={onFermer} />}
    >
      <BandeauConflit message={f.conflit} onRecharger={recharger} />
      {u ? (
        <Note>
          Écrite sur {nombre(u.nb_titrages)} titrage(s), portés par {nombre(u.nb_matieres)} matière(s).
          Désactivée, elle n’est plus proposée ni lue dans une nouvelle référence ; les titrages qui
          l’écrivent la gardent.
        </Note>
      ) : (
        <Note>
          L’unité du titrage, telle qu’elle s’écrit dans les références : « 20 Ne », « 8 lbs ». Elle se lit
          aussitôt dans les références (« Relire les références »).
        </Note>
      )}
      <ChampsUnite f={f} employee={(u?.nb_titrages ?? 0) > 0} />
    </Fenetre>
  )
}
