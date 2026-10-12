/**
 * La ligne d'ajout d'un frais (ECRANS-PRO 5.9, « la ligne bleue ») : poste (le premier par défaut),
 * taux (lot TAUX-FRAIS, facultatif), montant (un avoir en négatif), « Porte sur » (tout le dossier,
 * ou une marchandise), répartition qui en découle, prestataire, pièce, dates, observations ;
 * « Ajouter » grisé avec ce qui manque, « Effacer ». Le brouillon vit dans la fiche : il survit au
 * changement d'onglet et rend la fenêtre « sale » tant qu'il n'est pas ajouté ou effacé.
 *
 * Le montant suit le taux (`tauxFrais.ts`) tant que l'utilisateur n'y a pas tapé : taux, poste ou
 * « Porte sur » changés le recalculent. Tapé, il est « à la main » et ne bouge plus ; vidé, il
 * revient au calcul ; un taux changé ensuite le recalcule (geste explicite).
 */
import { classes } from '../../composants/mise-en-page/classes'
import { dire } from '../../composants/retour/Messages'
import { Bouton } from '../../composants/saisie/Bouton'
import { Champ } from '../../composants/saisie/Champ'
import { DateChamp } from '../../composants/saisie/DateChamp'
import { Nombre } from '../../composants/saisie/Nombre'
import { Saisie } from '../../composants/saisie/Saisie'
import { Selecteur, type OptionSelecteur } from '../../composants/saisie/Selecteur'
import styles from './Importations.module.css'
import { baseDuTaux, montantAuTaux, noteDuTaux, TAUX_MAX, tauxPermis } from './tauxFrais'
import type { DossierFiche, PosteFiche } from './types'
import type { GestesDossier } from './useDossier'

export interface BrouillonFrais {
  poste_id: number | null
  taux: number | null
  montant: number | null
  /** Le montant a été tapé : le taux, le poste ou « Porte sur » ne le recalculent plus. */
  montant_a_la_main: boolean
  ligne_id: number | null
  prestataire: string
  piece: string
  date_piece: string
  echeance: string
  commentaire: string
}

export const FRAIS_VIDE: BrouillonFrais = {
  poste_id: null,
  taux: null,
  montant: null,
  montant_a_la_main: false,
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
  b.taux != null ||
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

/** Le poste du brouillon : celui choisi, sinon le premier. */
const posteDe = (b: BrouillonFrais, postes: readonly PosteFiche[]) =>
  postes.find((p) => p.id === (b.poste_id ?? postes[0]?.id))

/**
 * Le brouillon après un champ posé. Taper un montant le met « à la main » ; le vider, ou changer
 * le taux, le rend au calcul ; tant qu'il n'est pas à la main, il vaut base × taux (vide sans taux).
 */
export function poserDansBrouillon<K extends keyof BrouillonFrais>(
  b: BrouillonFrais,
  cle: K,
  v: BrouillonFrais[K],
  d: DossierFiche,
  postes: readonly PosteFiche[],
): BrouillonFrais {
  const n: BrouillonFrais = { ...b, [cle]: v }
  if (cle === 'montant') n.montant_a_la_main = v != null
  if (cle === 'taux') n.montant_a_la_main = false
  if (n.montant_a_la_main) return n
  const base = baseDuTaux(d, postes, posteDe(n, postes), n.ligne_id)
  return { ...n, montant: tauxPermis(n.taux) ? montantAuTaux(base.montant, n.taux) : null }
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

/** Le taux et le montant : la note sous le taux dit la base utilisée. */
function ChampsMontant(p: AjoutFraisProps & { poser: Poser }) {
  const { b, poser } = p
  const base = baseDuTaux(p.d, p.postes, posteDe(b, p.postes), b.ligne_id)
  return (
    <>
      <Champ
        libelle="Taux (%)"
        className={styles.taux}
        aide={tauxPermis(b.taux) ? noteDuTaux(b.taux, base) : undefined}
      >
        <Nombre
          valeur={b.taux}
          onChange={(v) => poser('taux', v)}
          decimales={4}
          min={0}
          max={TAUX_MAX}
          unite="%"
          placeholder="TVA : 20"
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
    ...(b.taux != null && !tauxPermis(b.taux) ? ['Taux (plus de 0, au plus 100 %)'] : []),
  ]
  const ajouter = async () => {
    if (posteId == null || b.montant == null) return
    await g.ajouterFrais({
      poste_id: posteId,
      taux: b.taux,
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
  const poser: Poser = (cle, v) => setB(poserDansBrouillon(b, cle, v, d, postes))
  return (
    <div className={classes(styles.panneau, styles.panneauFrais)} aria-label="Ajouter un frais">
      <Champ libelle="Poste" className={styles.moyen}>
        <Selecteur
          valeur={posteId}
          options={optionsPostes(postes)}
          onChange={(id) => poser('poste_id', id)}
          effacable={false}
        />
      </Champ>
      <ChampsMontant {...p} poser={poser} />
      <Champ libelle="Porte sur" className={styles.moyen}>
        <Selecteur
          valeur={b.ligne_id ?? 0}
          options={optionsPorteSur(d)}
          onChange={(id) => poser('ligne_id', id ? id : null)}
          effacable={false}
        />
      </Champ>
      <span className={classes(styles.note, styles.surLesControles)}>{repartitionDe(poste, b.ligne_id)}</span>
      <ChampsTextes b={b} poser={poser} />
      <Bouton
        variante="principal"
        className={styles.surLesControles}
        manque={manque}
        blocages={d.actions.frais ? [d.actions.frais] : []}
        attente="Ajout…"
        onClick={ajouter}
      >
        Ajouter
      </Bouton>
      <Bouton
        variante="fantome"
        className={styles.surLesControles}
        titre="Vider la ligne d’ajout"
        grise={fraisCommence(b) ? undefined : 'La ligne d’ajout est vide.'}
        onClick={() => setB(FRAIS_VIDE)}
      >
        Effacer
      </Bouton>
    </div>
  )
}
