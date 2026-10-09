/**
 * Volet « Classification et référence » de la fiche matière : composition, type de fil, titrage,
 * couleur (avec ajout sur place), code couleur, suffixe du fournisseur ; la référence composée
 * semi-automatiquement (`useReference.ts`), la désignation, le rôle dans le tapis et, pour un
 * rôle au mètre (cuir, franges, ruban), la densité qui ramène les mètres aux kilos.
 */
import { Grille } from '../../composants/mise-en-page/Grille'
import { Bouton } from '../../composants/saisie/Bouton'
import { Champ } from '../../composants/saisie/Champ'
import { Saisie } from '../../composants/saisie/Saisie'
import { Selecteur } from '../../composants/saisie/Selecteur'
import { LONGUEURS, SUFFIXE_MAX } from './bornes'
import { ChampDensite } from './ChampDensite'
import { ChoixClasse } from './ChoixClasse'
import { avecClasse, type FormeMatiere } from './formeMatiere'
import styles from './catalogue.module.css'
import { LISTES, type Classification } from './types'
import type { ReferenceComposee } from './useReference'

export interface VoletClassificationProps {
  forme: FormeMatiere
  maj: (modif: Partial<FormeMatiere>) => void
  c: Classification
  composee: ReferenceComposee | null
  /** La référence a été retouchée à la main (ou la matière existe) : la composée est proposée. */
  libre: boolean
  onRetouche: () => void
  /** Une autre matière porte déjà cette référence. */
  doublon: boolean
}

/** L'aide sous la référence : composée, proposée, ou en double. */
function AideReference({
  forme,
  composee,
  libre,
  onReprendre,
}: Pick<VoletClassificationProps, 'forme' | 'composee' | 'libre'> & { onReprendre: () => void }) {
  if (!composee) return <>Choisir la classification : la référence s’écrit seule.</>
  if (!libre) return <>composée à partir de la classification</>
  if (composee.reference === forme.reference.trim()) return <>conforme à la classification</>
  return (
    <>
      La classification compose : <span className={styles.code}>{composee.reference}</span>
      {composee.existe ? ' (déjà au catalogue)' : ''}{' '}
      <Bouton taille="petit" variante="fantome" onClick={onReprendre}>
        la reprendre
      </Bouton>
    </>
  )
}

/** La référence (composée ou retouchée) et la désignation. */
function ChampsReference(p: VoletClassificationProps) {
  const { forme, maj, composee } = p
  const reprendre = () =>
    composee && maj({ reference: composee.reference, designation: composee.designation || forme.designation })
  return (
    <>
      <Champ
        libelle="Référence"
        obligatoire
        large
        erreur={p.doublon ? 'Une autre matière porte déjà cette référence.' : undefined}
        aide={<AideReference forme={forme} composee={composee} libre={p.libre} onReprendre={reprendre} />}
      >
        <Saisie
          valeur={forme.reference}
          onChange={(v) => {
            p.onRetouche()
            maj({ reference: v })
          }}
          max={LONGUEURS.REFERENCE}
          className={styles.code}
        />
      </Champ>
      <Champ libelle="Désignation" aide="composée : couleur de l’atelier et code couleur">
        <Saisie
          valeur={forme.designation}
          onChange={(v) => maj({ designation: v })}
          max={LONGUEURS.DESIGNATION}
        />
      </Champ>
    </>
  )
}

/** Le rôle dans le tapis, et la densité d'un rôle au mètre. */
function ChampsRole({ forme, maj, c }: VoletClassificationProps) {
  const role = c.roles.find((r) => r.id === forme.role_id)
  const roles = [...c.roles]
    .sort((a, b) => a.ordre - b.ordre || a.code.localeCompare(b.code))
    .map((r) => ({ id: r.id, titre: r.lineaire ? `${r.code} (au mètre)` : r.code }))
  return (
    <>
      <Champ libelle="Rôle dans le tapis" obligatoire aide="l’ordre est celui de la classification">
        <Selecteur<number>
          valeur={forme.role_id}
          options={roles}
          onChange={(id) => maj({ role_id: id })}
          effacable={false}
        />
      </Champ>
      {role?.lineaire ? (
        <ChampDensite
          valeur={forme.densite}
          onChange={(v) => maj({ densite: v })}
          aide="obligatoire pour le cuir, les franges, le ruban : la recette les compte en mètres, le stock en kilos"
        />
      ) : null}
    </>
  )
}

export function VoletClassification(p: VoletClassificationProps) {
  const { forme, maj, c } = p
  return (
    <div className={styles.volet}>
      <Grille colonnes={2}>
        {LISTES.map((d) => (
          <Champ key={d.liste} libelle={d.nom[0]?.toUpperCase() + d.nom.slice(1)}>
            <ChoixClasse
              d={d}
              valeurs={c[d.cle]}
              valeur={forme[d.champ]}
              onChange={(id) => maj(avecClasse(d.champ, id))}
            />
          </Champ>
        ))}
        <Champ libelle="Code couleur" aide="celui du fournisseur : 7612, A-304…">
          <Saisie
            valeur={forme.couleur_code}
            onChange={(v) => maj({ couleur_code: v })}
            max={LONGUEURS.COULEUR_CODE}
          />
        </Champ>
        <Champ
          libelle="Suffixe fournisseur"
          aide="la marque de fin du fournisseur : Hs, Oz, Tat… (non gardée)"
        >
          <Saisie valeur={forme.suffixe} onChange={(v) => maj({ suffixe: v })} max={SUFFIXE_MAX} />
        </Champ>
        <ChampsReference {...p} />
        <ChampsRole {...p} />
      </Grille>
    </div>
  )
}
