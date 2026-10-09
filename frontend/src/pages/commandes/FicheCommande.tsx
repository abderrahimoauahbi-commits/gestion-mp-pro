/**
 * La fiche d'un bon en fenêtre (`/commandes/:id?onglet=lignes|prix|expedition|receptions|
 * approbation|pieces|historique`, ECRANS-PRO 4.7–4.14) : en-tête, indicateurs, bandeaux, sept
 * volets et les gestes du bon. Relue au retour sur l'onglet et après chaque geste, sans écraser
 * une saisie en cours ; fermer avec une saisie en cours demande d'abord.
 */
import { useState } from 'react'
import { useNavigate } from 'react-router'

import { Historique } from '../../composants/documents/Historique'
import { PiecesJointes } from '../../composants/documents/PiecesJointes'
import { Fenetre } from '../../composants/mise-en-page/Fenetre'
import { Onglets } from '../../composants/mise-en-page/Onglets'
import { Badge } from '../../composants/retour/Badge'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { Vide } from '../../composants/retour/Vide'
import { useOngletAdresse } from '../../lib/adresse'
import { nombre } from '../../lib/format'
import { useSession } from '../../lib/session'
import { BandeauConflit } from '../catalogue/Conflit'
import styles from '../plan-achat/achats.module.css'
import { useMatieresDuFournisseur } from '../plan-achat/donnees'
import { adresseMatiere, lienSi } from '../plan-achat/liens'
import { useCommande } from './donnees'
import { BandeauxCommande, IndicateursCommande, quiQuand } from './EnTeteCommande'
import { versFormeLignes } from './formeLignes'
import { GestesCommande } from './GestesCommande'
import { SauverVolet, type Formes } from './SauverVolet'
import type { CommandeFiche } from './types'
import { memeForme, useFormeFiche } from './useFormeFiche'
import { versFormeExpedition, VoletExpedition } from './VoletExpedition'
import { VoletLignes } from './VoletLignes'
import { VoletApprobation, VoletReceptions } from './VoletsLecture'
import { versFormePrix, VoletPrix } from './VoletPrix'

const VOLETS = ['lignes', 'prix', 'expedition', 'receptions', 'approbation', 'pieces', 'historique'] as const
type Volet = (typeof VOLETS)[number]

function Titre({ c }: { c: CommandeFiche }) {
  return (
    <span className={styles.rangeeCentree}>
      {c.numero ? `Bon de commande ${c.numero} — ${c.fournisseur}` : `Bon de commande — ${c.fournisseur}`}
      <Badge famille="commande" valeur={c.statut} />
      {c.parti ? <Badge famille="livraison" valeur={c.livraison} /> : null}
    </span>
  )
}

function useFormes(c: CommandeFiche): Formes {
  return {
    lignes: useFormeFiche(c, versFormeLignes, memeForme),
    prix: useFormeFiche(c, versFormePrix, memeForme),
    expedition: useFormeFiche(c, versFormeExpedition, memeForme),
  }
}

function Volets({ volet, c, f }: { volet: Volet; c: CommandeFiche; f: Formes }) {
  const { role } = useSession()
  const navigate = useNavigate()
  const matieres = useMatieresDuFournisseur(c.fournisseur_id)
  const parId = new Map((matieres.data ?? []).map((m) => [m.id, m]))
  const memeDevise = (matieres.data ?? []).filter((m) => m.devise === c.devise)
  if (volet === 'lignes')
    return (
      <VoletLignes
        c={c}
        f={f.lignes}
        matieres={parId}
        ajoutables={memeDevise}
        lien={(id) => lienSi(role, adresseMatiere(id))}
      />
    )
  if (volet === 'prix') return <VoletPrix c={c} f={f.prix} />
  if (volet === 'expedition') return <VoletExpedition c={c} f={f.expedition} />
  if (volet === 'receptions')
    return <VoletReceptions c={c} onOuvrir={(id) => navigate(`/receptions/${id}`)} />
  if (volet === 'approbation') return <VoletApprobation c={c} />
  if (volet === 'pieces') return <PiecesJointes objet="commande" id={c.id} />
  return <Historique objet="commande" id={c.id} />
}

/** Les volets du bon ; « Approbation » n'apparaît qu'avec une décision. */
function OngletsBon({
  c,
  f,
  volet,
  choisir,
}: {
  c: CommandeFiche
  f: Formes
  volet: Volet
  choisir: (v: Volet) => void
}) {
  const aSaisir = c.lignes.filter((l) => !l.prix_confirme).length
  return (
    <Onglets<Volet>
      libelle="Volets du bon"
      actif={volet}
      onChange={choisir}
      onglets={[
        { cle: 'lignes', libelle: 'Lignes et livraison', compte: c.nb_lignes, sale: f.lignes.sale },
        {
          cle: 'prix',
          libelle:
            aSaisir && c.parti ? `Prix du fournisseur (${nombre(aSaisir)} à saisir)` : 'Prix du fournisseur',
          court: 'Prix',
          sale: f.prix.sale,
        },
        {
          cle: 'expedition',
          libelle: 'Suivi de l’expédition',
          court: 'Expédition',
          sale: f.expedition.sale,
        },
        { cle: 'receptions', libelle: 'Réceptions', compte: c.receptions.length },
        ...(c.decisions.length
          ? [{ cle: 'approbation' as const, libelle: 'Approbation', compte: c.decisions.length }]
          : []),
        { cle: 'pieces', libelle: 'Pièces jointes', court: 'Pièces' },
        { cle: 'historique', libelle: 'Historique' },
      ]}
    />
  )
}

function Ecrite({
  c,
  onFermer,
  recharger,
}: {
  c: CommandeFiche
  onFermer: () => void
  recharger: () => Promise<CommandeFiche | undefined>
}) {
  const { role } = useSession()
  const navigate = useNavigate()
  const f = useFormes(c)
  const [conflit, setConflit] = useState<string | null>(null)
  const permis: Volet[] = VOLETS.filter((v) => v !== 'approbation' || c.decisions.length > 0)
  const [volet, choisir] = useOngletAdresse<Volet>(permis, 'lignes')
  const sale = f.lignes.sale || f.prix.sale || f.expedition.sale
  return (
    <Fenetre
      titre={<Titre c={c} />}
      sous={quiQuand(c)}
      taille="tresLarge"
      sale={sale}
      onFermer={onFermer}
      pied={
        <div className={styles.pied}>
          <SauverVolet volet={volet} c={c} f={f} onConflit={setConflit} />
          <span className={styles.pousse} />
          <GestesCommande c={c} sale={sale} onSupprime={() => navigate('/commandes?onglet=brouillon')} />
        </div>
      }
    >
      <IndicateursCommande c={c} />
      <BandeauxCommande c={c} role={role} />
      <BandeauConflit
        message={conflit}
        onRecharger={async () => {
          const r = await recharger()
          if (r) for (const x of [f.lignes, f.prix, f.expedition]) x.repartir(r)
          setConflit(null)
        }}
      />
      <OngletsBon c={c} f={f} volet={volet} choisir={choisir} />
      <Volets volet={volet} c={c} f={f} />
    </Fenetre>
  )
}

export function FicheCommande({ id, onFermer }: { id: number; onFermer: () => void }) {
  const lu = useCommande(id)
  if (lu.data)
    return <Ecrite c={lu.data} onFermer={onFermer} recharger={async () => (await lu.refetch()).data} />
  return (
    <Fenetre titre="Bon de commande" onFermer={onFermer} taille="tresLarge">
      {lu.isError && lu.error.statut === 404 ? <Vide>Ce bon n’existe plus.</Vide> : null}
      {lu.isError && lu.error.statut !== 404 ? (
        <Erreur erreur={lu.error} onReessayer={() => void lu.refetch()} />
      ) : null}
      {lu.isPending ? <Chargement quoi="le bon de commande" /> : null}
    </Fenetre>
  )
}
