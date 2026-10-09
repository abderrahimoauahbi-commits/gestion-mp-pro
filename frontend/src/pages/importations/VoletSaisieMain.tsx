/**
 * Fiche dossier › Saisie à la main (ECRANS-PRO 5.13) : la marchandise d'un dossier d'avant la mise
 * en service, saisie comme un stock d'ouverture (un numéro de lot inconnu est créé sans stock).
 * Matière, lot, fournisseur (par défaut celui de la matière), poids, prix au kilo et valeur liés,
 * devise, cours payé (vide : le cours du jour, `null`), observations. Après l'ajout, le brouillon se
 * vide mais garde fournisseur, devise et cours. Le brouillon vit dans la fiche (onglets, garde).
 */
import { Grille } from '../../composants/mise-en-page/Grille'
import { dire } from '../../composants/retour/Messages'
import { Note } from '../../composants/retour/Note'
import { Bouton } from '../../composants/saisie/Bouton'
import { Champ } from '../../composants/saisie/Champ'
import { Nombre } from '../../composants/saisie/Nombre'
import { Saisie } from '../../composants/saisie/Saisie'
import { Selecteur } from '../../composants/saisie/Selecteur'
import { SelecteurMatiere } from '../../composants/saisie/SelecteurMatiere'
import { arrondi } from '../../lib/format'
import { useLecture } from '../../lib/requetes'
import styles from './Importations.module.css'
import type { DeviseFiche, DossierFiche, FournisseurResume, MatiereResume } from './types'
import type { GestesDossier } from './useDossier'

export interface BrouillonMain {
  matiere_id: number | null
  lot_numero: string
  fournisseur_id: number | null
  quantite_kg: number | null
  prix: number | null
  valeur_devise: number | null
  devise: string
  cours: number | null
  commentaire: string
}

export const MAIN_VIDE: BrouillonMain = {
  matiere_id: null,
  lot_numero: '',
  fournisseur_id: null,
  quantite_kg: null,
  prix: null,
  valeur_devise: null,
  devise: 'MAD',
  cours: null,
  commentaire: '',
}

export const mainCommencee = (b: BrouillonMain) =>
  b.matiere_id != null || b.quantite_kg != null || b.valeur_devise != null || Boolean(b.lot_numero.trim())

/** Poids, prix et valeur liés : la valeur suit poids × prix ; le prix suit valeur ÷ poids (4 déc.). */
function lier(b: BrouillonMain, modif: Partial<BrouillonMain>): BrouillonMain {
  const s = { ...b, ...modif }
  if ('valeur_devise' in modif) {
    s.prix = s.quantite_kg && s.valeur_devise != null ? arrondi(s.valeur_devise / s.quantite_kg, 4) : s.prix
  } else if (('quantite_kg' in modif || 'prix' in modif) && s.quantite_kg != null && s.prix != null) {
    s.valeur_devise = arrondi(s.quantite_kg * s.prix, 2)
  }
  return s
}

export interface VoletSaisieMainProps {
  d: DossierFiche
  g: GestesDossier
  b: BrouillonMain
  setB: (b: BrouillonMain) => void
}

type Poser = (modif: Partial<BrouillonMain>) => void

/** La matière, son lot, son fournisseur. */
function ChampsMatiere({
  b,
  poser,
  actives,
}: {
  b: BrouillonMain
  poser: Poser
  actives: readonly MatiereResume[]
}) {
  const fournisseurs = useLecture<FournisseurResume[]>('/fournisseurs')
  const m = actives.find((x) => x.id === b.matiere_id)
  return (
    <>
      <Champ libelle="Matière" obligatoire large>
        <SelecteurMatiere
          matieres={actives.map((x) => ({ ...x, type: x.type_fil }))}
          valeur={b.matiere_id}
          onChange={(id) => {
            const choisie = actives.find((x) => x.id === id)
            poser({ matiere_id: id, devise: choisie?.devise ?? b.devise, prix: choisie?.prix ?? b.prix })
          }}
        />
      </Champ>
      <Champ libelle="Numéro de lot" aide="facultatif">
        <Saisie valeur={b.lot_numero} onChange={(v) => poser({ lot_numero: v })} max={80} />
      </Champ>
      <Champ libelle="Fournisseur" aide="par défaut, celui de la matière">
        <Selecteur
          valeur={b.fournisseur_id}
          placeholder={m?.fournisseur ? `${m.fournisseur} (matière)` : 'Celui de la matière'}
          options={(fournisseurs.data ?? []).filter((f) => f.actif).map((f) => ({ id: f.id, titre: f.nom }))}
          onChange={(id) => poser({ fournisseur_id: id })}
        />
      </Champ>
    </>
  )
}

/** Poids, prix, valeur, devise, cours, observations. */
function ChampsValeur({ b, poser }: { b: BrouillonMain; poser: Poser }) {
  const devises = useLecture<DeviseFiche[]>('/devises')
  return (
    <>
      <Champ libelle="Poids (kg)" obligatoire>
        <Nombre
          valeur={b.quantite_kg}
          onChange={(v) => poser({ quantite_kg: v })}
          decimales={3}
          min={0.001}
          max={1e9}
          unite="kg"
        />
      </Champ>
      <Champ libelle={`Prix (${b.devise} / kg)`}>
        <Nombre valeur={b.prix} onChange={(v) => poser({ prix: v })} decimales={4} min={0} />
      </Champ>
      <Champ libelle={`Valeur facture (${b.devise})`} aide="le total de la ligne" obligatoire>
        <Nombre
          valeur={b.valeur_devise}
          onChange={(v) => poser({ valeur_devise: v })}
          decimales={2}
          min={0}
          max={1e10}
        />
      </Champ>
      <Champ libelle="Devise">
        <Selecteur
          valeur={b.devise}
          effacable={false}
          options={(devises.data ?? [])
            .filter((x) => x.actif || x.code === b.devise)
            .map((x) => ({ id: x.code, titre: `${x.code} — ${x.nom}` }))}
          onChange={(code) => poser({ devise: code ?? 'MAD' })}
        />
      </Champ>
      {b.devise !== 'MAD' ? (
        <Champ libelle={`Cours payé (MAD pour 1 ${b.devise})`} aide="vide : le cours du jour des réglages">
          <Nombre
            valeur={b.cours}
            onChange={(v) => poser({ cours: v })}
            decimales={4}
            min={0.0001}
            max={1000}
          />
        </Champ>
      ) : null}
      <Champ libelle="Observations" large>
        <Saisie valeur={b.commentaire} onChange={(v) => poser({ commentaire: v })} max={300} />
      </Champ>
    </>
  )
}

export function VoletSaisieMain({ d, g, b, setB }: VoletSaisieMainProps) {
  const matieres = useLecture<MatiereResume[]>('/matieres')
  const actives = (matieres.data ?? []).filter((m) => m.actif)
  const m = actives.find((x) => x.id === b.matiere_id)
  const poser: Poser = (modif) => setB(lier(b, modif))
  const manque = [
    ...(b.matiere_id == null ? ['Matière'] : []),
    ...(!b.quantite_kg ? ['Poids'] : []),
    ...(b.valeur_devise == null ? ['Valeur'] : []),
  ]
  const ajouter = async () => {
    if (!m || b.quantite_kg == null || b.valeur_devise == null) return
    await g.saisir({
      matiere_id: m.id,
      lot_numero: b.lot_numero.trim(),
      fournisseur_id: b.fournisseur_id,
      quantite_kg: b.quantite_kg,
      valeur_devise: b.valeur_devise,
      devise: b.devise,
      cours: b.devise === 'MAD' ? null : b.cours,
      commentaire: b.commentaire.trim(),
    })
    dire(`${m.reference} ajoutée au dossier${b.lot_numero.trim() ? `, lot ${b.lot_numero.trim()}` : ''}.`)
    setB({ ...MAIN_VIDE, fournisseur_id: b.fournisseur_id, devise: b.devise, cours: b.cours })
  }
  return (
    <div className={styles.pile}>
      <Note>
        Pour un dossier d’avant la mise en service : la marchandise n’a pas de réception dans Gestion MP. Un
        numéro de lot inconnu est créé (sans stock) : un stock d’ouverture saisi sous le même numéro prendra
        le coût de ce dossier.
      </Note>
      <Grille colonnes={4}>
        <ChampsMatiere b={b} poser={poser} actives={actives} />
        <ChampsValeur b={b} poser={poser} />
      </Grille>
      <div className={styles.rangee}>
        <span className={styles.pousse} />
        <Bouton
          variante="fantome"
          grise={mainCommencee(b) ? undefined : 'Rien n’est saisi.'}
          onClick={() => setB(MAIN_VIDE)}
        >
          Effacer
        </Bouton>
        <Bouton
          variante="principal"
          manque={manque}
          blocages={d.actions.saisir ? [d.actions.saisir] : []}
          attente="Ajout…"
          onClick={ajouter}
        >
          Ajouter au dossier
        </Bouton>
      </div>
    </div>
  )
}
