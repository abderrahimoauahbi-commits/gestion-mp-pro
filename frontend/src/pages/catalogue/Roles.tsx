/**
 * Les rôles de nomenclature (vue « Rôles » de la classification) : le rôle d'une matière dans
 * le tapis, dans l'ordre des listes et des colonnes. La direction ajoute un rôle (toujours compté
 * au kilo : seuls Cuir, Franges, Ruban vont au mètre), le renomme (un rôle de base garde son nom)
 * ou change son ordre, le supprime s'il n'est porté par rien ; les achats lisent.
 */
import { useState } from 'react'

import { Fenetre, useFermerFenetre } from '../../composants/mise-en-page/Fenetre'
import { Grille } from '../../composants/mise-en-page/Grille'
import { Badge } from '../../composants/retour/Badge'
import { dire } from '../../composants/retour/Messages'
import { Note } from '../../composants/retour/Note'
import { Bouton } from '../../composants/saisie/Bouton'
import { Champ } from '../../composants/saisie/Champ'
import { Confirmer } from '../../composants/saisie/Confirmer'
import { Nombre } from '../../composants/saisie/Nombre'
import { Saisie } from '../../composants/saisie/Saisie'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { api, ErreurApi } from '../../lib/api'
import { nombre } from '../../lib/format'
import { useEcriture } from '../../lib/requetes'
import { LONGUEURS } from './bornes'
import styles from './catalogue.module.css'
import { BandeauConflit } from './Conflit'
import type { Classification, RoleNomenclature } from './types'
import { useFiche, type Fiche } from './useFiche'

/** Ce qui empêche de supprimer un rôle (même règle que le serveur). */
export function blocagesRole(r: RoleNomenclature): string[] {
  if (r.de_base) return ['Rôle du calcul : il ne se supprime pas']
  if (r.nb_matieres || r.nb_qualites)
    return [
      `Porté par ${nombre(r.nb_matieres)} matière(s) et ${nombre(r.nb_qualites)} qualité(s) : les changer d’abord`,
    ]
  return []
}

function SupprimerRole({ r }: { r: RoleNomenclature }) {
  const ecriture = useEcriture(() => api.supprimer(`/classification/roles/${r.id}`))
  return (
    <span onClick={(e) => e.stopPropagation()} onKeyDown={(e) => e.stopPropagation()}>
      <Confirmer
        taille="petit"
        variante="danger"
        question={`Supprimer le rôle « ${r.code} » ?`}
        oui="Oui, supprimer"
        blocages={blocagesRole(r)}
        titre="Supprimer ce rôle, qu’aucune matière ni qualité ne porte"
        onOui={async () => {
          await ecriture.mutateAsync()
          dire(`Rôle « ${r.code} » supprimé.`)
        }}
      >
        Supprimer
      </Confirmer>
    </span>
  )
}

function colonnes(direction: boolean): Colonne<RoleNomenclature>[] {
  const base: Colonne<RoleNomenclature>[] = [
    {
      cle: 'code',
      titre: 'Rôle',
      rendu: (r) => (
        <>
          <span className={styles.fort}>{r.code}</span>
          {r.de_base ? <span className={styles.note}> · rôle du calcul</span> : null}
        </>
      ),
    },
    {
      cle: 'lineaire',
      titre: 'Compté',
      valeur: (r) => (r.lineaire ? 'au mètre (ml)' : 'au kilo'),
      rendu: (r) => (r.lineaire ? <Badge ton="accent">au mètre (ml)</Badge> : 'au kilo'),
    },
    { cle: 'ordre', titre: 'Ordre', droite: true },
    { cle: 'nb_matieres', titre: 'Matières', droite: true },
    {
      cle: 'nb_qualites',
      titre: 'Qualités',
      aide: 'Qualités qui portent le rôle (poids au m² > 0)',
      droite: true,
    },
  ]
  return direction
    ? [
        ...base,
        { cle: 'gestes', titre: '', triable: false, exporte: false, rendu: (r) => <SupprimerRole r={r} /> },
      ]
    : base
}

function AjoutRole({ prochain }: { prochain: number }) {
  const [code, setCode] = useState('')
  const [ordre, setOrdre] = useState<number | null>(null)
  const ecriture = useEcriture((corps: { code: string; ordre: number }) =>
    api.post<RoleNomenclature>('/classification/roles', corps),
  )
  const ajouter = async () => {
    const r = await ecriture.mutateAsync({ code: code.trim(), ordre: ordre ?? prochain })
    dire(`Rôle « ${r.code} » ajouté : il se choisit pour une matière et reçoit un poids dans chaque qualité.`)
    setCode('')
    setOrdre(null)
  }
  return (
    <Grille colonnes={3}>
      <Champ libelle="Nouveau rôle" aide="toujours compté au kilo (seuls Cuir, Franges, Ruban vont au mètre)">
        <Saisie valeur={code} onChange={setCode} max={LONGUEURS.CODE_ROLE} placeholder="Velours…" />
      </Champ>
      <Champ libelle="Ordre" aide="l’ordre des listes et des colonnes">
        <Nombre valeur={ordre ?? prochain} onChange={setOrdre} min={0} max={999} decimales={0} />
      </Champ>
      <Champ libelle="Ajout" groupe>
        <Bouton
          variante="principal"
          manque={code.trim() ? undefined : ['le nom du rôle']}
          attente="Ajout…"
          onClick={ajouter}
        >
          Ajouter le rôle
        </Bouton>
      </Champ>
    </Grille>
  )
}

function PiedRole({
  change,
  enregistrer,
  manque,
}: {
  change: boolean
  enregistrer: () => Promise<void>
  manque?: string[]
}) {
  const fermer = useFermerFenetre()
  return (
    <div className={styles.pied}>
      <span className={styles.pousse} />
      <Bouton variante="fantome" onClick={fermer}>
        {change ? 'Annuler' : 'Fermer'}
      </Bouton>
      <Bouton
        variante="principal"
        manque={manque}
        grise={change ? undefined : 'Aucune modification.'}
        attente="Enregistrement…"
        onClick={enregistrer}
      >
        Enregistrer
      </Bouton>
    </div>
  )
}

interface FormeRole {
  code: string
  ordre: number | null
}

const egalRole = (a: FormeRole, b: FormeRole) => a.code.trim() === b.code.trim() && a.ordre === b.ordre

function ChampsRole({ f, deBase }: { f: Fiche<RoleNomenclature, FormeRole>; deBase: boolean }) {
  return (
    <Grille colonnes={2}>
      <Champ
        libelle="Nom du rôle"
        obligatoire
        aide={deBase ? 'rôle du calcul : le nom reste' : 'le renommer le renomme partout'}
      >
        <Saisie
          valeur={f.forme.code}
          onChange={(v) => f.maj({ code: v })}
          max={LONGUEURS.CODE_ROLE}
          desactive={deBase}
        />
      </Champ>
      <Champ libelle="Ordre" aide="l’ordre des listes et des colonnes">
        <Nombre
          valeur={f.forme.ordre}
          onChange={(v) => f.maj({ ordre: v })}
          min={0}
          max={999}
          decimales={0}
        />
      </Champ>
    </Grille>
  )
}

function FenetreRole({ role, onFermer }: { role: RoleNomenclature; onFermer: () => void }) {
  const f = useFiche<RoleNomenclature, FormeRole>(
    role,
    (x) => ({ code: x?.code ?? '', ordre: x?.ordre ?? 0 }),
    egalRole,
  )
  const r = f.base ?? role
  const enregistrer = async () => {
    const corps = { code: f.forme.code.trim(), ordre: f.forme.ordre ?? 0, version: r.version }
    if (
      await f.ecrire(
        () => api.put<RoleNomenclature>(`/classification/roles/${r.id}`, corps),
        'Rôle enregistré.',
      )
    )
      onFermer()
  }
  const recharger = () =>
    f.recharger(async () => {
      const lu = (await api.get<Classification>('/classification')).roles.find((x) => x.id === r.id)
      if (!lu) throw new ErreurApi('Rôle introuvable.', 404, 'introuvable')
      return lu
    })
  return (
    <Fenetre
      titre={`Rôle « ${r.code} »`}
      onFermer={onFermer}
      sale={f.sale}
      pied={
        <PiedRole
          change={f.sale && !f.conflit}
          enregistrer={enregistrer}
          manque={f.forme.code.trim() ? undefined : ['le nom du rôle']}
        />
      }
    >
      <BandeauConflit message={f.conflit} onRecharger={recharger} />
      {r.de_base ? (
        <Note>« {r.code} » est un rôle de base du calcul : il garde son nom ; son ordre se change.</Note>
      ) : null}
      <ChampsRole f={f} deBase={r.de_base} />
    </Fenetre>
  )
}

export function Roles({ c, direction }: { c: Classification; direction: boolean }) {
  const [ouvert, setOuvert] = useState<RoleNomenclature | null>(null)
  const prochain = Math.max(0, ...c.roles.map((r) => r.ordre)) + 1
  return (
    <>
      <Note>
        Le rôle d’une matière dans le tapis : il dit dans quelle colonne de la recette elle entre, et comment
        elle se compte (au kilo, ou au mètre pour le cuir, les franges, le ruban). L’ordre est celui des
        listes et des colonnes.
        {direction ? '' : ' Seule la direction ajoute ou modifie un rôle.'}
      </Note>
      {direction ? <AjoutRole prochain={prochain} /> : null}
      <DataTable<RoleNomenclature>
        libelle="Rôles de nomenclature"
        lignes={c.roles}
        colonnes={colonnes(direction)}
        cle={(r) => r.id}
        recherche={false}
        triInitial={{ cle: 'ordre', sens: 1 }}
        cliquable={direction ? setOuvert : undefined}
      />
      {ouvert ? <FenetreRole role={ouvert} onFermer={() => setOuvert(null)} /> : null}
    </>
  )
}
