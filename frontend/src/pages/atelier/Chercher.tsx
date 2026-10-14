/**
 * Trouver un lot (`/atelier/chercher`), regroupé par fil (`FilsTrouves`) : pour chaque fil, ce
 * qui est en stock (chaque lot, magasin par magasin) et à l'atelier (sur les métiers).
 * La recherche part 250 ms après la frappe, au serveur,
 * sans accents (chaque mot dans la référence, la désignation, le n° de lot, le rôle, le magasin,
 * le fournisseur) ; ou la caméra lit le QR de l'étiquette (`ScanQR`) et ouvre la fiche du lot (un
 * numéro porté par plusieurs lots filtre la liste sur lui).
 * 50 lots, puis « charger les suivants » (an. 18) ; une coupure dit « Pas de réseau » (an. 3).
 */
import { useState } from 'react'
import { useNavigate } from 'react-router'

import { EcranAtelier } from '../../composants/atelier/EcranAtelier'
import { ScanQR } from '../../composants/atelier/ScanQR'
import { Vide } from '../../composants/retour/Vide'
import { Recherche } from '../../composants/tableaux/Recherche'
import { useRechercheAdresse } from '../../lib/adresse'
import { useLecture } from '../../lib/requetes'
import { attente } from './briques'
import { useDiffere, useMetiers } from './commun'
import { BlocFil, grouperParFil } from './FilsTrouves'
import styles from './atelier.module.css'
import { ChargerSuivants, PAGE_ATELIER } from './Ordres'
import type { LotSolde } from './types'

export default function Chercher() {
  const naviguer = useNavigate()
  const [q, setQ] = useRechercheAdresse()
  const mots = useDiffere(q.trim())
  const [nb, setNb] = useState(PAGE_ATELIER)
  const lots = useLecture<LotSolde[]>('/lots', { q: mots, non_nuls: true })
  const metiers = useMetiers()
  const fils = grouperParFil(
    (lots.data ?? []).filter((l) => l.quantite > 0.001),
    metiers.data ?? [],
    mots,
  )
  return (
    <EcranAtelier titre="Trouver un lot" retour="/atelier">
      <div className={styles.pile}>
        <Recherche
          valeur={q}
          onChange={(v) => {
            setQ(v)
            setNb(PAGE_ATELIER)
          }}
          placeholder="Référence, couleur, numéro de lot…"
          libelle="Chercher un lot"
        />
        <ScanQR
          onLot={(id) => void naviguer(`/atelier/lots/${id}`)}
          onPlusieurs={(numero) => {
            setQ(numero)
            setNb(PAGE_ATELIER)
          }}
        />
        {attente([lots, metiers], 'les lots et les métiers') ?? (
          <>
            {!fils.length ? <Vide>Aucun fil en stock ni à l’atelier ne correspond.</Vide> : null}
            {fils.slice(0, nb).map((f) => (
              <BlocFil key={f.matiereId} f={f} />
            ))}
            <ChargerSuivants
              montres={Math.min(nb, fils.length)}
              total={fils.length}
              onCharger={() => setNb(nb + PAGE_ATELIER)}
            />
          </>
        )}
      </div>
    </EcranAtelier>
  )
}
