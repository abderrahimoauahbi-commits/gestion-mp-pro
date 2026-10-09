/**
 * Fiche commande › Lignes et livraison (ECRANS-PRO 4.8) : la date promise, les remarques au
 * fournisseur (pleine largeur), les lignes saisies dans leur unité de commande et en kilos, ce qui
 * est reçu et ce qui reste ; « Enregistrer » envoie le bon entier (`PUT /commandes/{id}`).
 */
import { Link } from 'react-router'

import { Badge } from '../../composants/retour/Badge'
import { KgEtMetres } from '../../composants/retour/KgEtMetres'
import { Note } from '../../composants/retour/Note'
import { Bouton } from '../../composants/saisie/Bouton'
import { Champ } from '../../composants/saisie/Champ'
import { DateChamp } from '../../composants/saisie/DateChamp'
import { Nombre } from '../../composants/saisie/Nombre'
import { Selecteur } from '../../composants/saisie/Selecteur'
import { Zone } from '../../composants/saisie/Zone'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { arrondi, date, montant, nombre, part, prixUnite, VIDE } from '../../lib/format'
import { formule } from '../../lib/aide'
import { aujourdhui } from '../../lib/heure'
import styles from '../plan-achat/achats.module.css'
import { deux } from '../plan-achat/colonnesFournisseurs'
import { libelleUnite } from '../plan-achat/libelles'
import type { Matiere } from '../plan-achat/types'
import { ligneAjoutee, unitesDeLigne, type FormeLignes, type LigneForme } from './formeLignes'
import { texteReserve } from './messages'
import type { CommandeFiche, LigneCommande } from './types'
import type { FormeFiche } from './useFormeFiche'

interface Contexte {
  c: CommandeFiche
  f: FormeFiche<FormeLignes>
  matieres: ReadonlyMap<number, Matiere>
  lien: (id: number) => string | null
}

const lue = (c: CommandeFiche, id: number): LigneCommande | undefined =>
  c.lignes.find((l) => l.matiere_id === id)

function changer(x: Contexte, id: number, modif: Partial<LigneForme>) {
  x.f.maj({ lignes: x.f.forme.lignes.map((l) => (l.matiere_id === id ? { ...l, ...modif } : l)) })
}

function Unite({ x, l }: { x: Contexte; l: LigneForme }) {
  const unites = unitesDeLigne(l, x.matieres.get(l.matiere_id))
  return (
    <select
      className={styles.choix}
      aria-label="Commandé en"
      value={l.unite}
      disabled={!x.c.modifiable}
      onChange={(e) => {
        const u = unites.find((v) => v.unite === e.target.value)
        if (u) changer(x, l.matiere_id, { unite: u.unite, contenance: u.contenance || 1 })
      }}
    >
      {unites.map((u) => (
        <option key={u.unite} value={u.unite}>
          {libelleUnite(u.unite, u.contenance)}
        </option>
      ))}
    </select>
  )
}

function Prix({ c, l }: { c: CommandeFiche; l: LigneCommande | undefined }) {
  if (!l) return <Badge famille="prix" valeur="a_confirmer" />
  if (l.prix_confirme) return <>{prixUnite(l.prix, c.devise, 'kg')}</>
  return deux(
    <Badge famille="prix" valeur="a_confirmer" />,
    l.prix_catalogue ? `catalogue ${prixUnite(l.prix_catalogue, l.devise_catalogue, 'kg')}` : null,
  )
}

function colonnes1(x: Contexte): Colonne<LigneForme>[] {
  const { c } = x
  const modif = c.modifiable
  return [
    {
      cle: 'reference',
      titre: 'Référence',
      valeur: (l) => lue(c, l.matiere_id)?.reference ?? x.matieres.get(l.matiere_id)?.reference ?? '',
      rendu: (l) => {
        const ref = lue(c, l.matiere_id)?.reference ?? x.matieres.get(l.matiere_id)?.reference ?? ''
        const lien = x.lien(l.matiere_id)
        const texte = (
          <span className={styles.ref} title={ref}>
            {ref}
          </span>
        )
        return deux(
          lien ? <Link to={lien}>{texte}</Link> : texte,
          lue(c, l.matiere_id)?.designation ?? x.matieres.get(l.matiere_id)?.designation,
        )
      },
    },
    { cle: 'unite', titre: 'Commandé en', rendu: (l) => <Unite x={x} l={l} /> },
    {
      cle: 'unites',
      titre: 'Quantité',
      droite: true,
      valeur: (l) => l.quantite / (l.contenance || 1),
      rendu: (l) =>
        modif ? (
          <Nombre
            valeur={arrondi(l.quantite / (l.contenance || 1), 2)}
            onChange={(v) =>
              changer(x, l.matiere_id, { quantite: arrondi(Math.max(0, v ?? 0) * (l.contenance || 1), 3) })
            }
            min={0}
            decimales={2}
            libelle="Quantité dans l’unité de commande"
            className={styles.champEtroit}
          />
        ) : (
          nombre(l.quantite / (l.contenance || 1), 0, 2)
        ),
    },
  ]
}

function colonnes2(x: Contexte): Colonne<LigneForme>[] {
  const { c } = x
  return [
    {
      cle: 'quantite',
      titre: 'Soit (kg)',
      droite: true,
      unite: 'kg',
      total: true,
      rendu: (l) => (
        <KgEtMetres
          kg={l.quantite}
          kgParMl={lue(c, l.matiere_id)?.kg_par_ml || x.matieres.get(l.matiere_id)?.kg_par_ml || null}
        />
      ),
    },
    {
      cle: 'recu',
      titre: 'Reçu (kg)',
      aide: 'Pesé aux réceptions validées, moins ce qui est reparti chez le fournisseur',
      droite: true,
      unite: 'kg',
      total: true,
      valeur: (l) => lue(c, l.matiere_id)?.recu ?? 0,
      rendu: (l) => {
        const r = lue(c, l.matiere_id)
        if (!r || !r.recu) return VIDE
        return `${nombre(r.recu)} · ${part(r.quantite ? r.recu / r.quantite : 0, 0)}`
      },
    },
  ]
}

function colonnes3(x: Contexte): Colonne<LigneForme>[] {
  const { c } = x
  return [
    {
      cle: 'reste',
      titre: 'Reste à livrer (kg)',
      aide: 'Commandé moins reçu ; un reliquat sous la tolérance compte pour complet',
      droite: true,
      unite: 'kg',
      total: true,
      valeur: (l) =>
        c.statut === 'soldee' || c.statut === 'annulee' ? 0 : (lue(c, l.matiere_id)?.reste ?? l.quantite),
      rendu: (l) => {
        if (c.statut === 'soldee' || c.statut === 'annulee') return VIDE
        const r = lue(c, l.matiere_id)
        const reste =
          r && r.recu > 0 && r.reste <= 0 ? <Badge ton="ok">complet</Badge> : nombre(r?.reste ?? l.quantite)
        if (!r?.en_quarantaine) return reste
        return deux(reste, <span className={styles.attention}>{texteReserve(r.en_quarantaine)}</span>)
      },
    },
    { cle: 'prix', titre: 'Prix / kg', droite: true, rendu: (l) => <Prix c={c} l={lue(c, l.matiere_id)} /> },
    {
      cle: 'montant',
      titre: 'Montant',
      droite: true,
      unite: c.devise,
      total: c.lignes.some((l) => l.prix_confirme),
      valeur: (l) => lue(c, l.matiere_id)?.montant ?? 0,
      rendu: (l) => {
        const r = lue(c, l.matiere_id)
        return r?.prix_confirme ? montant(r.montant, c.devise) : VIDE
      },
    },
  ]
}

function colonnes4(x: Contexte): Colonne<LigneForme>[] {
  const modif = x.c.modifiable
  return [
    {
      cle: 'retirer',
      titre: '',
      triable: false,
      rendu: (l) =>
        modif ? (
          <Bouton
            taille="petit"
            variante="danger"
            manque={
              x.f.forme.lignes.length <= 1
                ? ['une autre ligne (un bon garde au moins une ligne : supprimez le bon)']
                : undefined
            }
            titre="Retirer cette matière du bon"
            onClick={() => x.f.maj({ lignes: x.f.forme.lignes.filter((y) => y.matiere_id !== l.matiere_id) })}
          >
            Retirer
          </Bouton>
        ) : null,
    },
  ]
}

function colonnes(x: Contexte): Colonne<LigneForme>[] {
  return [...colonnes1(x), ...colonnes2(x), ...colonnes3(x), ...colonnes4(x)]
}

/** Pourquoi la date promise ne se change plus (la phrase du serveur, `promesse_figee`), ou `''`. */
export const dateFigee = (c: CommandeFiche): string => c.promesse_figee ?? ''

function EnTeteLignes({ x, ajoutables }: { x: Contexte; ajoutables: readonly Matiere[] }) {
  const { c, f } = x
  const figee = dateFigee(c)
  const aide =
    figee ||
    (c.parti
      ? 'promise par le fournisseur'
      : `vide : date d’envoi + ${nombre(c.delai_jours)} j (délai du fournisseur)`)
  return (
    <>
      <div className={styles.rangee}>
        <Champ libelle="Livraison prévue" aide={aide}>
          <DateChamp
            valeur={f.forme.livraison}
            onChange={(v) => f.maj({ livraison: v })}
            min={c.parti ? c.date_commande : aujourdhui()}
            futurPermis
            desactive={Boolean(figee)}
          />
        </Champ>
        <Champ
          libelle={`Ajouter une matière (${c.devise})`}
          aide="Seules les matières de ce fournisseur, dans la devise du bon"
          className={styles.champLarge}
        >
          <Selecteur<number>
            valeur={null}
            options={ajoutables.map((m) => ({ id: m.id, titre: m.reference, sous: m.designation }))}
            placeholder="Référence, couleur, titrage…"
            onChange={(id) => {
              const m = ajoutables.find((y) => y.id === id)
              if (m) f.maj({ lignes: [...f.forme.lignes, ligneAjoutee(m)] })
            }}
          />
        </Champ>
      </div>
      <Champ
        libelle="Remarques au fournisseur — imprimées sur le bon, qui est en anglais : les écrire en anglais"
        large
      >
        <Zone
          valeur={f.forme.observations}
          onChange={(v) => f.maj({ observations: v })}
          lignes={2}
          max={2000}
        />
      </Champ>
    </>
  )
}

function NoteFigee({ c }: { c: CommandeFiche }) {
  const clos = c.statut === 'soldee' || c.statut === 'annulee'
  return (
    <>
      <Note ton="attention">
        {clos
          ? 'Ce bon est clos : il ne se modifie plus. « Rouvrir » le remet en attente de livraison.'
          : 'Ce bon a commencé à être livré : ses lignes sont figées. Pour un complément, préparez un autre bon ; s’il ne viendra rien de plus, soldez-le.'}
      </Note>
      <span className={styles.note}>
        Livraison prévue : {date(c.date_livraison_prevue)}
        {c.observations ? ` · Remarques au fournisseur : ${c.observations}` : ''}
      </span>
    </>
  )
}

/** La part du bon reçue sous réserve, en quarantaine : comptée reçue ici, attendue ailleurs. */
function NoteReserve({ c }: { c: CommandeFiche }) {
  if (c.statut === 'soldee' || c.statut === 'annulee') return null
  const kg = c.kg_en_quarantaine
  if (kg <= 0) return null
  const texte = texteReserve(kg)
  return (
    <Note ton="attention">
      Reçu : {texte.charAt(0).toUpperCase()}
      {texte.slice(1)}. {formule('commande_reserve')}
    </Note>
  )
}

export function VoletLignes(props: Contexte & { ajoutables: readonly Matiere[] }) {
  const { c, f } = props
  return (
    <div className={styles.volet}>
      {c.modifiable && c.parti ? (
        <Note>
          Ce bon est déjà parti. Vous pouvez encore le corriger (rien n’est reçu) : pensez à renvoyer le bon
          réimprimé au fournisseur.
        </Note>
      ) : null}
      {c.modifiable ? (
        <EnTeteLignes
          x={props}
          ajoutables={props.ajoutables.filter((m) => !f.forme.lignes.some((l) => l.matiere_id === m.id))}
        />
      ) : (
        <NoteFigee c={c} />
      )}
      <NoteReserve c={c} />
      <div className={styles.tableFenetre}>
        <DataTable<LigneForme>
          libelle="Lignes du bon"
          lignes={f.forme.lignes}
          colonnes={colonnes(props)}
          cle={(l) => l.matiere_id}
          recherche={false}
          hauteur="fenetre"
          vide="Aucune ligne : un bon garde au moins une ligne."
        />
      </div>
    </div>
  )
}
