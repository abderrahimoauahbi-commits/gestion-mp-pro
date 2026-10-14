/**
 * Un fil monté sur l'étage : son poids de bobine retenu (et d'où il vient), les mètres montés
 * (0…1000, pas 0,1), le remplissage des bobines (0…100 %, pas 5, borné aussi à la frappe, an. 12), les
 * observations, ce qu'il fait en bobines et en kilos ; « Retirer ce fil ».
 */
import { Compteur } from '../../composants/atelier/Compteur'
import { Bouton } from '../../composants/saisie/Bouton'
import { Champ } from '../../composants/saisie/Champ'
import { Saisie } from '../../composants/saisie/Saisie'
import { kgTelephone, nombre, poidsBobine } from '../../lib/format'
import { Fiche, Ligne, NoteAtelier } from './briques'
import styles from './atelier.module.css'
import { bobinesDe, type FilSaisi } from './calculMontage'
import type { MatiereMontage, MetierFiche } from './types'
import type { MontageEtage } from './useMontageEtage'

/** « Poil acrylique rouge · 2,5 kg / bobine · lot L-2601 (sorti) » (poids de bobine : 2 décimales au plus). */
export function detailFil(f: FilSaisi, poids: number, origine: string): string {
  const debut = f.designation ? `${f.designation} · ` : ''
  if (!poids) return `${debut}poids de bobine inconnu : ce fil ne pèse rien`
  return `${debut}${poidsBobine(poids)}${origine ? ` · ${origine}` : ''}`
}

export function CarteFil({
  m,
  f,
  t,
  poids,
  matieres,
}: {
  m: MetierFiche
  f: FilSaisi
  t: MontageEtage
  poids: number
  matieres?: MatiereMontage[]
}) {
  const changer = (c: Partial<FilSaisi>) =>
    t.poserFils(t.s.fils.map((x) => (x.matiere_id === f.matiere_id ? { ...x, ...c } : x)))
  const origine = matieres?.find((x) => x.matiere_id === f.matiere_id)?.origine_poids ?? ''
  const kgFil = (bobinesDe(m, f) * poids * f.pourcentage) / 100
  return (
    <Fiche titre={f.reference} ton={f.metres > 0 ? undefined : 'alerte'} libelle={f.reference}>
      <NoteAtelier>{detailFil(f, poids, origine)}</NoteAtelier>
      <Champ groupe libelle="Mètres montés">
        <Compteur
          libelle={`Mètres montés de ${f.reference}`}
          valeur={f.metres}
          uniteDite="m"
          pas={0.1}
          min={0}
          max={1000}
          decimales={2}
          onChange={(v) => changer({ metres: v ?? 0 })}
        />
      </Champ>
      <Champ groupe libelle="Bobines pleines (%)">
        <Compteur
          libelle={`Bobines pleines de ${f.reference} (%)`}
          valeur={f.pourcentage}
          uniteDite="%"
          pas={5}
          min={0}
          max={100}
          decimales={2}
          onChange={(v) => changer({ pourcentage: v ?? 0 })}
        />
      </Champ>
      <Champ libelle="Observations">
        <Saisie valeur={f.commentaire} max={300} onChange={(commentaire) => changer({ commentaire })} />
      </Champ>
      <Ligne libelle={`${nombre(bobinesDe(m, f))} bobines`}>{kgTelephone(kgFil)}</Ligne>
      <div className={styles.adroite}>
        <Bouton
          taille="atelier"
          variante="danger"
          onClick={() => t.poserFils(t.s.fils.filter((x) => x.matiere_id !== f.matiere_id))}
        >
          Retirer ce fil
        </Bouton>
      </div>
    </Fiche>
  )
}
