/**
 * Retour des machines (`/ordres/:id/retour`, fenêtre sur `/sorties`) : ce qui revient d'un ordre
 * validé, lot par lot, jamais plus que ce qui en est parti (net des retours déjà faits). Créé et
 * validé dans une seule transaction (`POST operations`, `valider: true`). Ce qui le ferait
 * refuser (inventaire en cours, date, dépassement) est dit avant l'envoi ; la saisie est gardée.
 */
import { useState } from 'react'

import { Fenetre, useFermerFenetre } from '../../composants/mise-en-page/Fenetre'
import { Grille } from '../../composants/mise-en-page/Grille'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { dire } from '../../composants/retour/Messages'
import { Note } from '../../composants/retour/Note'
import { Blocages } from '../../composants/saisie/Blocages'
import { Bouton } from '../../composants/saisie/Bouton'
import { Champ } from '../../composants/saisie/Champ'
import { Confirmer } from '../../composants/saisie/Confirmer'
import { DateChamp } from '../../composants/saisie/DateChamp'
import { Quantite } from '../../composants/saisie/Quantite'
import { Saisie } from '../../composants/saisie/Saisie'
import { Selecteur } from '../../composants/saisie/Selecteur'
import { CadreAgrandissable } from '../../composants/tableaux/Cadre'
import { api } from '../../lib/api'
import { date, kg, kgEtMetres } from '../../lib/format'
import { aujourdhui } from '../../lib/heure'
import { useEcriture } from '../../lib/requetes'
import { useSession } from '../../lib/session'
import { toutRendre, type Unite } from '../../lib/unites'
import { useMagasins, useMotifs } from '../stock/donnees'
import styles from '../stock/stock.module.css'
import { estQuarantaine, type OperationFiche } from '../stock/types'
import { useLotsSortis, useOrdre, type LotSorti, type OrdreFiche } from './donnees'

interface SaisieLot {
  kg: number | null
  unite: Unite
}

/** Ce que le serveur refusera, dit avant l'envoi (mots du serveur pour la date, et l'inventaire du lot). */
export function blocagesRetour(
  lots: readonly LotSorti[],
  saisies: Readonly<Record<number, SaisieLot>>,
  jour: string,
  cloture: string | null,
): string[] {
  const raisons: string[] = []
  if (jour > aujourdhui())
    raisons.push(`Date dans le futur (${date(jour)}) : un mouvement se saisit le jour où il a lieu.`)
  if (cloture && jour <= cloture)
    raisons.push(
      `La période jusqu'au ${date(cloture)} est close : rien ne s'y écrit plus. Dater après la clôture, ou demander à la direction de la rouvrir.`,
    )
  const pris = lots.filter((l) => (saisies[l.lot_id]?.kg ?? 0) >= 0.001)
  for (const l of pris) if (l.blocage) raisons.push(`lot ${l.lot} de ${l.reference} : ${l.blocage}`)
  const trop = pris.filter((l) => (saisies[l.lot_id]?.kg ?? 0) > l.sorti_net + 0.0005)
  if (trop.length)
    raisons.push(
      `${trop.length} lot(s) dépassent ce qui est parti : ${trop.map((l) => `${l.lot} (${kg(l.sorti_net)} au plus)`).join(', ')}`,
    )
  return raisons
}

function LigneRetour({
  l,
  x,
  poser,
}: {
  l: LotSorti
  x: SaisieLot
  poser: (id: number, s: SaisieLot) => void
}) {
  const trop = (x.kg ?? 0) > l.sorti_net + 0.0005
  return (
    <tr className={trop ? styles.ligneAlerte : undefined}>
      <td title={l.designation}>{l.reference}</td>
      <td className={styles.mono}>{l.lot}</td>
      <td className={styles.droite}>{kgEtMetres(l.sorti_net, l.kg_par_ml)}</td>
      <td>
        <Quantite
          kg={x.kg}
          onChange={(v) => poser(l.lot_id, { ...x, kg: v })}
          unite={x.unite}
          onUnite={(u) => poser(l.lot_id, { ...x, unite: u })}
          libelle={`Ce qui revient du lot ${l.lot}`}
          poidsBobine={l.poids_bobine}
          bobinesPalette={l.bobines_palette}
          kgParMl={l.kg_par_ml}
          borne={l.sorti_net}
        />
        {trop ? <span className={styles.alerte}>plus que ce qui est parti</span> : null}
      </td>
      <td>
        <button
          type="button"
          className={styles.lien}
          title="Tout ce qui est parti de ce lot"
          onClick={() => poser(l.lot_id, { kg: toutRendre({}, l.sorti_net, 'kg'), unite: 'kg' })}
        >
          tout
        </button>
      </td>
    </tr>
  )
}

function TableRetour({
  lots,
  saisies,
  poser,
}: {
  lots: readonly LotSorti[]
  saisies: Readonly<Record<number, SaisieLot>>
  poser: (id: number, s: SaisieLot) => void
}) {
  return (
    <CadreAgrandissable>
      <table className={styles.tableSimple} aria-label="Ce qui revient, lot par lot">
        <thead>
          <tr>
            <th>Référence</th>
            <th>Lot</th>
            <th className={styles.droite}>Parti (net)</th>
            <th>Revient</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {lots.map((l) => (
            <LigneRetour
              key={l.lot_id}
              l={l}
              x={saisies[l.lot_id] ?? { kg: null, unite: 'kg' }}
              poser={poser}
            />
          ))}
        </tbody>
      </table>
    </CadreAgrandissable>
  )
}

/** L'état de la saisie du retour et son envoi. */
function useRetour(o: OrdreFiche, lots: readonly LotSorti[], onFait: () => void) {
  const { contexte } = useSession()
  const magasins = useMagasins()
  const motifs = useMotifs()
  const [jour, setJour] = useState(aujourdhui())
  const [magasin, setMagasin] = useState<number | null>(o.magasin_id)
  const [motif, setMotif] = useState<number | null>(null)
  const [commentaire, setCommentaire] = useState('')
  const [saisies, setSaisies] = useState<Record<number, SaisieLot>>({})
  const ecrire = useEcriture((corps: unknown) => api.post<OperationFiche>('/operations', corps))
  const listeMotifs = (motifs.data?.motifs ?? []).filter((m) => m.type === 'retour_machine')
  const motifRetenu = motif ?? listeMotifs[0]?.id ?? null
  const pris = lots.filter((l) => (saisies[l.lot_id]?.kg ?? 0) >= 0.001)
  const total = pris.reduce((t, l) => t + (saisies[l.lot_id]?.kg ?? 0), 0)
  const enregistrer = async () => {
    const op = await ecrire.mutateAsync({
      type: 'retour_machine',
      date: jour,
      ordre_id: o.id,
      motif_id: motifRetenu,
      commentaire: commentaire.trim(),
      valider: true,
      lignes: pris.map((l) => ({
        matiere_id: l.matiere_id,
        lot_id: l.lot_id,
        magasin_id: magasin,
        quantite: saisies[l.lot_id]?.kg,
        unite: 'kg',
      })),
    })
    dire(`${op.numero ?? 'Retour'} enregistré : la matière est revenue en stock.`)
    onFait()
  }
  return {
    jour,
    setJour,
    magasin,
    setMagasin,
    motifRetenu,
    setMotif,
    commentaire,
    setCommentaire,
    saisies,
    poser: (id: number, x: SaisieLot) => setSaisies((t) => ({ ...t, [id]: x })),
    magasins: (magasins.data ?? []).filter((g) => g.actif && !estQuarantaine(g.type)),
    code: magasins.data?.find((g) => g.id === magasin)?.code ?? '',
    listeMotifs,
    total,
    sale: pris.length > 0 || commentaire.trim() !== '',
    blocages: blocagesRetour(lots, saisies, jour, contexte.date_cloture),
    manque: [
      ...(pris.length ? [] : ['ce qui revient, lot par lot']),
      ...(motifRetenu ? [] : ['pourquoi la matière revient']),
      ...(magasin ? [] : ['le magasin']),
    ],
    enregistrer,
  }
}

type Retour = ReturnType<typeof useRetour>

function CorpsRetour({ o, lots, f }: { o: OrdreFiche; lots: readonly LotSorti[]; f: Retour }) {
  return (
    <>
      <Blocages blocages={f.blocages} />
      <Grille colonnes={4}>
        <Champ libelle="Date du retour" obligatoire>
          <DateChamp
            valeur={f.jour}
            onChange={f.setJour}
            min={o.date}
            raisonMin="un retour ne se date pas avant son ordre"
          />
        </Champ>
        <Champ libelle="Ranger dans le magasin" obligatoire>
          <Selecteur
            valeur={f.magasin}
            options={f.magasins.map((g) => ({ id: g.id, titre: g.code, sous: g.nom }))}
            onChange={f.setMagasin}
          />
        </Champ>
        <Champ libelle="Pourquoi revient-elle ?" obligatoire>
          <Selecteur
            valeur={f.motifRetenu}
            options={f.listeMotifs.map((m) => ({
              id: m.id,
              titre: m.code_r ? `${m.code_r} · ${m.libelle}` : m.libelle,
            }))}
            onChange={f.setMotif}
          />
        </Champ>
        <Champ libelle="Commentaire">
          <Saisie
            valeur={f.commentaire}
            onChange={f.setCommentaire}
            max={300}
            placeholder="Bobines entamées, arrêt du métier…"
          />
        </Champ>
      </Grille>
      {lots.length ? (
        <TableRetour lots={lots} saisies={f.saisies} poser={f.poser} />
      ) : (
        <Note>Tout ce qui est parti sur cet ordre est déjà revenu.</Note>
      )}
    </>
  )
}

function PiedRetour({ f }: { f: Retour }) {
  const fermer = useFermerFenetre()
  return (
    <>
      <span className={styles.pousse} />
      <Bouton onClick={fermer}>Fermer</Bouton>
      <Confirmer
        variante="principal"
        manque={f.manque}
        blocages={f.blocages}
        question={`Remettre ${kg(f.total)} en stock (${f.code}) ?`}
        oui="Oui, enregistrer le retour"
        titre="Le retour est validé tout de suite : le stock remonte"
        attente="Enregistrement…"
        onOui={f.enregistrer}
      >
        Remettre {kg(f.total)} en stock
      </Confirmer>
    </>
  )
}

function FenetreRetour({
  o,
  lots,
  onFermer,
}: {
  o: OrdreFiche
  lots: readonly LotSorti[]
  onFermer: () => void
}) {
  const f = useRetour(o, lots, onFermer)
  return (
    <Fenetre
      titre={`Retour des machines — ${o.numero ?? ''}`}
      taille="tresLarge"
      sale={f.sale}
      onFermer={onFermer}
      pied={<PiedRetour f={f} />}
    >
      <CorpsRetour o={o} lots={lots} f={f} />
    </Fenetre>
  )
}

export function RetourMachines({ id, onFermer }: { id: number; onFermer: () => void }) {
  const ordre = useOrdre(id)
  const lots = useLotsSortis(id)
  if (ordre.isPending || lots.isPending)
    return (
      <Fenetre titre="Retour des machines" taille="tresLarge" onFermer={onFermer}>
        <Chargement quoi="les lots sortis" />
      </Fenetre>
    )
  if (ordre.isError || lots.isError)
    return (
      <Fenetre titre="Retour des machines" taille="tresLarge" onFermer={onFermer}>
        <Erreur
          erreur={ordre.error ?? lots.error}
          onReessayer={() => void (ordre.refetch(), lots.refetch())}
        />
      </Fenetre>
    )
  return <FenetreRetour o={ordre.data} lots={lots.data} onFermer={onFermer} />
}
