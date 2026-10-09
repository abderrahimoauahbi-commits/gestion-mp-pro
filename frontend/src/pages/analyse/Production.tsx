/**
 * Analyse › Production (`/analyse?onglet=production`) : le rendement de chaque ordre de
 * fabrication — sorti net (retours déduits) face au prévu par la recette (figé à la validation,
 * perte comprise). Une seule règle d'écart, celle des Sorties (`sorties/ecart.tsx` : 5 % fixes,
 * écrits dans la formule, P8-4). Un clic ouvre l'ordre en fenêtre à adresse stable (`&ordre=ID`),
 * matière par matière. Adresse : `pq` (recherche), `ecarts` (seulement au-delà de 5 %).
 */
import { useMemo } from 'react'
import { Link, useSearchParams } from 'react-router'

import { Carte } from '../../composants/mise-en-page/Carte'
import { Fenetre } from '../../composants/mise-en-page/Fenetre'
import { Indicateurs } from '../../composants/mise-en-page/Indicateurs'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { Kpi } from '../../composants/retour/Kpi'
import { Note } from '../../composants/retour/Note'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { avecParametre } from '../../lib/adresse'
import { formule } from '../../lib/aide'
import { permis } from '../../lib/droits'
import { date, kg, m2, nombre, nombreSigne, part, VIDE } from '../../lib/format'
import { useSession } from '../../lib/session'
import { useEtatListe } from '../catalogue/etatListe'
import { EcartRecette, SEUIL_ECART } from '../sorties/ecart'
import styles from './analyse.module.css'
import { Case, Criteres } from './briques'
import { useConsommation } from './donnees'
import type { ConsommationOrdre, ParMatiere } from './types'

const qualitesDe = (o: ConsommationOrdre) => o.qualites.map((q) => q.qualite).join(', ')
const horsSeuil = (o: ConsommationOrdre) => o.ecart_relatif != null && Math.abs(o.ecart_relatif) > SEUIL_ECART

const COLONNES: readonly Colonne<ConsommationOrdre>[] = [
  {
    cle: 'numero',
    titre: 'Ordre',
    recherche: (o) => [o.commentaire, ...o.lots, ...o.references.map((r) => r.reference)],
    rendu: (o) => (
      <>
        <strong>{o.numero}</strong>
        {o.commentaire ? <span className={styles.dessous}>{o.commentaire}</span> : null}
      </>
    ),
  },
  {
    cle: 'date',
    titre: 'Période',
    rendu: (o) => (o.debut === o.fin ? date(o.debut) : `${date(o.debut)} → ${date(o.fin)}`),
  },
  {
    cle: 'qualite',
    titre: 'Qualité',
    valeur: qualitesDe,
    rendu: (o) => qualitesDe(o) || <span className={styles.note}>hors recette</span>,
  },
  { cle: 'm2', titre: 'Surface (m²)', droite: true, rendu: (o) => (o.m2 ? m2(o.m2) : VIDE) },
  { cle: 'net', titre: 'Sorti net (kg)', droite: true, unite: 'kg', total: true, rendu: (o) => kg(o.net) },
  {
    cle: 'prevu',
    titre: 'Prévu par la recette (kg)',
    droite: true,
    unite: 'kg',
    total: true,
    rendu: (o) => (o.prevu ? kg(o.prevu) : VIDE),
  },
  {
    cle: 'ecart_relatif',
    titre: 'Écart',
    aide: `Signalé au-delà de ${part(SEUIL_ECART, 0)}`,
    droite: true,
    rendu: (o) => <EcartRecette relatif={o.ecart_relatif} />,
  },
  { cle: 'lots', titre: 'Lots', droite: true, valeur: (o) => o.lots.length },
]

function IndicateursProduction({ ordres }: { ordres: readonly ConsommationOrdre[] }) {
  const net = ordres.reduce((s, o) => s + o.net, 0)
  const avecRecette = ordres.filter((o) => o.prevu > 0)
  const sorti = avecRecette.reduce((s, o) => s + o.net, 0)
  const prevu = avecRecette.reduce((s, o) => s + o.prevu, 0)
  const relatif = prevu ? (sorti - prevu) / prevu : null
  const au_dela = avecRecette.filter(horsSeuil).length
  return (
    <Indicateurs libelle="Indicateurs de la production">
      <Kpi
        titre="Sorti net par les ordres"
        valeur={kg(net)}
        detail={`${nombre(ordres.length)} ordre(s) de fabrication, retours déduits`}
        formule={formule('sorti_net')}
      />
      <Kpi
        titre="Sorti face à la recette"
        valeur={relatif == null ? VIDE : `${relatif > 0 ? '+' : ''}${part(relatif)}`}
        ton={relatif == null ? undefined : Math.abs(relatif) <= SEUIL_ECART ? 'ok' : 'attention'}
        detail={`${kg(sorti)} sortis pour ${kg(prevu)} prévus par la recette`}
        formule={formule('ecart_recette')}
      />
      <Kpi
        titre={`Ordres au-delà de ${part(SEUIL_ECART, 0)} d’écart`}
        valeur={`${nombre(au_dela)} sur ${nombre(avecRecette.length)}`}
        ton={au_dela ? 'attention' : 'ok'}
        detail="parmi les ordres qui disent leur qualité"
        formule={formule('production_ordres_ecart')}
      />
    </Indicateurs>
  )
}

const COLONNES_ORDRE: readonly Colonne<ParMatiere>[] = [
  { cle: 'reference', titre: 'Référence' },
  {
    cle: 'quantite',
    titre: 'Sorti net (kg)',
    droite: true,
    unite: 'kg',
    total: true,
    rendu: (r) => kg(r.quantite),
  },
  {
    cle: 'prevu',
    titre: 'Prévu par la recette (kg)',
    droite: true,
    unite: 'kg',
    total: true,
    rendu: (r) => kg(r.prevu),
  },
  {
    cle: 'ecart',
    titre: 'Écart (kg)',
    droite: true,
    rendu: (r) =>
      r.hors_recette ? (
        <span className={styles.note}>hors recette</span>
      ) : r.quantite === 0 && r.prevu > 0 ? (
        <span className={styles.note}>pas sorti</span>
      ) : r.ecart == null ? (
        VIDE
      ) : (
        nombreSigne(r.ecart, 1)
      ),
  },
]

function FenetreOrdre({ o, onFermer }: { o: ConsommationOrdre; onFermer: () => void }) {
  const { role } = useSession()
  const fiche = `/ordres/${o.ordre_id}`
  const suivi = `/tracabilite?ordre=${o.ordre_id}`
  return (
    <Fenetre titre={`Ordre de fabrication ${o.numero}`} taille="large" onFermer={onFermer}>
      <Indicateurs libelle="L’ordre en chiffres">
        <Kpi
          titre="Sorti"
          valeur={kg(o.consomme)}
          detail={o.retours ? `${kg(o.retours)} rendus` : 'aucun retour'}
          formule={formule('sorti_net')}
        />
        <Kpi
          titre="Sorti net"
          valeur={kg(o.net)}
          detail="sorti moins les retours"
          formule={formule('sorti_net')}
        />
        <Kpi
          titre="Prévu par la recette"
          valeur={o.prevu ? kg(o.prevu) : VIDE}
          detail={o.qualites.map((q) => `${q.qualite} : ${m2(q.m2)}`).join(' · ') || 'qualité non précisée'}
          formule={formule('prevu_recette')}
        />
        <Kpi
          titre="Écart"
          valeur={<EcartRecette relatif={o.ecart_relatif} />}
          detail={o.ecart == null ? undefined : `${nombreSigne(o.ecart, 1)} kg`}
          formule={formule('ecart_recette')}
        />
      </Indicateurs>
      <DataTable<ParMatiere>
        libelle={`Matières de l’ordre ${o.numero}`}
        lignes={o.references}
        colonnes={COLONNES_ORDRE}
        cle={(r) => r.matiere_id ?? r.reference}
        recherche={false}
        hauteur="fenetre"
        vide="Aucune matière sortie pour cet ordre."
      />
      <Note>{`Lots utilisés : ${o.lots.length ? o.lots.join(', ') : 'aucun lot nommé'}.`}</Note>
      <div className={styles.rangee}>
        {permis(role, fiche) ? <Link to={fiche}>Ouvrir l’ordre</Link> : null}
        {permis(role, suivi) ? <Link to={suivi}>Traçabilité de l’ordre →</Link> : null}
      </div>
    </Fenetre>
  )
}

export function Production() {
  const lu = useConsommation()
  const [params, setParams] = useSearchParams()
  const etat = useEtatListe('pq', ['ecarts'])
  const ecarts = etat.lire('ecarts') === '1'
  const lignes = useMemo(() => (lu.data ?? []).filter((o) => !ecarts || horsSeuil(o)), [lu.data, ecarts])
  if (lu.isPending) return <Chargement quoi="le rendement des ordres" />
  if (lu.isError) return <Erreur erreur={lu.error} onReessayer={() => void lu.refetch()} />
  const ouvert = lu.data.find((o) => o.ordre_id === Number(params.get('ordre')))
  const ouvrir = (id: number | null) =>
    setParams((p) => avecParametre(p, 'ordre', id == null ? null : String(id)))
  const n = (etat.recherche.valeur.trim() ? 1 : 0) + (ecarts ? 1 : 0)
  return (
    <>
      <IndicateursProduction ordres={lu.data} />
      <Carte
        titre={`Rendement par ordre — ${nombre(lignes.length)} ordre(s)`}
        sous="Cliquer un ordre montre, matière par matière, le sorti net face au prévu par la recette."
        actions={<Link to="/production?onglet=realise">Plan et réalisé par qualité →</Link>}
        serre
        remplir
        className={styles.carteListe}
      >
        <DataTable<ConsommationOrdre>
          libelle="Rendement par ordre"
          lignes={lignes}
          colonnes={COLONNES}
          cle={(o) => o.ordre_id}
          recherche={etat.recherche}
          placeholder="Ordre, qualité, lot, référence… plusieurs mots"
          triInitial={{ cle: 'date', sens: -1 }}
          cliquable={(o) => ouvrir(o.ordre_id)}
          vide="Aucune sortie n’a encore été rattachée à un ordre de fabrication."
          outils={
            <>
              <Case
                valeur={ecarts}
                titre={`Seuil : ${part(SEUIL_ECART, 0)}`}
                onChange={(v) => etat.choix.poser('ecarts', v ? '1' : null)}
              >
                {`seulement les écarts de plus de ${part(SEUIL_ECART, 0)}`}
              </Case>
              <Criteres nombre={n} onEffacer={etat.choix.effacer} />
            </>
          }
        />
      </Carte>
      {ouvert ? <FenetreOrdre o={ouvert} onFermer={() => ouvrir(null)} /> : null}
    </>
  )
}
