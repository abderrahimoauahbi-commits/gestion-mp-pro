/**
 * La fiche matière en fenêtre par-dessus la liste (`/matieres/:id`, `/matieres/nouvelle`), à
 * onglets (`?onglet=classification|achat|conditionnement|pieces|historique`). Direction et
 * achats l'écrivent ; l'alimentation la lit sans rien de l'achat (R10). La saisie n'est jamais
 * perdue sans question (R4) ; une version périmée se recharge (R2).
 */
import { useMemo } from 'react'
import { Link, useSearchParams } from 'react-router'

import { Historique } from '../../composants/documents/Historique'
import { PiecesJointes } from '../../composants/documents/PiecesJointes'
import { Fenetre } from '../../composants/mise-en-page/Fenetre'
import { Onglets } from '../../composants/mise-en-page/Onglets'
import { Badge } from '../../composants/retour/Badge'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { Note } from '../../composants/retour/Note'
import { useOngletAdresse } from '../../lib/adresse'
import { horodatage, kgEtMetres } from '../../lib/format'
import styles from './catalogue.module.css'
import { BandeauConflit } from './Conflit'
import {
  useClassification,
  useCodesDouaniers,
  useDevises,
  useFournisseurs,
  useMatiere,
  useMatieres,
} from './donnees'
import { VoletLectureClassification, VoletLectureConditionnement } from './FicheMatiereLecture'
import { manques, nomVolet, type DefautsCreation, type Volet } from './formeMatiere'
import { PiedMatiere } from './PiedMatiere'
import { estComplet, LISTES, type Classification, type Matiere, type MatiereFiche } from './types'
import { useFicheMatiere, type FicheMatiereEtat } from './useFicheMatiere'
import { useReferenceComposee, type ReferenceComposee } from './useReference'
import { VoletAchat } from './VoletAchat'
import { VoletClassification } from './VoletClassification'
import { VoletConditionnement } from './VoletConditionnement'

export interface FicheMatiereProps {
  id: number | null
  ecrit: boolean
  onFermer: () => void
  onCree: (id: number) => void
}

/** Les défauts d'une création : les filtres posés sur la liste (rôle, classification, fournisseur). */
function useDefauts(c: Classification | undefined): DefautsCreation {
  const [params] = useSearchParams()
  return useMemo(() => {
    const parCode = (i: number, code: string | null) =>
      c?.[LISTES[i]?.cle ?? 'compositions'].find((v) => v.code === code)?.id
    const nombre = (cle: string) => Number(params.get(cle)) || null
    return {
      role_id: nombre('role'),
      fournisseur_id: nombre('fournisseur'),
      composition_id: parCode(0, params.get('composition')),
      type_fil_id: parCode(1, params.get('type')),
      titrage_id: parCode(2, params.get('titrage')),
      couleur_id: parCode(3, params.get('couleur')),
    }
  }, [c, params])
}

/** « 1 234,0 kg ≈ 1 020 ml en stock · modifiée le … par Nadia » et les liens vers le stock. */
function Bandeau({ m }: { m: MatiereFiche }) {
  return (
    <div className={styles.rangee}>
      <span className={styles.note}>
        {kgEtMetres(m.stock, m.lineaire ? m.kg_par_ml : null)} en stock
        {m.modifie_le || m.modifie_par ? ' · modifiée' : ''}
        {m.modifie_le ? ` le ${horodatage(m.modifie_le)}` : ''}
        {m.modifie_par ? ` par ${m.modifie_par}` : ''}
      </span>
      <span className={styles.pousse} />
      <Link className={styles.lien} to={`/stock?onglet=lots&matiere=${m.id}`}>
        Voir ses lots
      </Link>
      <Link className={styles.lien} to={`/stock?onglet=mouvements&matiere=${m.id}`}>
        Ses mouvements de stock
      </Link>
    </div>
  )
}

function Titre({ m }: { m: MatiereFiche | null }) {
  if (!m) return <>Nouvelle matière</>
  return (
    <>
      {m.reference} {m.actif ? null : <Badge ton="neutre">désactivée</Badge>}
    </>
  )
}

/** Le volet ouvert de la fiche écrite. */
function CorpsVolet({
  volet,
  f,
  c,
  composee,
  doublon,
  groupes,
}: {
  volet: Volet
  f: FicheMatiereEtat
  c: Classification
  composee: ReferenceComposee | null
  doublon: boolean
  groupes: readonly string[]
}) {
  const fournisseurs = useFournisseurs()
  const devises = useDevises(true)
  const codes = useCodesDouaniers(true)
  return (
    <>
      {volet === 'classification' ? (
        <VoletClassification
          forme={f.forme}
          maj={f.maj}
          c={c}
          composee={composee}
          libre={f.libre}
          onRetouche={f.retoucher}
          doublon={doublon}
        />
      ) : null}
      {volet === 'achat' ? (
        <VoletAchat
          forme={f.forme}
          maj={f.maj}
          c={c}
          fournisseurs={(fournisseurs.data ?? []).filter(estComplet)}
          devises={devises.data ?? []}
          codes={codes.isError ? null : (codes.data ?? [])}
          creation={!f.base}
        />
      ) : null}
      {volet === 'conditionnement' ? (
        <VoletConditionnement forme={f.forme} maj={f.maj} groupes={groupes} />
      ) : null}
      {volet === 'pieces' && f.base ? <PiecesJointes objet="matiere" id={f.base.id} /> : null}
      {volet === 'historique' && f.base ? <Historique objet="matiere" id={f.base.id} /> : null}
    </>
  )
}

function FicheEcrite({
  fiche,
  c,
  matieres,
  onFermer,
  onCree,
}: FicheMatiereProps & { fiche: MatiereFiche | null; c: Classification; matieres: readonly Matiere[] }) {
  const defauts = useDefauts(c)
  const f = useFicheMatiere({ fiche, c, defauts, onCree, onSupprimee: onFermer })
  const composee = useReferenceComposee(f.forme, f.libre, (r) =>
    f.maj({ reference: r.reference, designation: r.designation || f.forme.designation }),
  )
  const volets: Volet[] = f.base
    ? ['classification', 'achat', 'conditionnement', 'pieces', 'historique']
    : ['classification', 'achat', 'conditionnement']
  const [volet, choisir] = useOngletAdresse(volets, 'classification')
  const manque = manques(f.forme, c)
  const reference = f.forme.reference.trim().toLowerCase()
  const doublon =
    Boolean(reference) && matieres.some((m) => m.reference.toLowerCase() === reference && m.id !== f.base?.id)
  const groupes = useMemo(
    () => [...new Set(matieres.map((m) => m.groupe_equiv).filter(Boolean))].sort(),
    [matieres],
  )
  return (
    <Fenetre
      titre={<Titre m={f.base} />}
      onFermer={onFermer}
      sale={f.sale}
      taille="large"
      pied={<PiedMatiere f={f} manque={manque} doublon={doublon} />}
    >
      {f.base ? (
        <Bandeau m={f.base} />
      ) : (
        <Note>
          Choisir d’abord la classification : la référence et la désignation s’écrivent seules, à la manière
          du catalogue. Une valeur qui manque s’ajoute sur place. On peut ensuite retoucher la référence.
        </Note>
      )}
      <BandeauConflit message={f.conflit} onRecharger={f.recharger} />
      <Onglets<Volet>
        libelle="Volets de la fiche"
        actif={volet}
        onChange={choisir}
        onglets={volets.map((v) => ({
          cle: v,
          libelle: manque.some((x) => x.volet === v) ? `${nomVolet(v)} !` : nomVolet(v),
        }))}
      />
      <CorpsVolet volet={volet} f={f} c={c} composee={composee} doublon={doublon} groupes={groupes} />
    </Fenetre>
  )
}

function Lecture({ m, onFermer }: { m: MatiereFiche; onFermer: () => void }) {
  const volets = ['classification', 'conditionnement', 'historique'] as const
  const [volet, choisir] = useOngletAdresse(volets, 'classification')
  return (
    <Fenetre titre={<Titre m={m} />} onFermer={onFermer} taille="large">
      <Bandeau m={m} />
      <Onglets
        libelle="Volets de la fiche"
        actif={volet}
        onChange={choisir}
        onglets={volets.map((v) => ({ cle: v, libelle: nomVolet(v) }))}
      />
      {volet === 'classification' ? <VoletLectureClassification m={m} /> : null}
      {volet === 'conditionnement' ? <VoletLectureConditionnement m={m} /> : null}
      {volet === 'historique' ? <Historique objet="matiere" id={m.id} /> : null}
    </Fenetre>
  )
}

export function FicheMatiere(props: FicheMatiereProps) {
  const fiche = useMatiere(props.id)
  const c = useClassification(props.ecrit)
  const matieres = useMatieres()
  const lectures = [fiche, c, matieres].filter((l) => l.fetchStatus !== 'idle' || l.data)
  const echec = lectures.find((l) => l.isError)
  if (echec)
    return (
      <Fenetre titre="Fiche matière" onFermer={props.onFermer}>
        <Erreur erreur={echec.error} onReessayer={() => void echec.refetch()} />
      </Fenetre>
    )
  const prete = (props.id == null || fiche.data) && matieres.data && (!props.ecrit || c.data)
  if (!prete)
    return (
      <Fenetre titre="Fiche matière" onFermer={props.onFermer}>
        <Chargement quoi="la fiche" />
      </Fenetre>
    )
  if (!props.ecrit && fiche.data) return <Lecture m={fiche.data} onFermer={props.onFermer} />
  if (!c.data || !matieres.data) return null
  return (
    <FicheEcrite
      key={fiche.data?.id ?? 'nouvelle'}
      {...props}
      fiche={fiche.data ?? null}
      c={c.data}
      matieres={matieres.data}
    />
  )
}
