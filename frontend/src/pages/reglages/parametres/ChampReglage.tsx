/**
 * Un réglage : son libellé (unité en infobulle, « modifié, pas encore enregistré »), sa saisie à
 * la française (virgule acceptée, un taux en pourcent), son unité, et une aide d'une seule source
 * — la déclaration du serveur, « entre {bas} et {haut} », « par défaut », « avant ». Le refus du
 * champ se dit dessous, à la frappe ; un réglage sans effet se lit sans se saisir.
 */
import { Champ } from '../../../composants/saisie/Champ'
import { Saisie } from '../../../composants/saisie/Saisie'
import { nombre } from '../../../lib/format'
import styles from '../reglages.module.css'
import { lisible, refusDuChamp, texteInitial, type Reglage } from './logique'

/** L'aide d'un champ : la déclaration du serveur, ses bornes, son défaut, la valeur d'avant. */
export function aideDuReglage(r: Reglage, modifie: boolean): string {
  const echelle = r.echelle || 1
  const bornes =
    !r.texte && r.bas != null && r.haut != null
      ? `entre ${nombre(r.bas * echelle, 0, 6)} et ${nombre(r.haut * echelle, 0, 6)}${r.unite ? ` ${r.unite}` : ''}`
      : ''
  return [
    r.modifiable ? '' : 'sans effet, gardé pour mémoire',
    r.aide,
    bornes,
    `par défaut : ${lisible(r, r.defaut)}`,
    modifie ? `avant : ${lisible(r, r.valeur)}` : '',
  ]
    .filter(Boolean)
    .join(' · ')
}

export function ChampReglage({
  r,
  saisie,
  ecrit,
  onChange,
}: {
  r: Reglage
  saisie: string | undefined
  ecrit: boolean
  onChange: (v: string) => void
}) {
  const modifie = saisie !== undefined
  const valeur = saisie ?? texteInitial(r)
  const erreur = modifie ? refusDuChamp(r, valeur) : ''
  const titre = `${r.libelle}${r.unite ? ` (${r.unite})` : ''}${modifie ? ' — modifié, pas encore enregistré' : ''}`
  return (
    <div className={modifie ? styles.modifie : undefined} data-cle={r.cle}>
      <Champ
        libelle={<span title={titre}>{r.libelle}</span>}
        aide={aideDuReglage(r, modifie)}
        erreur={erreur || null}
      >
        <span className={styles.avecUnite}>
          <Saisie
            valeur={valeur}
            onChange={onChange}
            desactive={!ecrit || !r.modifiable}
            max={r.texte ? (r.cle === 'adresse_publique' ? 200 : 500) : 24}
            className={r.texte ? undefined : styles.nombre}
          />
          {r.unite ? <span className={styles.unite}>{r.unite}</span> : null}
        </span>
      </Champ>
    </div>
  )
}
