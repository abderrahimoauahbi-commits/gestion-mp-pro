/**
 * La ligne d'ajout d'un frais (ECRANS-PRO 5.9, « la ligne bleue ») : poste (le premier par défaut),
 * montant (un avoir en négatif), « Porte sur » (tout le dossier, ou une marchandise), répartition
 * qui en découle, prestataire, pièce, dates, observations ; « Ajouter » grisé avec ce qui manque,
 * « Effacer ». Le brouillon vit dans la fiche : il survit au changement d'onglet et rend la fenêtre
 * « sale » tant qu'il n'est pas ajouté ou effacé.
 */
import { dire } from '../../composants/retour/Messages'
import { Bouton } from '../../composants/saisie/Bouton'
import { Champ } from '../../composants/saisie/Champ'
import { DateChamp } from '../../composants/saisie/DateChamp'
import { Nombre } from '../../composants/saisie/Nombre'
import { Saisie } from '../../composants/saisie/Saisie'
import { Selecteur, type OptionSelecteur } from '../../composants/saisie/Selecteur'
import styles from './Importations.module.css'
import type { DossierFiche, PosteFiche } from './types'
import type { GestesDossier } from './useDossier'

export interface BrouillonFrais {
  poste_id: number | null
  montant: number | null
  ligne_id: number | null
  prestataire: string
  piece: string
  date_piece: string
  echeance: string
  commentaire: string
}

export const FRAIS_VIDE: BrouillonFrais = {
  poste_id: null,
  montant: null,
  ligne_id: null,
  prestataire: '',
  piece: '',
  date_piece: '',
  echeance: '',
  commentaire: '',
}

/** Un brouillon commencé (le poste seul, choisi d'office, ne compte pas). */
export const fraisCommence = (b: BrouillonFrais) =>
  b.montant != null ||
  b.ligne_id != null ||
  [b.prestataire, b.piece, b.date_piece, b.echeance, b.commentaire].some((x) => x.trim())

/** « Droits de douane — à la valeur » : le poste et ce qu'il fait au coût. */
export function optionsPostes(postes: readonly PosteFiche[]): OptionSelecteur<number>[] {
  return postes.map((p) => ({
    id: p.id,
    titre: `${p.libelle} — ${p.recuperable ? 'hors coût' : p.cle === 'poids' ? 'au poids' : 'à la valeur'}`,
    recherche: p.code,
  }))
}

/** « Tout le dossier » (0) ou une marchandise. */
export function optionsPorteSur(d: DossierFiche): OptionSelecteur<number>[] {
  return [
    { id: 0, titre: 'Tout le dossier' },
    ...d.lignes.map((l) => ({ id: l.id, titre: `${l.reference} · lot ${l.lot || '—'}` })),
  ]
}

/** La répartition d'un frais à ajouter, dite comme le serveur la dira. */
export function repartitionDe(p: PosteFiche | undefined, ligneId: number | null): string {
  if (!p) return '—'
  if (p.recuperable) return 'hors coût (récupérable)'
  if (ligneId != null) return 'sur cette marchandise'
  return p.cle === 'poids' ? 'au poids' : 'à la valeur'
}

export interface AjoutFraisProps {
  d: DossierFiche
  g: GestesDossier
  postes: readonly PosteFiche[]
  b: BrouillonFrais
  setB: (b: BrouillonFrais) => void
}

type Poser = <K extends keyof BrouillonFrais>(cle: K, v: BrouillonFrais[K]) => void

/** Les textes et les dates de la ligne d'ajout. */
function ChampsTextes({ b, poser }: { b: BrouillonFrais; poser: Poser }) {
  return (
    <>
      <Champ libelle="Prestataire" className={styles.etroit}>
        <Saisie
          valeur={b.prestataire}
          onChange={(v) => poser('prestataire', v)}
          max={120}
          placeholder="transitaire, transporteur…"
        />
      </Champ>
      <Champ libelle="Pièce" className={styles.etroit}>
        <Saisie
          valeur={b.piece}
          onChange={(v) => poser('piece', v)}
          max={64}
          placeholder="n° de facture, quittance"
        />
      </Champ>
      <Champ libelle="Date de la pièce" className={styles.etroit}>
        <DateChamp valeur={b.date_piece} onChange={(v) => poser('date_piece', v)} />
      </Champ>
      <Champ libelle="Échéance" className={styles.etroit}>
        <DateChamp valeur={b.echeance} onChange={(v) => poser('echeance', v)} futurPermis />
      </Champ>
      <Champ libelle="Observations" className={styles.etroit}>
        <Saisie valeur={b.commentaire} onChange={(v) => poser('commentaire', v)} max={300} />
      </Champ>
    </>
  )
}

/** Le poste choisi (le premier par défaut), ce qui manque, et l'ajout. */
function useAjout({ g, postes, b, setB }: AjoutFraisProps) {
  const posteId = b.poste_id ?? postes[0]?.id ?? null
  const poste = postes.find((p) => p.id === posteId)
  const manque = [
    ...(b.montant == null || b.montant === 0 ? ['Montant'] : []),
    ...(posteId == null ? ['Poste'] : []),
  ]
  const ajouter = async () => {
    if (posteId == null || b.montant == null) return
    await g.ajouterFrais({
      poste_id: posteId,
      montant: b.montant,
      ligne_id: b.ligne_id,
      prestataire: b.prestataire.trim(),
      piece: b.piece.trim(),
      date_piece: b.date_piece || null,
      echeance: b.echeance || null,
      commentaire: b.commentaire.trim(),
    })
    setB(FRAIS_VIDE)
    dire(`Frais « ${poste?.libelle ?? ''} » ajouté.`)
  }
  return { posteId, poste, manque, ajouter }
}

export function AjoutFrais(p: AjoutFraisProps) {
  const { d, b, setB, postes } = p
  const { posteId, poste, manque, ajouter } = useAjout(p)
  const poser: Poser = (cle, v) => setB({ ...b, [cle]: v })
  return (
    <div className={styles.panneau} aria-label="Ajouter un frais">
      <Champ libelle="Poste" className={styles.moyen}>
        <Selecteur
          valeur={posteId}
          options={optionsPostes(postes)}
          onChange={(id) => poser('poste_id', id)}
          effacable={false}
        />
      </Champ>
      <Champ libelle="Montant (MAD)" className={styles.etroit}>
        <Nombre
          valeur={b.montant}
          onChange={(v) => poser('montant', v)}
          decimales={2}
          min={-1e9}
          max={1e9}
          placeholder="avoir : négatif"
        />
      </Champ>
      <Champ libelle="Porte sur" className={styles.moyen}>
        <Selecteur
          valeur={b.ligne_id ?? 0}
          options={optionsPorteSur(d)}
          onChange={(id) => poser('ligne_id', id ? id : null)}
          effacable={false}
        />
      </Champ>
      <span className={styles.note}>{repartitionDe(poste, b.ligne_id)}</span>
      <ChampsTextes b={b} poser={poser} />
      <Bouton
        variante="principal"
        manque={manque}
        blocages={d.actions.frais ? [d.actions.frais] : []}
        attente="Ajout…"
        onClick={ajouter}
      >
        Ajouter
      </Bouton>
      <Bouton
        variante="fantome"
        titre="Vider la ligne d’ajout"
        grise={fraisCommence(b) ? undefined : 'La ligne d’ajout est vide.'}
        onClick={() => setB(FRAIS_VIDE)}
      >
        Effacer
      </Bouton>
    </div>
  )
}
