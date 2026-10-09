/**
 * Une valeur de classification en fenêtre (onglet Classification ; direction, achats) : la créer
 * (« Ajouter une composition ») ou la modifier (« Composition « PP » »). Changer le code renomme
 * la valeur sur les matières qui la portent ; leurs références déjà écrites ne changent pas.
 * Désactivée, elle n'est plus proposée ; le serveur dit combien de matières la gardent.
 */
import { useFermerFenetre, Fenetre } from '../../composants/mise-en-page/Fenetre'
import { dire } from '../../composants/retour/Messages'
import { Note } from '../../composants/retour/Note'
import { Bouton } from '../../composants/saisie/Bouton'
import { Confirmer } from '../../composants/saisie/Confirmer'
import { api, ErreurApi } from '../../lib/api'
import { nombre } from '../../lib/format'
import { ChampsValeur, corpsValeur, versFormeValeur, type FormeValeur } from './ChampsValeur'
import styles from './catalogue.module.css'
import { BandeauConflit } from './Conflit'
import type { Classification, DefinitionListe, Valeur } from './types'
import { useFiche, type Fiche } from './useFiche'

const egal = (a: FormeValeur, b: FormeValeur) => JSON.stringify(a) === JSON.stringify(b)
const nomMaj = (d: DefinitionListe) => d.nom[0]?.toUpperCase() + d.nom.slice(1)

/** Ce qui empêche de supprimer une valeur : les matières qui la portent. */
export function blocagesValeur(v: Valeur | null): string[] {
  return v?.nb_matieres
    ? [`Portée par ${nombre(v.nb_matieres)} matière(s) : la reclasser d’abord, ou la désactiver`]
    : []
}

/** Après une écriture : l'avertissement du serveur (matières qui gardent une valeur désactivée). */
export function direEnregistree(v: Valeur, d: DefinitionListe): void {
  if (v.avertissement) dire(v.avertissement, 'attention')
  else dire(`« ${v.code} » enregistré${d.feminin ? 'e' : ''}.`)
}

function Pied({
  f,
  d,
  ecrire,
  onFermer,
}: {
  f: Fiche<Valeur, FormeValeur>
  d: DefinitionListe
  ecrire: () => Promise<void>
  onFermer: () => void
}) {
  const fermer = useFermerFenetre()
  const v = f.base
  const code = corpsValeur(d, f.forme).code
  const supprimer = async () => {
    if (!v) return
    await f.executer(() => api.supprimer(`/classification/${d.liste}/${v.id}?version=${v.version}`))
    dire(`« ${v.code} » supprimé${d.feminin ? 'e' : ''}.`)
    onFermer()
  }
  return (
    <div className={styles.pied}>
      {v ? (
        <Confirmer
          variante="danger"
          question={`Supprimer « ${v.code} » ?`}
          oui="Oui, supprimer"
          blocages={blocagesValeur(v)}
          titre="Supprimer cette valeur, qu’aucune matière ne porte"
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
        manque={code ? undefined : ['le code']}
        grise={v && !f.sale ? 'Aucune modification.' : f.conflit ? 'Recharger d’abord la fiche.' : undefined}
        attente="Enregistrement…"
        onClick={ecrire}
      >
        {v ? 'Enregistrer' : 'Ajouter'}
      </Bouton>
    </div>
  )
}

/** Ajouter ou enregistrer la valeur, puis fermer ; le conflit de version reste sur la fiche. */
function useEcrireValeur(f: Fiche<Valeur, FormeValeur>, d: DefinitionListe, onFermer: () => void) {
  const v = f.base
  return async () => {
    const corps = corpsValeur(d, f.forme)
    if (!v) {
      await f.executer(() => api.post<Valeur>(`/classification/${d.liste}`, corps))
      dire(`« ${corps.code} » ajouté${d.feminin ? 'e' : ''}.`)
      return onFermer()
    }
    const rendue = await f.ecrire(
      () => api.put<Valeur>(`/classification/${d.liste}/${v.id}`, { ...corps, version: v.version }),
      '',
    )
    if (!rendue) return
    direEnregistree(rendue, d)
    onFermer()
  }
}

export function ValeurClassification({
  d,
  valeur,
  c,
  onFermer,
}: {
  d: DefinitionListe
  valeur: Valeur | null
  c: Classification
  onFermer: () => void
}) {
  const f = useFiche<Valeur, FormeValeur>(valeur, (v) => versFormeValeur(v), egal)
  const v = f.base
  const ecrire = useEcrireValeur(f, d, onFermer)
  const recharger = () =>
    f.recharger(async () => {
      const lue = (await api.get<Classification>('/classification'))[d.cle].find((x) => x.id === v?.id)
      if (!lue) throw new ErreurApi('Valeur introuvable.', 404, 'introuvable')
      return lue
    })
  const familles = [...new Set(c[d.cle].map((x) => x.famille ?? '').filter(Boolean))].sort()
  return (
    <Fenetre
      titre={v ? `${nomMaj(d)} « ${v.code} »` : `Ajouter ${d.un}`}
      onFermer={onFermer}
      sale={f.sale}
      pied={<Pied f={f} d={d} ecrire={ecrire} onFermer={onFermer} />}
    >
      <BandeauConflit message={f.conflit} onRecharger={recharger} />
      {v ? (
        <Note>
          Portée par {nombre(v.nb_matieres)} matière(s) du catalogue. Désactivée, elle ne sera plus proposée
          pour une nouvelle matière ; celles qui la portent la gardent.
        </Note>
      ) : (
        <Note>
          {d.note} Exemple : « {d.exemple} ».
        </Note>
      )}
      <ChampsValeur d={d} forme={f.forme} onChange={f.maj} familles={familles} />
      {v?.nb_matieres ? (
        <p className={styles.note}>
          Changer le code renomme la valeur sur les {nombre(v.nb_matieres)} matière(s) qui la portent ; leurs
          références déjà écrites ne changent pas.
        </p>
      ) : null}
    </Fenetre>
  )
}
