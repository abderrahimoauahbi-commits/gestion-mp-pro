/**
 * Onglet « Classification » (`/catalogue?onglet=classification&liste=…` ; direction, achats) :
 * une bascule de cinq vues — compositions, types de fil, titrages, couleurs (valeurs actives
 * comptées) et rôles de nomenclature. Une ligne ouvre la valeur en fenêtre ; désactiver se
 * confirme sur la ligne (P7-23) ; supprimer est grisé tant qu'une matière porte la valeur.
 */
import { useMemo, useState } from 'react'

import { Bascule } from '../../composants/mise-en-page/Bascule'
import { Carte } from '../../composants/mise-en-page/Carte'
import { Badge } from '../../composants/retour/Badge'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { dire } from '../../composants/retour/Messages'
import { Note } from '../../composants/retour/Note'
import { Bouton } from '../../composants/saisie/Bouton'
import { Confirmer } from '../../composants/saisie/Confirmer'
import { Interrupteur } from '../../composants/saisie/Interrupteur'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { api } from '../../lib/api'
import { nombre, VIDE } from '../../lib/format'
import { useEcriture } from '../../lib/requetes'
import { corpsValeur, versFormeValeur } from './ChampsValeur'
import styles from './catalogue.module.css'
import { Classer } from './Classer'
import { useClassification } from './donnees'
import { useEtatListe } from './etatListe'
import { Roles } from './Roles'
import {
  definition,
  LISTES,
  type Classification,
  type DefinitionListe,
  type Liste,
  type Valeur,
} from './types'
import { blocagesValeur, ValeurClassification } from './ValeurClassification'

type Vue = Liste | 'roles'
const VUES: readonly Vue[] = ['compositions', 'types-fil', 'titrages', 'couleurs', 'roles']

/** Les gestes d'une valeur sur sa ligne : changer son état, la supprimer. */
function useGestesValeur(v: Valeur, d: DefinitionListe) {
  const ecriture = useEcriture((envoi: () => Promise<unknown>) => envoi())
  const modification = useEcriture((actif: boolean) =>
    api.put<Valeur>(`/classification/${d.liste}/${v.id}`, {
      ...corpsValeur(d, versFormeValeur(v)),
      actif,
      version: v.version,
    }),
  )
  const e = d.feminin ? 'e' : ''
  const desactivee = `« ${v.code} » désactivé${e} : ${d.feminin ? 'elle' : 'il'} n’est plus proposé${e} pour une nouvelle matière.`
  return {
    changer: async (actif: boolean) => {
      const r = await modification.mutateAsync(actif)
      if (r.avertissement) dire(r.avertissement, 'attention')
      else dire(actif ? `« ${v.code} » réactivé${e}.` : desactivee)
    },
    supprimer: async () => {
      await ecriture.mutateAsync(() =>
        api.supprimer(`/classification/${d.liste}/${v.id}?version=${v.version}`),
      )
      dire(`« ${v.code} » supprimé${e}.`)
    },
  }
}

/** Désactiver (confirmé) ou réactiver, et supprimer (grisé si portée), sur la ligne. */
function Gestes({ v, d }: { v: Valeur; d: DefinitionListe }) {
  const { changer, supprimer } = useGestesValeur(v, d)
  return (
    <span
      className={styles.rangee}
      onClick={(ev) => ev.stopPropagation()}
      onKeyDown={(ev) => ev.stopPropagation()}
    >
      {v.actif ? (
        <Confirmer
          taille="petit"
          question={`Désactiver « ${v.code} » ?`}
          oui="Oui, désactiver"
          titre="Ne plus la proposer pour une nouvelle matière ; celles qui la portent la gardent"
          onOui={() => changer(false)}
        >
          Désactiver
        </Confirmer>
      ) : (
        <Bouton
          taille="petit"
          titre="La proposer de nouveau"
          attente="Réactivation…"
          onClick={() => changer(true)}
        >
          Réactiver
        </Bouton>
      )}
      <Confirmer
        taille="petit"
        variante="danger"
        question={`Supprimer « ${v.code} » ?`}
        oui="Oui, supprimer"
        blocages={blocagesValeur(v)}
        titre="Supprimer cette valeur, qu’aucune matière ne porte"
        onOui={supprimer}
      >
        Supprimer
      </Confirmer>
    </span>
  )
}

const etatValeur = (v: Valeur) => (v.actif ? 'active' : 'désactivée')

/** Les colonnes propres à une liste (libellé, famille, composition détaillée, valeur, unité). */
const PROPRES: readonly {
  cle: 'libelle' | 'famille' | 'composition_detaillee' | 'valeur' | 'unite'
  titre: string
}[] = [
  { cle: 'libelle', titre: 'Libellé' },
  { cle: 'famille', titre: 'Famille' },
  { cle: 'composition_detaillee', titre: 'Composition détaillée' },
  { cle: 'valeur', titre: 'Valeur' },
  { cle: 'unite', titre: 'Unité' },
]

function colonnes(d: DefinitionListe): Colonne<Valeur>[] {
  const code: Colonne<Valeur> = {
    cle: 'code',
    titre: 'Code',
    rendu: (v) => (
      <span className={v.actif ? styles.code : `${styles.code} ${styles.eteinte}`}>{v.code}</span>
    ),
  }
  const fin: Colonne<Valeur>[] = [
    {
      cle: 'commentaire',
      titre: 'Observations',
      rendu: (v) => (
        <span className={styles.coupe} title={v.commentaire}>
          {v.commentaire || VIDE}
        </span>
      ),
    },
    { cle: 'nb_matieres', titre: 'Matières', droite: true },
    {
      cle: 'actif',
      titre: 'État',
      valeur: etatValeur,
      rendu: (v) => <Badge ton={v.actif ? 'ok' : 'neutre'}>{etatValeur(v)}</Badge>,
    },
    { cle: 'gestes', titre: '', triable: false, exporte: false, rendu: (v) => <Gestes v={v} d={d} /> },
  ]
  const propres = PROPRES.filter((p) => d.champs.includes(p.cle)).map((p) => ({
    ...p,
    valeur: (v: Valeur) => v[p.cle] || VIDE,
  }))
  return [code, ...propres, ...fin]
}

function Valeurs({ d, c }: { d: DefinitionListe; c: Classification }) {
  const etat = useEtatListe('cq', ['desactivees'])
  const [ouverte, setOuverte] = useState<Valeur | 'nouvelle' | null>(null)
  const montrer = etat.lire('desactivees') === '1'
  const toutes = c[d.cle]
  const lignes = useMemo(() => toutes.filter((v) => montrer || v.actif), [toutes, montrer])
  const cols = useMemo(() => colonnes(d), [d])
  const desactivees = toutes.length - toutes.filter((v) => v.actif).length
  return (
    <>
      <Note>{d.note}</Note>
      <DataTable<Valeur>
        libelle={d.pluriel}
        lignes={lignes}
        colonnes={cols}
        cle={(v) => v.id}
        recherche={etat.recherche}
        choix={etat.choix}
        rechercheCachee={(v) => [v.commentaire, v.composition_detaillee]}
        placeholder={`Chercher dans les ${d.pluriel.toLowerCase()}…`}
        triInitial={{ cle: 'code', sens: 1 }}
        cliquable={(v) => setOuverte(v)}
        vide={
          toutes.length
            ? 'Aucune valeur ne correspond.'
            : 'Aucune valeur. « Relire les références » propose de les déduire des références du catalogue.'
        }
        outils={
          <>
            <Interrupteur
              valeur={montrer}
              onChange={(x) => etat.choix.poser('desactivees', x ? '1' : null)}
              libelle={`Montrer les valeurs désactivées (${nombre(desactivees)})`}
            />
            <Bouton variante="principal" icone="plus" onClick={() => setOuverte('nouvelle')}>
              {`Ajouter ${d.un}`}
            </Bouton>
          </>
        }
      />
      {ouverte ? (
        <ValeurClassification
          d={d}
          c={c}
          valeur={ouverte === 'nouvelle' ? null : ouverte}
          onFermer={() => setOuverte(null)}
        />
      ) : null}
    </>
  )
}

export function OngletClassification({ direction }: { direction: boolean }) {
  const lu = useClassification()
  const etat = useEtatListe('cq', ['liste'])
  const vue = VUES.find((v) => v === etat.lire('liste')) ?? 'compositions'
  const [classer, setClasser] = useState(false)
  const c = lu.data
  const vues = c
    ? [
        ...LISTES.map((d) => ({
          cle: d.liste,
          libelle: `${d.pluriel} · ${nombre(c[d.cle].filter((v) => v.actif).length)}`,
        })),
        { cle: 'roles' as const, libelle: `Rôles · ${nombre(c.roles.length)}` },
      ]
    : []
  const actions =
    vue === 'roles' ? null : (
      <Bouton
        titre="Lire les références et montrer ce qui serait complété, sans rien écrire"
        onClick={() => setClasser(true)}
      >
        Relire les références
      </Bouton>
    )
  return (
    <Carte titre="Classification des matières" actions={actions} remplir className={styles.carteListe}>
      {lu.isPending ? <Chargement quoi="la classification" /> : null}
      {lu.isError ? <Erreur erreur={lu.error} onReessayer={() => void lu.refetch()} /> : null}
      {c ? (
        <div className={styles.volet}>
          <Bascule<Vue>
            libelle="Liste de la classification"
            vues={vues}
            valeur={vue}
            onChange={(v) => etat.choix.poser('liste', v === 'compositions' ? null : v)}
          />
          {vue === 'roles' ? (
            <Roles c={c} direction={direction} />
          ) : (
            <Valeurs key={vue} d={definition(vue)} c={c} />
          )}
        </div>
      ) : null}
      {classer ? <Classer onFermer={() => setClasser(false)} /> : null}
    </Carte>
  )
}
