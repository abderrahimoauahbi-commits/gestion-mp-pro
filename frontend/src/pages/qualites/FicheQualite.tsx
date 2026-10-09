/**
 * La fiche d'une qualité en fenêtre très large (`/qualites/:id?onglet=recette|plan|versions|historique`).
 * Direction : fiche, poids et recette s'éditent ensemble et partent en **une** requête ; achats :
 * lecture, coûts compris ; alimentation : lecture sans coût ni prix (R10). Une version périmée se
 * recharge (« Recharger la qualité », R2) ; la saisie n'est jamais perdue sans question (R4).
 */
import { useMemo } from 'react'

import { Historique } from '../../composants/documents/Historique'
import { Fenetre } from '../../composants/mise-en-page/Fenetre'
import { Onglets } from '../../composants/mise-en-page/Onglets'
import { Badge } from '../../composants/retour/Badge'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { Note } from '../../composants/retour/Note'
import { useOngletAdresse } from '../../lib/adresse'
import type { Role } from '../../lib/types'
import { BandeauConflit } from '../catalogue/Conflit'
import { useClassification, useMatieres } from '../catalogue/donnees'
import type { Classification, Matiere } from '../catalogue/types'
import { rolesDansLOrdre } from './ChampsPoids'
import { useQualite, useQualites } from './donnees'
import { recetteChangee } from './formeQualite'
import { IndicateursFiche } from './IndicateursFiche'
import { PiedQualite } from './PiedQualite'
import { aCorriger, bilan, grouper } from './recette'
import type { Qualite, QualiteFiche } from './types'
import { useFicheQualite, type FicheQualiteEtat } from './useFicheQualite'
import { VoletPlan } from './VoletPlan'
import { VoletRecette } from './VoletRecette'
import { VoletVersions } from './VoletVersions'

type Volet = 'recette' | 'plan' | 'versions' | 'historique'
const VOLETS: readonly Volet[] = ['recette', 'plan', 'versions', 'historique']
const LIBELLES: Record<Volet, string> = {
  recette: 'Recette',
  plan: 'Plan de production',
  versions: 'Versions',
  historique: 'Historique',
}

/** Les autres qualités qui portent chaque matière (« Sert aussi à »). */
function autresQualites(qualites: readonly Qualite[], ici: number): Map<number, string[]> {
  const m = new Map<number, string[]>()
  for (const q of qualites) {
    if (q.id === ici) continue
    for (const l of q.recette)
      if (l.matiere_id != null) m.set(l.matiere_id, [...(m.get(l.matiere_id) ?? []), q.code])
  }
  return m
}

/** La recette calculée à la frappe : rôles, groupes, bilan, ce qui est à corriger. */
function useCalculs(
  f: FicheQualiteEtat,
  c: Classification,
  q: QualiteFiche,
  ecrit: boolean,
  voitPrix: boolean,
) {
  const roles = useMemo(() => rolesDansLOrdre(c.roles), [c.roles])
  const poids = new Map(Object.entries(f.forme.poids).map(([k, v]) => [Number(k), v ?? 0]))
  const groupes = grouper(roles, poids, f.forme.lignes, voitPrix ? q.facteurs_cout : null)
  const b = bilan(groupes)
  const corriger = ecrit ? aCorriger(b, f.forme.actif, recetteChangee(f.forme, f.initiale)) : []
  return { roles, groupes, b, corriger }
}

function Titre({ q }: { q: QualiteFiche }) {
  return (
    <>
      Qualité {q.code}
      {q.nom ? ` — ${q.nom}` : ''} {q.actif ? null : <Badge ton="neutre">arrêtée</Badge>}
    </>
  )
}

interface ContenuProps {
  fiche: QualiteFiche
  role: Role
  c: Classification
  matieres: readonly Matiere[]
  qualites: readonly Qualite[]
  onFermer: () => void
}

function Contenu({ fiche, role, c, matieres, qualites, onFermer }: ContenuProps) {
  const ecrit = role === 'direction'
  const voitPrix = ecrit || role === 'achats'
  const f = useFicheQualite(fiche, onFermer)
  const q = f.base ?? fiche
  const [volet, choisir] = useOngletAdresse(VOLETS, 'recette')
  const { roles, groupes, b, corriger } = useCalculs(f, c, q, ecrit, voitPrix)
  const autres = useMemo(() => autresQualites(qualites, q.id), [qualites, q.id])
  return (
    <Fenetre
      titre={<Titre q={q} />}
      onFermer={onFermer}
      sale={ecrit && f.sale}
      taille="tresLarge"
      pied={<PiedQualite f={f} ecrit={ecrit} corriger={corriger} />}
    >
      {ecrit ? null : <Note>Lecture seule : seule la direction modifie les qualités et les recettes.</Note>}
      <BandeauConflit message={f.conflit} onRecharger={f.recharger} libelle="Recharger la qualité" />
      <IndicateursFiche b={b} base={q.base_mensuelle} voitPrix={voitPrix} sale={f.sale} />
      <Onglets<Volet>
        libelle="Volets de la qualité"
        actif={volet}
        onChange={choisir}
        onglets={VOLETS.map((v) => ({
          cle: v,
          libelle: LIBELLES[v],
          compte: v === 'recette' ? b.matieres : null,
          sale: v === 'recette' && f.sale,
        }))}
      />
      {volet === 'recette' ? (
        <VoletRecette
          f={f}
          roles={roles}
          groupes={groupes}
          matieres={matieres}
          autres={autres}
          ecrit={ecrit}
          voitPrix={voitPrix}
        />
      ) : null}
      {volet === 'plan' ? <VoletPlan q={q} /> : null}
      {volet === 'versions' ? <VoletVersions f={f} ecrit={ecrit} matieres={matieres} /> : null}
      {volet === 'historique' ? <Historique objet="qualite" id={q.id} /> : null}
    </Fenetre>
  )
}

export function FicheQualite({ id, role, onFermer }: { id: number; role: Role; onFermer: () => void }) {
  const fiche = useQualite(id)
  const c = useClassification()
  const matieres = useMatieres()
  const qualites = useQualites()
  const echec = [fiche, c, matieres].find((l) => l.isError)
  if (echec)
    return (
      <Fenetre titre="Qualité" onFermer={onFermer}>
        <Erreur erreur={echec.error} onReessayer={() => void echec.refetch()} />
      </Fenetre>
    )
  if (!fiche.data || !c.data || !matieres.data)
    return (
      <Fenetre titre="Qualité" onFermer={onFermer}>
        <Chargement quoi="la qualité" />
      </Fenetre>
    )
  return (
    <Contenu
      fiche={fiche.data}
      role={role}
      c={c.data}
      matieres={matieres.data}
      qualites={qualites.data ?? []}
      onFermer={onFermer}
    />
  )
}
