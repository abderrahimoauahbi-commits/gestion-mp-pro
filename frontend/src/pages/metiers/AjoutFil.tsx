/**
 * Monter un fil depuis la fiche du métier : l'étage (« Étage 2 (3,10 / 4,20 m) »), puis la
 * matière (matières au poids, actives, pas déjà sur cet étage), avec le poids de bobine que le
 * montage retiendra — le même qu'au téléphone (an. 11). Le fil prend les mètres restants, 100 %.
 */
import { useState } from 'react'

import { Champ } from '../../composants/saisie/Champ'
import { Selecteur } from '../../composants/saisie/Selecteur'
import { nombre } from '../../lib/format'
import { largeurs, type FilForme } from './formeMetier'
import styles from './metiers.module.css'
import type { FicheMetierEtat } from './useFicheMetier'

let compteur = 0

export function AjoutFil({ e }: { e: FicheMetierEtat }) {
  const [etage, setEtage] = useState<number | null>(1)
  const laize = e.forme.laize ?? 0
  const occupe = largeurs(e.forme)
  const nb = e.forme.etages ?? 0
  const deja = new Set(e.forme.fils.filter((f) => f.etage === etage).map((f) => f.matiere_id))
  const options = (e.matieres ?? [])
    .filter((x) => x.actif && !deja.has(x.matiere_id))
    .map((x) => ({
      id: x.matiere_id,
      titre: x.designation ? `${x.reference} — ${x.designation}` : x.reference,
      sous: x.poids_bobine_compte
        ? `${nombre(x.poids_bobine_compte, 3)} kg / bobine`
        : 'poids de bobine inconnu',
    }))
  const ajouter = (id: number | null) => {
    const x = e.matieres?.find((y) => y.matiere_id === id)
    if (!x || etage == null) return
    const fil: FilForme = {
      cle: `n${++compteur}`,
      matiere_id: x.matiere_id,
      reference: x.reference,
      designation: x.designation,
      etage,
      metres: Math.max(0, Math.round((laize - (occupe.get(etage) ?? 0)) * 100) / 100),
      pourcentage: 100,
      commentaire: '',
    }
    e.maj({ fils: [...e.forme.fils, fil] })
  }
  return (
    <div className={styles.ajout}>
      <Champ libelle="Monter à l’étage">
        <Selecteur
          valeur={etage}
          effacable={false}
          options={Array.from({ length: nb }, (_, i) => i + 1).map((n) => ({
            id: n,
            titre: `Étage ${n} (${nombre(occupe.get(n) ?? 0, 2)} / ${nombre(laize, 2)} m)`,
          }))}
          onChange={setEtage}
        />
      </Champ>
      <Champ libelle="Fil à monter">
        <Selecteur
          valeur={null}
          placeholder="Taper quelques mots : référence, couleur…"
          options={options}
          onChange={ajouter}
        />
      </Champ>
    </div>
  )
}
