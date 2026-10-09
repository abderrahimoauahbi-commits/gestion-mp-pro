/**
 * Onglet « Recette » de la fiche qualité : la fiche et les poids au m² **en tête** (ils
 * commandent la recette, ECRANS-PRO partie 7), puis la recette groupée par rôle et l'ajout d'une
 * matière (elle rejoint son rôle, avec la part qui lui reste). Les achats et l'alimentation lisent.
 */
import { useMemo } from 'react'

import { Grille } from '../../composants/mise-en-page/Grille'
import { Note } from '../../composants/retour/Note'
import { Vide } from '../../composants/retour/Vide'
import { Blocages } from '../../composants/saisie/Blocages'
import { Champ } from '../../composants/saisie/Champ'
import { Interrupteur } from '../../composants/saisie/Interrupteur'
import { Saisie } from '../../composants/saisie/Saisie'
import { SelecteurMatiere } from '../../composants/saisie/SelecteurMatiere'
import styles from '../catalogue/catalogue.module.css'
import type { Matiere } from '../catalogue/types'
import { ChampsPoids } from './ChampsPoids'
import { depuisMatiere } from './formeQualite'
import { CODE_MAX, NOM_MAX } from './NouvelleQualite'
import { reste, type GroupeRole, type RoleQualite } from './recette'
import { TableRecette } from './TableRecette'
import type { FicheQualiteEtat } from './useFicheQualite'

export interface VoletRecetteProps {
  f: FicheQualiteEtat
  roles: readonly RoleQualite[]
  groupes: readonly GroupeRole[]
  matieres: readonly Matiere[]
  autres: ReadonlyMap<number, readonly string[]>
  ecrit: boolean
  voitPrix: boolean
}

function BlocFiche({ f, roles, ecrit }: VoletRecetteProps) {
  return (
    <>
      <Grille colonnes={3}>
        <Champ libelle="Code" obligatoire>
          <Saisie
            valeur={f.forme.code}
            onChange={(v) => f.maj({ code: v })}
            max={CODE_MAX}
            desactive={!ecrit}
          />
        </Champ>
        <Champ libelle="Nom">
          <Saisie valeur={f.forme.nom} onChange={(v) => f.maj({ nom: v })} max={NOM_MAX} desactive={!ecrit} />
        </Champ>
        <Champ libelle="État" groupe aide="une qualité arrêtée ne compte plus dans le plan">
          <Interrupteur
            valeur={f.forme.actif}
            onChange={(v) => f.maj({ actif: v })}
            libelle="qualité fabriquée (active)"
            desactive={!ecrit}
          />
        </Champ>
      </Grille>
      <strong>Poids d’un m² de tapis, rôle par rôle</strong>
      <ChampsPoids roles={roles} poids={f.forme.poids} onChange={f.poser} lecture={!ecrit} />
    </>
  )
}

function Ajout({ f, groupes, matieres }: VoletRecetteProps) {
  const presentes = new Set(f.forme.lignes.map((l) => l.matiere_id))
  const pesants = new Map(groupes.filter((g) => g.poids > 0).map((g) => [g.role_id, g]))
  const proposees = matieres.filter((m) => m.actif && pesants.has(m.role_id) && !presentes.has(m.id))
  const choix = proposees.map((m) => ({
    id: m.id,
    reference: m.reference,
    designation: `${m.designation ? `${m.designation} · ` : ''}${m.role}`,
    composition: m.composition,
    type: m.type_fil,
    titrage: m.titrage,
    couleur: m.couleur,
    fournisseur: m.fournisseur,
  }))
  return (
    <div className={styles.panneau}>
      <strong>Ajouter une matière (elle rejoint son rôle) :</strong>
      <SelecteurMatiere
        matieres={choix}
        valeur={null}
        libelle="Matière à ajouter"
        onChange={(id) => {
          const m = proposees.find((x) => x.id === id)
          if (m) f.ajouter(depuisMatiere(m, reste(pesants.get(m.role_id)?.somme ?? 0)))
        }}
      />
    </div>
  )
}

export function VoletRecette(p: VoletRecetteProps) {
  const { f, groupes, ecrit } = p
  const disparues = useMemo(
    () => f.forme.lignes.filter((l) => l.disparue).map((l) => l.reference),
    [f.forme.lignes],
  )
  const sansMatiere = groupes.filter((g) => g.etat === 'vide' && g.poids > 0).map((g) => g.role)
  return (
    <div className={styles.volet}>
      <BlocFiche {...p} />
      <Note>
        Dans chaque rôle utilisé, les parts des matières totalisent 100 %. Un rôle à zéro n’entre pas dans la
        qualité ; en rouge, le rôle n’y est pas encore.
      </Note>
      {disparues.length ? (
        <Note ton="critique">
          {disparues.length} ligne(s) de la recette visent une matière disparue du catalogue (
          {disparues.join(', ')}) : elles seront retirées à l’enregistrement.
        </Note>
      ) : null}
      {sansMatiere.length ? (
        <Blocages
          titre="Rôle(s) avec un poids au m² mais sans matière :"
          blocages={[
            `${sansMatiere.join(', ')} — leurs kilos manqueraient aux besoins et aux sorties : ajouter une matière avant d’enregistrer`,
          ]}
        />
      ) : null}
      {groupes.length ? (
        <TableRecette
          groupes={groupes}
          voitPrix={p.voitPrix}
          ecrit={ecrit}
          autres={p.autres}
          onPart={(id, v) => f.changerLigne(id, { pourcentage: v ?? 0 })}
          onRetirer={(id) => f.changerLigne(id, null)}
        />
      ) : (
        <Vide>Aucun rôle n’a de poids : renseigner d’abord les poids au m² (en tête de cet onglet).</Vide>
      )}
      {ecrit && groupes.some((g) => g.poids > 0) ? <Ajout {...p} /> : null}
    </div>
  )
}
