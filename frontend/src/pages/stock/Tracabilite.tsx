/**
 * Suivi de traçabilité (`/tracabilite?lot=|ordre=|matiere=`, fenêtre par-dessus le Stock) : d'un
 * lot, d'où il vient et quels ordres il a servis ; d'un ordre, quelles matières et quels lots sont
 * partis dedans, face au prévu de ses recettes ; d'une matière, tout son chemin. Cliquer un lot, un
 * ordre ou une matière suit la matière de l'autre côté ; le chemin parcouru est dans l'adresse
 * (`depuis`), « ← Revenir au lot N » le remonte, × rend l'écran d'où l'on vient (`retour`).
 */
import { useSearchParams, useNavigate } from 'react-router'

import { Bascule } from '../../composants/mise-en-page/Bascule'
import { Fenetre } from '../../composants/mise-en-page/Fenetre'
import { Indicateurs } from '../../composants/mise-en-page/Indicateurs'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { Kpi } from '../../composants/retour/Kpi'
import { Bouton } from '../../composants/saisie/Bouton'
import { avecParametre } from '../../lib/adresse'
import { formule } from '../../lib/aide'
import { kg, nombre } from '../../lib/format'
import { useLecture } from '../../lib/requetes'
import type { Schema } from '../../lib/types'
import { useMatieres, useTracabilite, type Suivi } from './donnees'
import { adresseSuivi, codeSuivi } from './navigation'
import styles from './stock.module.css'
import { ParMatiere, PasDuSuivi } from './TracabiliteVues'
import type { Tracabilite as Trace } from './types'

type Consommation = Schema<'ConsommationOrdre'>

/** Une étape du chemin parcouru : le suivi et son nom (« lot L-12 », « ordre OF-2026-0004 »). */
export interface Etape {
  suivi: Suivi
  nom: string
}

/** `depuis=lot:12:L-12,ordre:5:OF-2026-0004` (noms encodés) ↔ les étapes. */
export function lireDepuis(texte: string | null): Etape[] {
  return (texte ?? '')
    .split(',')
    .filter(Boolean)
    .flatMap((x) => {
      const [genre = '', id = '', nom = ''] = x.split(':')
      const n = Number(id)
      if (!n) return []
      const suivi: Suivi | null =
        genre === 'lot'
          ? { lot: n }
          : genre === 'ordre'
            ? { ordre: n }
            : genre === 'matiere'
              ? { matiere: n }
              : null
      return suivi ? [{ suivi, nom: decodeURIComponent(nom) }] : []
    })
}

export const ecrireEtape = (e: Etape) => `${codeSuivi(e.suivi)}:${encodeURIComponent(e.nom)}`

/** Le nom d'un suivi, pour le chemin : « lot L-12 », « ordre OF-… », « matière REF ». */
export function nomSuivi(s: Suivi, t: Trace | undefined): string {
  if (s.lot) return `lot ${t?.lot || s.lot}`
  if (s.ordre) return `ordre ${t?.ordre || s.ordre}`
  return `matière ${t?.matiere || s.matiere}`
}

/** « ← Revenir au lot N », « à l'ordre OF-… », « à la matière REF » (P2-17). */
export function libelleRevenir(e: Etape): string {
  if (e.suivi.lot) return `← Revenir au ${e.nom}`
  if (e.suivi.ordre) return `← Revenir à l’${e.nom}`
  return `← Revenir à la ${e.nom}`
}

export function titreSuivi(s: Suivi, t: Trace | undefined): string {
  if (s.lot) return `Traçabilité du lot ${t?.lot ?? ''}`.trim()
  if (s.ordre) return `Ordre de fabrication ${t?.ordre ?? ''}`.trim()
  return `Parcours de la matière ${t?.matiere ?? ''}`.trim()
}

function IndicateursSuivi({ s, t }: { s: Suivi; t: Trace }) {
  return (
    <Indicateurs libelle="Indicateurs du suivi">
      <Kpi
        titre="Entré"
        valeur={kg(t.entrees)}
        detail="hors annulations et transferts"
        formule={formule('trace_entre_sorti')}
      />
      <Kpi
        titre="Sorti"
        valeur={kg(t.sorties)}
        detail="les retours des machines déduits"
        formule={formule('trace_entre_sorti')}
      />
      {s.ordre ? null : (
        <Kpi
          titre="Ordres servis"
          valeur={nombre(t.ordres.length)}
          detail={t.ordres.slice(0, 3).join(' · ')}
          formule={formule('ordres_servis')}
        />
      )}
      {s.lot ? null : (
        <Kpi
          titre={s.ordre ? 'Lots consommés' : 'Lots'}
          valeur={nombre(t.lots.length)}
          detail={t.lots.slice(0, 3).join(' · ')}
          formule={formule('trace_lots')}
        />
      )}
      {s.ordre ? (
        <Kpi
          titre="Matières"
          valeur={nombre(t.references.length)}
          detail={t.references.slice(0, 3).join(' · ')}
          formule={formule('trace_lots')}
        />
      ) : (
        <Kpi
          titre="Reste"
          valeur={kg(t.entrees - t.sorties)}
          detail={s.lot ? t.references.join(' · ') : 'entré − sorti'}
          formule={formule('trace_entre_sorti')}
        />
      )}
    </Indicateurs>
  )
}

/** « ← Revenir au … », le chemin parcouru, « Ouvrir l'ordre », « Fiche du lot ». */
function PiedSuivi({
  suivi,
  t,
  depuis,
  retour,
}: {
  suivi: Suivi
  t: Trace | undefined
  depuis: readonly Etape[]
  retour?: string
}) {
  const navigate = useNavigate()
  const precedent = depuis[depuis.length - 1]
  return (
    <>
      {precedent ? (
        <Bouton
          onClick={() =>
            navigate(adresseSuivi(precedent.suivi, retour, depuis.slice(0, -1).map(ecrireEtape)))
          }
        >
          {libelleRevenir(precedent)}
        </Bouton>
      ) : null}
      {depuis.length ? (
        <span className={styles.note}>
          Chemin : {[...depuis.map((e) => e.nom), nomSuivi(suivi, t)].join(' → ')}
        </span>
      ) : null}
      <span className={styles.pousse} />
      {suivi.ordre ? (
        <Bouton
          titre="L’ordre de fabrication, ses lots et ses retours"
          onClick={() => navigate(`/ordres/${suivi.ordre}`)}
        >
          Ouvrir l’ordre
        </Bouton>
      ) : null}
      {suivi.lot ? (
        <Bouton titre="La fiche du lot" onClick={() => navigate(`/lots/${suivi.lot}`)}>
          Fiche du lot
        </Bouton>
      ) : null}
    </>
  )
}

/** Ce que le suivi lit, et « suivre » de l'autre côté (le chemin s'allonge dans l'adresse). */
function useSuivi(suivi: Suivi) {
  const [params, setParams] = useSearchParams()
  const navigate = useNavigate()
  const trace = useTracabilite(suivi)
  const matieres = useMatieres()
  const ordres = useLecture<Consommation[]>('/ordres/consommation')
  const retour = params.get('retour') ?? undefined
  const depuis = lireDepuis(params.get('depuis'))
  const t = trace.data
  const ordre = suivi.ordre ? ordres.data?.find((o) => o.ordre_id === suivi.ordre) : undefined
  return {
    trace,
    t,
    ordre,
    retour,
    depuis,
    vue: ordre?.qualites.length && params.get('tvue') !== 'mouvements' ? 'matieres' : 'mouvements',
    choisirVue: (v: string) =>
      setParams((p) => avecParametre(p, 'tvue', v === 'matieres' ? null : v), { replace: true }),
    suivre: (s: Suivi) =>
      navigate(
        adresseSuivi(s, retour, [
          ...depuis.map(ecrireEtape),
          ecrireEtape({ suivi, nom: nomSuivi(suivi, t) }),
        ]),
      ),
    fermer: () => navigate(retour ?? '/stock?onglet=ordres'),
    idMatiere: new Map((matieres.data ?? []).map((m) => [m.reference, m.id])),
    idOrdre: new Map((ordres.data ?? []).map((o) => [o.numero, o.ordre_id])),
  }
}

export function Tracabilite({ suivi }: { suivi: Suivi }) {
  const x = useSuivi(suivi)
  const { t, ordre } = x
  return (
    <Fenetre
      titre={titreSuivi(suivi, t)}
      taille="tresLarge"
      onFermer={x.fermer}
      pied={<PiedSuivi suivi={suivi} t={t} depuis={x.depuis} retour={x.retour} />}
    >
      {x.trace.isPending ? <Chargement quoi="la traçabilité" /> : null}
      {x.trace.isError ? <Erreur erreur={x.trace.error} onReessayer={() => void x.trace.refetch()} /> : null}
      {t ? (
        <>
          <IndicateursSuivi s={suivi} t={t} />
          {ordre?.qualites.length ? (
            <Bascule
              vues={[
                { cle: 'matieres', libelle: `Prévu et sorti, par matière (${ordre.references.length})` },
                { cle: 'mouvements', libelle: `Mouvements (${t.mouvements.length})` },
              ]}
              valeur={x.vue}
              onChange={x.choisirVue}
              libelle="Vue du suivi"
            />
          ) : null}
          {ordre && x.vue === 'matieres' ? (
            <ParMatiere ordre={ordre} onSuivre={x.suivre} idMatiere={x.idMatiere} />
          ) : (
            <PasDuSuivi t={t} suivi={suivi} onSuivre={x.suivre} idMatiere={x.idMatiere} idOrdre={x.idOrdre} />
          )}
        </>
      ) : null}
    </Fenetre>
  )
}
