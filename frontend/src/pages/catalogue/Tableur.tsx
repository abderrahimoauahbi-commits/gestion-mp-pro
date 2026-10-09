/**
 * « Le catalogue par tableur » (`/catalogue/tableur`, fenêtre sur les matières ; direction,
 * achats). Télécharger le modèle (le catalogue actuel), le corriger dans Excel, le relire ici :
 * l'aperçu dit ce qui sera créé, modifié (champ par champ, avant → après, P7-11) ou refusé ;
 * rien n'est écrit avant « Appliquer ».
 *
 * L'aperçu **est** l'application : « Appliquer » renvoie le même fichier avec l'empreinte du plan
 * que l'aperçu a montré ; si le catalogue a changé depuis, le serveur refuse (409) au lieu
 * d'écrire autre chose que ce qu'on a vu. Un tableur en erreur n'écrit rien.
 */
import { useRef, useState } from 'react'

import { Fenetre } from '../../composants/mise-en-page/Fenetre'
import { Indicateurs } from '../../composants/mise-en-page/Indicateurs'
import { Erreur } from '../../composants/retour/Erreur'
import { Kpi } from '../../composants/retour/Kpi'
import { dire } from '../../composants/retour/Messages'
import { Note } from '../../composants/retour/Note'
import { Bouton } from '../../composants/saisie/Bouton'
import { Confirmer } from '../../composants/saisie/Confirmer'
import { adresseApi, api, requete } from '../../lib/api'
import { formule } from '../../lib/aide'
import { nombre } from '../../lib/format'
import { useEcriture } from '../../lib/requetes'
import styles from './catalogue.module.css'
import { VolumesApercu } from './TableurApercu'
import type { ApercuImport } from './types'

export const APPLIQUE = 'Tableur appliqué : le catalogue est à jour, chaque changement est au journal.'

/** Ce qu'écrira l'application : les matières créées et modifiées. */
export const aEcrire = (a: ApercuImport) => a.creees + a.modifiees

/** La note du pied : en erreur, rien à écrire, ou combien de matières seront écrites. */
export function notePied(a: ApercuImport | null): string {
  if (!a) return 'Rien n’est écrit tant qu’on n’a pas vu ce qui changera et cliqué « Appliquer ».'
  if (a.erreurs)
    return 'Corriger les erreurs dans le tableur, puis le relire : un tableur en erreur n’écrit rien.'
  const n = aEcrire(a)
  if (!n) return 'Rien à écrire : le tableur dit la même chose que le catalogue.'
  return `${nombre(n)} matière${n > 1 ? 's' : ''} ${n > 1 ? 'seront écrites' : 'sera écrite'}.`
}

function ModeEmploi() {
  return (
    <Note>
      <ol className={styles.liste}>
        <li>Télécharger le modèle : c’est le catalogue actuel, une matière par ligne.</li>
        <li>
          Le corriger ou le compléter dans Excel (une ligne nouvelle crée une matière ; aucune n’est
          supprimée).
        </li>
        <li>
          Le relire ici : rien n’est écrit tant qu’on n’a pas vu ce qui changera et cliqué « Appliquer ».
        </li>
      </ol>
      Une case vide ne change rien ; pour vider une case, nommer sa colonne dans « Vider ».
    </Note>
  )
}

function Compteurs({ a }: { a: ApercuImport }) {
  return (
    <Indicateurs libelle="Ce que le tableur changera">
      <Kpi
        titre="Créées"
        valeur={nombre(a.creees)}
        detail="matières nouvelles"
        ton={a.creees ? 'ok' : undefined}
        formule={formule('tableur_creees')}
      />
      <Kpi
        titre="Modifiées"
        valeur={nombre(a.modifiees)}
        detail="au moins un champ change"
        formule={formule('tableur_modifiees')}
      />
      <Kpi
        titre="Inchangées"
        valeur={nombre(a.inchangees)}
        detail="rien à faire"
        formule={formule('tableur_inchangees')}
      />
      <Kpi
        titre="Erreurs"
        valeur={nombre(a.erreurs)}
        detail={a.erreurs ? 'à corriger dans le tableur' : 'tableur juste'}
        ton={a.erreurs ? 'critique' : 'ok'}
        formule={formule('tableur_erreurs')}
      />
    </Indicateurs>
  )
}

function Pied({ apercu, appliquer }: { apercu: ApercuImport | null; appliquer: () => Promise<void> }) {
  const n = apercu ? aEcrire(apercu) : 0
  return (
    <div className={styles.pied}>
      <span className={styles.etat}>{notePied(apercu)}</span>
      <span className={styles.pousse} />
      <Confirmer
        variante="principal"
        question={`Écrire ${nombre(n)} matière${n > 1 ? 's' : ''} au catalogue ?`}
        oui="Oui, appliquer"
        titre="Créer et modifier les matières lues"
        grise={
          !apercu
            ? 'Relire d’abord un tableur.'
            : apercu.erreurs
              ? undefined
              : n
                ? undefined
                : 'Rien à écrire.'
        }
        blocages={apercu?.erreurs ? ['Des lignes sont en erreur : corriger le tableur d’abord'] : undefined}
        attente="Écriture…"
        onOui={appliquer}
      >
        Appliquer
      </Confirmer>
    </div>
  )
}

/** Le fichier choisi, son aperçu (relu aussitôt), et l'application de ce même aperçu. */
function useTableur(onFermer: () => void) {
  const [fichier, setFichier] = useState<File | null>(null)
  const [apercu, setApercu] = useState<ApercuImport | null>(null)
  const [erreur, setErreur] = useState<unknown>(null)
  const [lecture, setLecture] = useState(false)
  const ecriture = useEcriture((f: FormData) =>
    requete<ApercuImport>('/matieres/tableur/appliquer', { methode: 'POST', corps: f }),
  )
  const relire = async (f: File) => {
    setFichier(f)
    setApercu(null)
    setErreur(null)
    setLecture(true)
    try {
      setApercu(await api.envoyerFichier<ApercuImport>('/matieres/tableur/apercu', f, f.name))
    } catch (e) {
      setErreur(e)
    } finally {
      setLecture(false)
    }
  }
  const appliquer = async () => {
    if (!fichier || !apercu) return
    const corps = new FormData()
    corps.append('fichier', fichier, fichier.name)
    corps.append('empreinte_apercu', apercu.empreinte_apercu)
    await ecriture.mutateAsync(corps)
    setApercu(null)
    dire(APPLIQUE)
    onFermer()
  }
  return { fichier, apercu, erreur, lecture, relire, appliquer }
}

/** Le modèle à télécharger et le tableur à relire. */
function Choix({ t }: { t: ReturnType<typeof useTableur> }) {
  const choix = useRef<HTMLInputElement>(null)
  return (
    <div className={styles.rangee}>
      <a className={styles.lien} href={adresseApi('/matieres/tableur')} download>
        Télécharger le modèle (.xlsx)
      </a>
      <input
        ref={choix}
        type="file"
        accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        hidden
        aria-label="Tableur à relire"
        onChange={(e) => {
          const f = e.target.files?.[0]
          e.target.value = ''
          if (f) void t.relire(f)
        }}
      />
      <Bouton
        variante={t.apercu ? 'neutre' : 'principal'}
        occupe={t.lecture}
        attente="Lecture…"
        onClick={() => choix.current?.click()}
      >
        {t.fichier ? 'Choisir un autre tableur…' : 'Choisir le tableur à relire…'}
      </Bouton>
      {t.fichier ? <span className={styles.note}>{t.fichier.name}</span> : null}
    </div>
  )
}

export function Tableur({ onFermer }: { onFermer: () => void }) {
  const t = useTableur(onFermer)
  const a = t.apercu
  return (
    <Fenetre
      titre="Le catalogue par tableur"
      onFermer={onFermer}
      sale={Boolean(a && !a.erreurs && aEcrire(a))}
      taille="large"
      pied={<Pied apercu={a} appliquer={t.appliquer} />}
    >
      <ModeEmploi />
      <Choix t={t} />
      <Erreur erreur={t.erreur} />
      {a ? <Compteurs a={a} /> : null}
      {a ? <VolumesApercu key={a.empreinte_apercu} a={a} /> : null}
    </Fenetre>
  )
}
