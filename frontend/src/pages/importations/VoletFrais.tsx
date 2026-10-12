/**
 * Fiche dossier › Frais (ECRANS-PRO 5.9) : les deux encarts de contrôle, la ligne d'ajout, puis un
 * frais par ligne — poste et « porte sur » enregistrés aussitôt, montant, textes et dates en quittant
 * le champ. Un montant vidé revient, avec « Un frais a un montant : pour l'enlever, « Retirer ». »
 * (anomalie 5.6). Un frais **réglé** garde son poste, son montant et sa marchandise, et ne se retire
 * pas : les champs sont grisés avec la raison du serveur (« Frais réglé le … : annuler d'abord le
 * règlement (Analyse › Échéancier) », anomalie 5.5) ; « réglé le » se lit aussi en saisie. Le pied
 * dit les charges dans le coût et, à part, la TVA récupérable.
 *
 * Taux (lot TAUX-FRAIS) : le taux enregistré s'affiche avec le montant enregistré, que rien ne
 * recalcule (ni la réouverture, ni un cours changé). Seul un taux changé recalcule le montant
 * (base × taux, `tauxFrais.ts`) et enregistre les deux ; un taux vidé garde le montant.
 */
import { dire } from '../../composants/retour/Messages'
import { Vide } from '../../composants/retour/Vide'
import { Confirmer } from '../../composants/saisie/Confirmer'
import { Selecteur } from '../../composants/saisie/Selecteur'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { date, montantPrecis, VIDE } from '../../lib/format'
import { AjoutFrais, optionsPorteSur, optionsPostes, type BrouillonFrais } from './AjoutFrais'
import { DateEnregistree, NombreEnregistre, TexteEnregistre } from './champsEnregistres'
import { ControlesFrais } from './ControlesFrais'
import styles from './Importations.module.css'
import { baseDuTaux, montantAuTaux, TAUX_MAX, tauxLisible } from './tauxFrais'
import type { DossierFiche, FraisDossier, PosteFiche } from './types'
import { corpsDuFrais, type FraisCorps, type GestesDossier } from './useDossier'

interface Ctx {
  d: DossierFiche
  g: GestesDossier
  postes: readonly PosteFiche[]
  modifiable: boolean
  noter: () => void
}

const VIDER_MONTANT = 'Un frais a un montant : pour l’enlever, « Retirer ».'

/** Modifier un champ d'un frais : tout le frais est renvoyé, avec sa version. */
const modifier = (c: Ctx, f: FraisDossier) => async (modif: Partial<FraisCorps>) => {
  await c.g.modifierFrais(f, { ...corpsDuFrais(f), ...modif })
  c.noter()
}

function Poste({ f, c }: { f: FraisDossier; c: Ctx }) {
  if (!c.modifiable || f.blocage) {
    return (
      <span className={styles.valeur} title={f.blocage ?? undefined}>
        <span>{f.libelle}</span>
        {f.recuperable ? <span className={styles.note}>récupérable</span> : null}
      </span>
    )
  }
  return (
    <span className={styles.celluleLarge}>
      <Selecteur
        libelle={`Poste du frais ${f.libelle}`}
        valeur={f.poste_id}
        options={optionsPostes(c.postes)}
        effacable={false}
        onChange={(id) => {
          if (id != null && id !== f.poste_id) void modifier(c, f)({ poste_id: id }).catch(() => undefined)
        }}
      />
    </span>
  )
}

/** Le taux changé (geste explicite) : le montant recalculé sur la base du frais ; vidé, le taux
 * seul s'efface (le montant reste). Une base nulle ne donne pas de montant : il reste aussi. */
export function changementDeTaux(
  d: DossierFiche,
  postes: readonly PosteFiche[],
  f: FraisDossier,
  taux: number | null,
): Partial<FraisCorps> {
  if (taux == null || taux <= 0) return { taux }
  const base = baseDuTaux(
    d,
    postes,
    postes.find((p) => p.id === f.poste_id),
    f.ligne_id,
  )
  const montant = montantAuTaux(base.montant, taux)
  return montant ? { taux, montant } : { taux }
}

function Taux({ f, c }: { f: FraisDossier; c: Ctx }) {
  if (!c.modifiable || f.blocage) {
    return <span title={f.blocage ?? undefined}>{f.taux == null ? VIDE : tauxLisible(f.taux)}</span>
  }
  // Un champ suivi de son unité prend « la place qui reste » : dans une cellule, il s'écrasait à
  // quelques pixels et le taux enregistré paraissait vide. La cellule lui donne sa largeur.
  return (
    <span className={styles.celluleTaux}>
      <NombreEnregistre
        libelle={`Taux du frais ${f.libelle}`}
        valeur={f.taux}
        decimales={4}
        min={0}
        max={TAUX_MAX}
        unite="%"
        onEnregistrer={(v) => modifier(c, f)(changementDeTaux(c.d, c.postes, f, v))}
      />
    </span>
  )
}

function PorteSur({ f, c }: { f: FraisDossier; c: Ctx }) {
  const options = optionsPorteSur(c.d)
  if (!c.modifiable || f.blocage) {
    const o = options.find((x) => x.id === (f.ligne_id ?? 0))
    return <span title={f.blocage ?? undefined}>{o?.titre ?? '?'}</span>
  }
  return (
    <span className={styles.celluleLarge}>
      <Selecteur
        libelle={`Ce que vise le frais ${f.libelle}`}
        valeur={f.ligne_id ?? 0}
        options={options}
        effacable={false}
        onChange={(id) => {
          const ligne = id ? id : null
          if (ligne !== f.ligne_id) void modifier(c, f)({ ligne_id: ligne }).catch(() => undefined)
        }}
      />
    </span>
  )
}

function texte(c: Ctx, cle: 'prestataire' | 'piece' | 'commentaire', libelle: string, max: number) {
  return (f: FraisDossier) =>
    c.modifiable ? (
      <TexteEnregistre
        libelle={`${libelle} du frais ${f.libelle}`}
        valeur={f[cle]}
        max={max}
        onEnregistrer={(v) => modifier(c, f)({ [cle]: v })}
      />
    ) : (
      f[cle] || VIDE
    )
}

function Echeance({ f, c }: { f: FraisDossier; c: Ctx }) {
  const regle = f.payee_le ? <span className={styles.note}>réglé le {date(f.payee_le)}</span> : null
  if (!c.modifiable)
    return (
      <span className={styles.valeur}>
        {date(f.echeance)}
        {regle}
      </span>
    )
  return (
    <span className={styles.valeur}>
      <DateEnregistree
        libelle={`Échéance du frais ${f.libelle}`}
        valeur={f.echeance}
        futurPermis
        onEnregistrer={(v) => modifier(c, f)({ echeance: v })}
      />
      {regle}
    </span>
  )
}

function Retirer({ f, c }: { f: FraisDossier; c: Ctx }) {
  if (!c.modifiable) return null
  return (
    <Confirmer
      taille="petit"
      variante="danger"
      question="Retirer ce frais ?"
      oui="Oui, retirer"
      titre={`Retirer le frais « ${f.libelle} » de ${montantPrecis(f.montant, 'MAD')}`}
      blocages={f.blocage ? [f.blocage] : []}
      onOui={async () => {
        await c.g.retirerFrais(f)
        dire(`Frais « ${f.libelle} » retiré.`)
      }}
    >
      Retirer
    </Confirmer>
  )
}

function colonnes(c: Ctx): Colonne<FraisDossier>[] {
  return [
    { cle: 'libelle', titre: 'Poste', recherche: (f) => [f.poste], rendu: (f) => <Poste f={f} c={c} /> },
    { cle: 'taux', titre: 'Taux', droite: true, rendu: (f) => <Taux f={f} c={c} /> },
    {
      cle: 'montant',
      titre: 'Montant (MAD)',
      droite: true,
      rendu: (f) =>
        c.modifiable && !f.blocage ? (
          <NombreEnregistre
            libelle={`Montant du frais ${f.libelle}`}
            valeur={f.montant}
            decimales={2}
            min={-1e9}
            max={1e9}
            videInterdit={VIDER_MONTANT}
            onEnregistrer={(v) => modifier(c, f)({ montant: v ?? f.montant })}
          />
        ) : (
          <span title={f.blocage ?? undefined}>{montantPrecis(f.montant, 'MAD')}</span>
        ),
    },
    { cle: 'ligne_id', titre: 'Porte sur', rendu: (f) => <PorteSur f={f} c={c} /> },
    { cle: 'repartition', titre: 'Répartition' },
    { cle: 'prestataire', titre: 'Prestataire', rendu: texte(c, 'prestataire', 'Prestataire', 120) },
    { cle: 'piece', titre: 'Pièce', rendu: texte(c, 'piece', 'Pièce', 64) },
    {
      cle: 'date_piece',
      titre: 'Date de la pièce',
      rendu: (f) =>
        c.modifiable ? (
          <DateEnregistree
            libelle={`Date de la pièce du frais ${f.libelle}`}
            valeur={f.date_piece}
            onEnregistrer={(v) => modifier(c, f)({ date_piece: v })}
          />
        ) : (
          date(f.date_piece)
        ),
    },
    { cle: 'echeance', titre: 'Échéance', rendu: (f) => <Echeance f={f} c={c} /> },
    { cle: 'commentaire', titre: 'Observations', rendu: texte(c, 'commentaire', 'Observations', 300) },
    {
      cle: 'geste',
      titre: '',
      triable: false,
      exporte: false,
      valeur: () => '',
      rendu: (f) => <Retirer f={f} c={c} />,
    },
  ]
}

function Pied({ d }: { d: DossierFiche }) {
  const recuperables = d.frais.filter((f) => f.recuperable).reduce((s, f) => s + f.montant, 0)
  const cout = d.frais.filter((f) => !f.recuperable).reduce((s, f) => s + f.montant, 0)
  return (
    <tr>
      <td>Charges hors TVA</td>
      <td />
      <td className={styles.chiffre}>{montantPrecis(cout, 'MAD')}</td>
      <td colSpan={8}>dans le coût · TVA récupérable, hors coût : {montantPrecis(recuperables, 'MAD')}</td>
    </tr>
  )
}

export interface VoletFraisProps extends Ctx {
  brouillon: BrouillonFrais
  setBrouillon: (b: BrouillonFrais) => void
}

export function VoletFrais(p: VoletFraisProps) {
  const { d, modifiable, postes } = p
  const dd = postes.find((x) => x.code === 'DD')
  const proposer =
    modifiable && dd && d.droits_attendus_mad != null && !d.frais.some((f) => f.poste_id === dd.id)
      ? () =>
          p.setBrouillon({
            ...p.brouillon,
            poste_id: dd.id,
            montant: Math.round((d.droits_attendus_mad ?? 0) * 100) / 100,
            montant_a_la_main: true,
            commentaire: 'proposé par les codes douaniers',
          })
      : null
  return (
    <div className={styles.pile}>
      <ControlesFrais d={d} proposer={proposer} />
      {modifiable ? <AjoutFrais d={d} g={p.g} postes={postes} b={p.brouillon} setB={p.setBrouillon} /> : null}
      {d.frais.length ? (
        <DataTable
          libelle="Frais du dossier"
          lignes={d.frais}
          colonnes={colonnes(p)}
          cle={(f) => f.id}
          recherche={false}
          pied={<Pied d={d} />}
          hauteur="fenetre"
        />
      ) : (
        <Vide>
          {modifiable
            ? 'Aucun frais encore : le coût hors TVA est celui de la facture. Saisir droits, fret, transitaire, banque… dès que les pièces arrivent, sur la ligne d’ajout.'
            : 'Aucun frais saisi : le coût hors TVA est celui de la facture.'}
        </Vide>
      )}
    </div>
  )
}
