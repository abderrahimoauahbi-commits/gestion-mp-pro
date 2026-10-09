/**
 * Fenêtre du détail d'un contrôle (`/analyse?onglet=controles&controle=Cxx`) : quoi faire, l'écran
 * où corriger, et **toutes** les lignes fautives (route 235, 500 par page, « Charger les 500
 * suivants » ; plus de détail coupé à 200, A2), cherchées au serveur sur tous les mots, sans
 * accents (`?q=`). Chaque cellule qui nomme une fiche l'ouvre.
 */
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router'

import { Fenetre } from '../../../composants/mise-en-page/Fenetre'
import { Badge } from '../../../composants/retour/Badge'
import { Chargement } from '../../../composants/retour/Chargement'
import { Erreur } from '../../../composants/retour/Erreur'
import { Note } from '../../../composants/retour/Note'
import { useListePaginee } from '../../../composants/tableaux/ChargerPlus'
import { DataTable } from '../../../composants/tableaux/DataTable'
import { permis } from '../../../lib/droits'
import { nombre } from '../../../lib/format'
import { useLecture } from '../../../lib/requetes'
import { useSession } from '../../../lib/session'
import styles from '../analyse.module.css'
import type { ControleResume, LigneControle, PageControle } from '../types'
import { colonnesDetail } from './cellules'

/** La valeur après un temps de calme (la recherche part au serveur 300 ms après la frappe). */
export function useApresCalme<T>(valeur: T, delai = 300): T {
  const [calme, setCalme] = useState(valeur)
  useEffect(() => {
    const t = setTimeout(() => setCalme(valeur), delai)
    return () => clearTimeout(t)
  }, [valeur, delai])
  return calme
}

type Ligne = LigneControle & { _rang: number }

interface EnTeteDetailProps {
  gravite: string
  total: number
  lien: string | null
  quoiFaire: string
}

/** La gravité, le nombre de lignes, l'écran où corriger, et quoi faire. */
function EnTeteDetail({ gravite, total, lien, quoiFaire }: EnTeteDetailProps) {
  return (
    <>
      <div className={styles.rangee}>
        {gravite ? <Badge famille="controle" valeur={gravite} /> : null}
        <span className={styles.note}>{`${nombre(total)} ligne(s) à examiner.`}</span>
        <span className={styles.pousse} />
        {lien ? <Link to={lien}>Ouvrir l’écran →</Link> : null}
      </div>
      {quoiFaire ? (
        <Note ton={gravite === 'bloquant' ? 'critique' : 'info'}>
          <strong>Quoi faire :</strong> {quoiFaire}
        </Note>
      ) : null}
    </>
  )
}

export function DetailControle({
  code,
  resume,
  onFermer,
}: {
  code: string
  resume: ControleResume | undefined
  onFermer: () => void
}) {
  const { role } = useSession()
  const [q, setQ] = useState('')
  const cherche = useApresCalme(q.trim())
  const chemin = `/controles/${encodeURIComponent(code)}`
  const tete = useLecture<PageControle>(chemin, { limite: 1 })
  const pages = useListePaginee<LigneControle>(chemin, { q: cherche || undefined })
  const lignes = useMemo<Ligne[]>(() => pages.lignes.map((l, i) => ({ ...l, _rang: i })), [pages.lignes])
  const t = tete.data
  const cols = useMemo(() => colonnesDetail(t?.colonnes ?? resume?.colonnes ?? [], role), [t, resume, role])
  const libelle = t?.libelle ?? resume?.libelle ?? ''
  const lien = t?.lien ?? resume?.lien ?? ''
  const gravite = t?.gravite ?? resume?.gravite ?? ''
  return (
    <Fenetre titre={`${code} — ${libelle}`} taille="tresLarge" onFermer={onFermer}>
      {tete.isError ? <Erreur erreur={tete.error} onReessayer={() => void tete.refetch()} /> : null}
      <EnTeteDetail
        gravite={gravite}
        total={t?.total ?? resume?.lignes_total ?? 0}
        lien={lien && permis(role, lien) ? lien : null}
        quoiFaire={t?.quoi_faire ?? resume?.quoi_faire ?? ''}
      />
      {pages.requete.isPending && !cherche ? <Chargement quoi="les lignes du contrôle" /> : null}
      {pages.requete.isError ? (
        <Erreur erreur={pages.requete.error} onReessayer={() => void pages.requete.refetch()} />
      ) : null}
      {(!pages.requete.isPending || cherche) && !pages.requete.isError ? (
        <DataTable<Ligne>
          libelle={`Lignes du contrôle ${code}`}
          lignes={lignes}
          colonnes={cols}
          cle={(l) => l._rang}
          recherche={{ valeur: q, onChange: setQ }}
          placeholder="Chercher dans les lignes…"
          serveur
          total={pages.total}
          chargerPlus={pages.chargerPlus}
          hauteur="fenetre"
          vide={
            pages.requete.isFetching
              ? 'Recherche…'
              : cols.length
                ? 'Rien ne correspond.'
                : 'Ce contrôle ne détaille pas ses lignes.'
          }
        />
      ) : null}
    </Fenetre>
  )
}
