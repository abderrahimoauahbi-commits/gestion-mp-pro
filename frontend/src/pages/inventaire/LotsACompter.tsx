/**
 * Les volets de la fenêtre de comptage (`?onglet=lots|pieces|historique`) et le volet « Lots à compter »
 * (ECRANS-PRO partie 6) : vues avec leurs compteurs posées sur la rangée des volets, recherche,
 * « Effacer les filtres » et « N critère(s) » dès deux critères (an. 9), tableau de saisie dans son
 * cadre avec pied de totaux, export du comptage (an. 10).
 */
import { useState } from 'react'

import { Historique } from '../../composants/documents/Historique'
import { PiecesJointes } from '../../composants/documents/PiecesJointes'
import { Onglets } from '../../composants/mise-en-page/Onglets'
import { Bouton } from '../../composants/saisie/Bouton'
import { Segments } from '../../composants/saisie/Segments'
import { DataTable } from '../../composants/tableaux/DataTable'
import { useOngletAdresse } from '../../lib/adresse'
import { nombre } from '../../lib/format'
import { useSession } from '../../lib/session'
import { dansLaVue, VUES, type Brouillon, type EtatLigne, type Vue } from './calculComptage'
import styles from './Inventaire.module.css'
import { colonnesComptage } from './LignesComptage'
import type { InventaireFiche, LigneInventaire } from './types'

const VOLETS = ['lots', 'pieces', 'historique'] as const
type Volet = (typeof VOLETS)[number]

export interface VoletsProps {
  fiche: InventaireFiche
  etats: readonly EtatLigne[]
  saisie: boolean
  modifiees: number
  changer: (l: LigneInventaire, modif: Partial<Brouillon>) => void
}

/** Les vues avec leur compteur ; « N critère(s) » et « Effacer les filtres » dès deux critères (an. 9). */
function BarreDesVues(p: {
  etats: readonly EtatLigne[]
  vues: typeof VUES
  active: Vue
  choisir: (v: Vue) => void
  criteres: number
  effacer: () => void
}) {
  return (
    <div className={styles.vues}>
      <Segments
        libelle="Vue"
        valeur={p.active}
        onChange={p.choisir}
        options={p.vues.map((v) => ({
          valeur: v.cle,
          libelle: `${v.libelle} (${nombre(p.etats.filter((e) => dansLaVue(e, v.cle)).length)})`,
        }))}
      />
      {p.criteres >= 2 ? (
        <>
          <span className={styles.note}>{nombre(p.criteres)} critère(s)</span>
          <Bouton taille="petit" variante="fantome" onClick={p.effacer}>
            Effacer les filtres
          </Bouton>
        </>
      ) : null}
    </div>
  )
}

function Lots({ p, vue, q, setQ }: { p: VoletsProps; vue: Vue; q: string; setQ: (q: string) => void }) {
  const { moi } = useSession()
  const { fiche, etats, saisie, changer } = p
  return (
    <DataTable
      libelle="Lots à compter"
      lignes={etats.filter((e) => dansLaVue(e, vue))}
      colonnes={colonnesComptage({
        saisie,
        tousMagasins: fiche.magasin_id == null,
        voitPrix: moi.voit_prix,
        changer,
      })}
      cle={(e) => e.ligne.id}
      recherche={{ valeur: q, onChange: setQ }}
      rechercheCachee={(e) => [e.ligne.magasin]}
      placeholder="Référence, lot, magasin…"
      marquee={(e) => e.modifiee || e.manque}
      hauteur="fenetre"
      exporter={{ route: `/export/inventaires/${fiche.id}` }}
      vide={
        etats.length
          ? 'Aucune ligne dans cette vue.'
          : 'Aucun lot en stock dans ce périmètre : ajouter les lots trouvés.'
      }
    />
  )
}

export function VoletsComptage(p: VoletsProps) {
  const [volet, choisirVolet] = useOngletAdresse<Volet>(VOLETS, 'lots')
  const defaut: Vue = p.fiche.statut === 'ouvert' ? 'toutes' : 'ecarts'
  const [vue, setVue] = useState<Vue | null>(null)
  const [q, setQ] = useState('')
  const active = vue ?? defaut
  const criteres = (q.trim() ? 1 : 0) + (active !== defaut ? 1 : 0)
  return (
    <>
      <Onglets
        libelle="Volets du comptage"
        actif={volet}
        onChange={choisirVolet}
        onglets={[
          { cle: 'lots', libelle: 'Lots à compter', compte: p.fiche.lignes.length, sale: p.modifiees > 0 },
          { cle: 'pieces', libelle: 'Pièces jointes' },
          { cle: 'historique', libelle: 'Historique' },
        ]}
        apres={
          volet === 'lots' ? (
            <BarreDesVues
              etats={p.etats}
              vues={VUES.filter((v) => v.cle !== 'modifiees' || p.saisie)}
              active={active}
              choisir={setVue}
              criteres={criteres}
              effacer={() => {
                setQ('')
                setVue(null)
              }}
            />
          ) : null
        }
      />
      {volet === 'lots' ? (
        <Lots p={p} vue={active} q={q} setQ={setQ} />
      ) : volet === 'pieces' ? (
        <PiecesJointes objet="inventaire" id={p.fiche.id} />
      ) : (
        <Historique objet="inventaire" id={p.fiche.id} />
      )}
    </>
  )
}
