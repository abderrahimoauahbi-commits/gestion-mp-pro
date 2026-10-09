/**
 * Réglages › Magasins (`/reglages?onglet=magasins`, fenêtre `&magasin=ID|nouveau`) : les magasins
 * de stock courant et de quarantaine, et ce qu'ils détiennent. La direction écrit, les achats
 * lisent. Un magasin qui détient de la matière ne change pas de type et ne se désactive pas : le
 * bouton le dit avant le clic (P8-7) ; il reste toujours un magasin en service de chaque type.
 */
import { useState } from 'react'
import { useSearchParams } from 'react-router'

import { Carte } from '../../composants/mise-en-page/Carte'
import { Fenetre, useFermerFenetre } from '../../composants/mise-en-page/Fenetre'
import { Grille } from '../../composants/mise-en-page/Grille'
import { Badge } from '../../composants/retour/Badge'
import { dire } from '../../composants/retour/Messages'
import { Note } from '../../composants/retour/Note'
import { Bouton } from '../../composants/saisie/Bouton'
import { Champ } from '../../composants/saisie/Champ'
import { Saisie } from '../../composants/saisie/Saisie'
import { Segments } from '../../composants/saisie/Segments'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { avecParametre } from '../../lib/adresse'
import { api } from '../../lib/api'
import { kg } from '../../lib/format'
import { useEcriture } from '../../lib/requetes'
import type { Schema } from '../../lib/types'
import styles from './reglages.module.css'

export type MagasinFiche = Schema<'MagasinFiche'>

const TYPES = [
  { valeur: 'stock_courant', libelle: 'Stock courant' },
  { valeur: 'quarantaine', libelle: 'Quarantaine' },
] as const

const CONTENUS = [
  'Tout',
  'Fils',
  'Fils PP',
  'Fils PES',
  'Chaîne et trame',
  'Colles et intrants',
  'Franges et cuir',
]

const detient = (m: MagasinFiche | undefined) => (m?.kg_detenus ?? 0) > 0.001

const COLONNES: readonly Colonne<MagasinFiche>[] = [
  { cle: 'code', titre: 'Code', rendu: (m) => <span className={styles.code}>{m.code}</span> },
  { cle: 'nom', titre: 'Nom' },
  {
    cle: 'type',
    titre: 'Type',
    rendu: (m) =>
      m.type === 'quarantaine' ? (
        <Badge ton="attention">Quarantaine</Badge>
      ) : (
        <Badge ton="neutre">Stock courant</Badge>
      ),
  },
  { cle: 'contenu', titre: 'Contenu', rendu: (m) => m.contenu || <span className={styles.note}>Tout</span> },
  {
    cle: 'kg_detenus',
    titre: 'Stock détenu (kg)',
    droite: true,
    unite: 'kg',
    total: true,
    rendu: (m) => kg(m.kg_detenus),
  },
  {
    cle: 'actif',
    titre: 'État',
    valeur: (m) => (m.actif ? 'actif' : 'désactivé'),
    rendu: (m) => (m.actif ? <Badge ton="ok">actif</Badge> : <Badge ton="neutre">désactivé</Badge>),
  },
]

interface Forme {
  code: string
  nom: string
  type: string
  contenu: string
  actif: boolean
}

const formeDe = (m: MagasinFiche | undefined): Forme =>
  m
    ? { code: m.code, nom: m.nom, type: m.type, contenu: m.contenu, actif: m.actif }
    : { code: '', nom: '', type: 'stock_courant', contenu: '', actif: true }

/** Ce que le serveur refuserait, dit sur le bouton. */
export function blocagesMagasin(m: MagasinFiche | undefined, f: Forme): string[] {
  if (!detient(m) || !m) return []
  return [
    ...(f.type !== m.type ? ['Un magasin qui détient de la matière ne change pas de type.'] : []),
    ...(!f.actif && m.actif
      ? [`Ce magasin détient encore ${kg(m.kg_detenus)} : transférer la matière avant de le désactiver.`]
      : []),
  ]
}

function PiedMagasin({
  m,
  f,
  sale,
  ecrit,
  onFait,
}: {
  m?: MagasinFiche
  f: Forme
  sale: boolean
  ecrit: boolean
  onFait: () => void
}) {
  const fermer = useFermerFenetre()
  const corps = { ...f, code: f.code.trim(), nom: f.nom.trim(), contenu: f.contenu.trim() }
  const ecrire = useEcriture(() =>
    m
      ? api.put<MagasinFiche>(`/magasins/${m.id}`, { ...corps, version: m.version })
      : api.post<MagasinFiche>('/magasins', corps),
  )
  return (
    <>
      <Bouton variante="fantome" onClick={fermer}>
        {sale ? 'Abandonner les modifications' : 'Fermer'}
      </Bouton>
      {ecrit ? (
        <Bouton
          variante="principal"
          manque={f.code.trim() ? [] : ['le code']}
          grise={m && !sale ? 'Aucune modification' : undefined}
          blocages={blocagesMagasin(m, f)}
          attente="Enregistrement…"
          onClick={async () => {
            await ecrire.mutateAsync()
            dire(m ? 'Magasin enregistré.' : `Magasin ${corps.code} créé.`)
            onFait()
          }}
        >
          {m ? 'Enregistrer' : 'Créer le magasin'}
        </Bouton>
      ) : null}
    </>
  )
}

function FenetreMagasin({ m, ecrit, onFermer }: { m?: MagasinFiche; ecrit: boolean; onFermer: () => void }) {
  const [f, setF] = useState(() => formeDe(m))
  const sale = JSON.stringify(f) !== JSON.stringify(formeDe(m))
  const poser = (champ: Partial<Forme>) => setF({ ...f, ...champ })
  return (
    <Fenetre
      titre={m ? `Magasin ${m.code}` : 'Nouveau magasin'}
      onFermer={onFermer}
      sale={sale}
      pied={<PiedMagasin m={m} f={f} sale={sale} ecrit={ecrit} onFait={onFermer} />}
    >
      <Grille colonnes={2}>
        <Champ libelle="Code" obligatoire>
          <Saisie valeur={f.code} max={64} desactive={!ecrit} onChange={(v) => poser({ code: v })} />
        </Champ>
        <Champ libelle="Nom">
          <Saisie valeur={f.nom} max={120} desactive={!ecrit} onChange={(v) => poser({ nom: v })} />
        </Champ>
        <Champ
          libelle="Type"
          groupe
          aide={detient(m) ? 'il détient de la matière : son type ne change plus' : undefined}
        >
          <Segments
            libelle="Type"
            valeur={f.type}
            options={TYPES}
            desactive={!ecrit || detient(m)}
            onChange={(v) => poser({ type: v })}
          />
        </Champ>
        <Champ
          libelle="Contenu"
          aide="ce qu’on y range : « Tout », « Fils PP », « Colles et intrants »… ; vide = Tout"
        >
          <Saisie valeur={f.contenu} max={120} desactive={!ecrit} onChange={(v) => poser({ contenu: v })} />
        </Champ>
      </Grille>
      <span className={styles.note}>Suggestions : {CONTENUS.join(', ')}.</span>
      <label className={styles.case}>
        <input
          type="checkbox"
          checked={f.actif}
          disabled={!ecrit}
          onChange={(e) => poser({ actif: e.target.checked })}
        />
        magasin actif
      </label>
      {blocagesMagasin(m, f).map((b) => (
        <Note key={b} ton="attention">
          {b}
        </Note>
      ))}
    </Fenetre>
  )
}

export function Magasins({ magasins, ecrit }: { magasins: readonly MagasinFiche[]; ecrit: boolean }) {
  const [params, setParams] = useSearchParams()
  const ouvert = params.get('magasin')
  const ouvrir = (v: string | null) => setParams((p) => avecParametre(p, 'magasin', v))
  const m = magasins.find((x) => String(x.id) === ouvert)
  return (
    <Carte
      titre="Les magasins"
      actions={
        ecrit ? (
          <Bouton variante="principal" icone="plus" onClick={() => ouvrir('nouveau')}>
            Nouveau magasin
          </Bouton>
        ) : null
      }
      serre
      remplir
      className={styles.carteListe}
    >
      <Note>
        « Stock courant » : la matière disponible pour les machines. « Quarantaine » : la matière reçue sous
        réserve, qui attend une décision avant de servir (comptée dans le stock et sa valeur, mais ni proposée
        aux machines, ni comptée dans le disponible). Cliquer sur un magasin pour{' '}
        {ecrit ? 'le modifier' : 'le voir'}.
      </Note>
      <DataTable<MagasinFiche>
        libelle="Magasins"
        lignes={[...magasins].sort((a, b) => a.type.localeCompare(b.type) || a.code.localeCompare(b.code))}
        colonnes={COLONNES}
        cle={(x) => x.id}
        recherche={false}
        cliquable={(x) => ouvrir(String(x.id))}
        vide="Aucun magasin."
      />
      {ouvert === 'nouveau' && ecrit ? <FenetreMagasin ecrit onFermer={() => ouvrir(null)} /> : null}
      {m ? <FenetreMagasin key={m.id} m={m} ecrit={ecrit} onFermer={() => ouvrir(null)} /> : null}
    </Carte>
  )
}
