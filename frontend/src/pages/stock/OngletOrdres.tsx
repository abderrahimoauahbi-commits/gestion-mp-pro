/**
 * Stock › Ordres de fabrication (`/stock?onglet=ordres`) : ce que chaque ordre validé a consommé,
 * net des retours, face au prévu de sa recette (perte figée à la validation), avec quelles matières
 * et quels lots. Recherche, période (un ordre est gardé s'il chevauche la période), export ; une
 * ligne ou « Suivre » ouvre la traçabilité de l'ordre.
 */
import { useMemo } from 'react'

import { LienDocument } from '../../composants/documents/LienDocument'
import { Carte } from '../../composants/mise-en-page/Carte'
import { Indicateurs } from '../../composants/mise-en-page/Indicateurs'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { Kpi } from '../../composants/retour/Kpi'
import { Bouton } from '../../composants/saisie/Bouton'
import { champsCherches, type Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { useEtatTableAdresse } from '../../composants/tableaux/etatAdresse'
import { ExportExcel } from '../../composants/tableaux/ExportExcel'
import { trouve } from '../../composants/tableaux/filtrage'
import { formule } from '../../lib/aide'
import { date, kg, nombre, VIDE } from '../../lib/format'
import { useLecture } from '../../lib/requetes'
import type { Schema } from '../../lib/types'
import { EcartRecette, ecartRelatif, tonEcart } from '../sorties/ecart'
import { Double, Kg, Liste } from './cellules'
import type { Suivi } from './donnees'
import { Periode } from './Periode'
import styles from './stock.module.css'

type Consommation = Schema<'ConsommationOrdre'>

/** La période de l'onglet (`?debut=&fin=`, distincte de celle des mouvements). */
export const CLES_ORDRES = ['debut', 'fin'] as const

const fabrication = (o: Consommation) =>
  o.qualites.length ? o.qualites.map((q) => `${q.qualite} · ${nombre(q.m2)} m²`).join(', ') : 'hors recette'

function Numero({ o }: { o: Consommation }) {
  return (
    <span className={styles.mono} onClick={(e) => e.stopPropagation()}>
      <LienDocument genre="ordre" id={o.ordre_id} numero={o.numero} />
    </span>
  )
}

const COLONNES: Colonne<Consommation>[] = [
  {
    cle: 'numero',
    titre: 'Ordre',
    valeur: (o) => o.numero,
    recherche: (o) => [o.commentaire, ...o.lots, ...o.references.map((r) => r.reference)],
    rendu: (o) => <Numero o={o} />,
  },
  {
    cle: 'date',
    titre: 'Date',
    valeur: (o) => o.debut,
    rendu: (o) => <Double haut={date(o.debut)} bas={o.debut !== o.fin ? `→ ${date(o.fin)}` : undefined} />,
  },
  {
    cle: 'fabrication',
    titre: 'Fabrication',
    valeur: fabrication,
    rendu: (o) => <Double haut={fabrication(o)} bas={o.commentaire} />,
  },
  {
    cle: 'prevu',
    titre: 'Prévu par la recette (kg)',
    droite: true,
    unite: 'kg',
    total: true,
    valeur: (o) => o.prevu || null,
    rendu: (o) => (o.prevu ? nombre(o.prevu, 1) : <span className={styles.nul}>{VIDE}</span>),
  },
  {
    cle: 'net',
    titre: 'Sorti net (kg)',
    droite: true,
    unite: 'kg',
    total: true,
    valeur: (o) => o.net,
    rendu: (o) => (
      <Double
        haut={<Kg v={o.net} />}
        bas={o.retours ? `dont ${nombre(o.retours, 0, 2)} revenus` : undefined}
      />
    ),
  },
  {
    cle: 'ecart',
    titre: 'Écart',
    droite: true,
    valeur: (o) => o.ecart_relatif ?? null,
    rendu: (o) => <EcartRecette relatif={o.ecart_relatif} />,
  },
  {
    cle: 'matieres',
    titre: 'Matières',
    triable: false,
    rendu: (o) => (
      <Liste valeurs={o.references.filter((r) => r.quantite).map((r) => r.reference)} nom="matières" />
    ),
  },
  {
    cle: 'lots',
    titre: 'Lots',
    triable: false,
    rendu: (o) => <Liste valeurs={o.lots} nom="lots" vide="— sans lot" />,
  },
]

function colonneSuivre(onSuivre: (s: Suivi) => void): Colonne<Consommation> {
  return {
    cle: 'suivre',
    titre: '',
    triable: false,
    exporte: false,
    rendu: (o) => (
      <span onClick={(e) => e.stopPropagation()}>
        <Bouton
          taille="petit"
          titre="Quelles matières et quels lots sont partis dans cet ordre"
          onClick={() => onSuivre({ ordre: o.ordre_id })}
        >
          Suivre
        </Bouton>
      </span>
    ),
  }
}

/** Un ordre est gardé s'il chevauche la période (fin après le début, début avant la fin). */
const dansPeriode = (o: Consommation, du?: string, au?: string) =>
  (!du || o.fin >= du) && (!au || o.debut <= au)

function IndicateursOrdres({ lignes, total }: { lignes: readonly Consommation[]; total: number }) {
  const net = lignes.reduce((t, o) => t + o.net, 0)
  const revenus = lignes.reduce((t, o) => t + o.retours, 0)
  const avecRecette = lignes.filter((o) => o.prevu)
  const prevu = avecRecette.reduce((t, o) => t + o.prevu, 0)
  const sortiRecette = avecRecette.reduce((t, o) => t + o.net, 0)
  const relatif = ecartRelatif(sortiRecette, prevu)
  return (
    <Indicateurs>
      <Kpi
        titre="Ordres de fabrication"
        valeur={nombre(lignes.length)}
        detail={`sur ${nombre(total)}`}
        formule={formule('ordres_valides')}
      />
      <Kpi
        titre="Sorti net"
        valeur={kg(net)}
        detail={revenus ? `${kg(revenus)} revenus, déduits` : 'aucun retour'}
        formule={formule('sorti_net')}
      />
      <Kpi
        titre="Prévu par la recette"
        valeur={kg(prevu)}
        detail={`${avecRecette.length} ordre(s) selon recette`}
        formule={formule('prevu_recette')}
      />
      <Kpi
        titre="Écart"
        valeur={<EcartRecette relatif={relatif} />}
        detail={prevu ? `${kg(sortiRecette)} sortis pour ${kg(prevu)} prévus` : undefined}
        ton={tonEcart(relatif)}
        formule={formule('ecart_recette')}
      />
    </Indicateurs>
  )
}

export function OngletOrdres({ onSuivre }: { onSuivre: (s: Suivi) => void }) {
  const ordres = useLecture<Consommation[]>('/ordres/consommation')
  const table = useEtatTableAdresse(CLES_ORDRES)
  const { debut, fin } = table.choix.valeurs
  const colonnes = useMemo(() => [...COLONNES, colonneSuivre(onSuivre)], [onSuivre])
  const toutes = ordres.data ?? []
  const periode = toutes.filter((o) => dansPeriode(o, debut, fin))
  const lignes = periode.filter((o) => trouve(champsCherches(colonnes, o), table.recherche.valeur))
  if (ordres.isPending) return <Chargement quoi="les ordres de fabrication" />
  if (ordres.isError) return <Erreur erreur={ordres.error} onReessayer={() => void ordres.refetch()} />
  return (
    <>
      <IndicateursOrdres lignes={lignes} total={toutes.length} />
      <Carte
        titre="Ordres de fabrication"
        sous="Le plus récent d’abord · « Suivre » : quelles matières et quels lots sont partis dans l’ordre"
        actions={
          <ExportExcel
            route="/export/ordres"
            parametres={{
              vue: 'consommation',
              du: debut,
              au: fin,
              q: table.recherche.valeur.trim() || undefined,
            }}
          />
        }
        serre
        remplir
        className={styles.carteListe}
      >
        <DataTable<Consommation>
          libelle="Ordres de fabrication"
          lignes={periode}
          colonnes={colonnes}
          cle={(o) => o.ordre_id}
          recherche={table.recherche}
          choix={table.choix}
          placeholder="Un ordre, une qualité, une référence, un lot… plusieurs mots affinent"
          cliquable={(o) => onSuivre({ ordre: o.ordre_id })}
          vide={toutes.length ? 'Aucun ordre ne correspond.' : 'Aucun ordre de fabrication validé.'}
          outils={<Periode choix={table.choix} du="debut" au="fin" />}
        />
      </Carte>
    </>
  )
}
