/**
 * Les champs d'un code douanier (ECRANS-PRO 5.22) : Code (chiffres et points, contrôlé à la
 * frappe) et Taux de droits saisi en % (gardé en fraction, contrôlé de 0 à 100 % à la frappe) sur
 * une rangée, Libellé sur toute la rangée, puis « code actif ». Les achats lisent le code
 * (`LectureCode`) : pas de champs grisés.
 */
import { Link } from 'react-router'

import { Definitions } from '../../../composants/mise-en-page/Definitions'
import { Grille } from '../../../composants/mise-en-page/Grille'
import { Champ } from '../../../composants/saisie/Champ'
import { Interrupteur } from '../../../composants/saisie/Interrupteur'
import { Nombre } from '../../../composants/saisie/Nombre'
import { Saisie } from '../../../composants/saisie/Saisie'
import { nombre, part } from '../../../lib/format'
import type { CodeDouanier } from '../types'
import {
  erreurCodeDouanier,
  lienMatieres,
  LONGUEUR_CODE,
  LONGUEUR_LIBELLE,
  MESSAGE_TAUX,
  tauxHorsBornes,
  type FormeCode,
} from './formeCode'
import styles from './reglages.module.css'

/** « 2 matière(s) », lien vers elles au catalogue s'il y en a. */
export function Matieres({ c }: { c: CodeDouanier }) {
  if (!c.nb_matieres) return <>{nombre(0)}</>
  return (
    <Link to={lienMatieres(c.code)} title="Voir les matières qui portent ce code">
      {nombre(c.nb_matieres)} matière(s)
    </Link>
  )
}

/** Le code lu par les achats. */
export function LectureCode({ c }: { c: CodeDouanier }) {
  return (
    <Definitions
      items={[
        ['Code', <span className={styles.code}>{c.code}</span>],
        ['Libellé', c.libelle],
        ['Taux de droits', part(c.taux_droits, 1)],
        ['Matières', <Matieres c={c} />],
        ['État', c.actif ? 'actif' : 'désactivé'],
      ]}
    />
  )
}

/** Les champs saisis par la direction. */
export function ChampsCode({
  forme,
  maj,
  code,
}: {
  forme: FormeCode
  maj: (m: Partial<FormeCode>) => void
  code: CodeDouanier | null
}) {
  return (
    <>
      <Grille colonnes={2}>
        <Champ
          libelle="Code"
          obligatoire
          aide={
            code?.nb_matieres
              ? `${nombre(code.nb_matieres)} matière(s) le portent : elles suivront la correction`
              : 'chiffres et points (ex. 5402.47.00.00)'
          }
          erreur={erreurCodeDouanier(forme.code) || undefined}
        >
          <Saisie
            valeur={forme.code}
            onChange={(v) => maj({ code: v })}
            max={LONGUEUR_CODE}
            className={styles.saisieCode}
          />
        </Champ>
        <Champ
          libelle="Taux de droits (%)"
          obligatoire
          aide="sur la valeur en douane : achat + fret + assurance (CAF)"
          erreur={tauxHorsBornes(forme.taux) ? MESSAGE_TAUX : undefined}
        >
          <Nombre
            valeur={forme.taux}
            onChange={(taux) => maj({ taux })}
            echelle={100}
            unite="%"
            placeholder="ex. 10"
          />
        </Champ>
        <Champ libelle="Libellé" large>
          <Saisie
            valeur={forme.libelle}
            onChange={(v) => maj({ libelle: v })}
            max={LONGUEUR_LIBELLE}
            placeholder="Fils de polypropylène…"
          />
        </Champ>
      </Grille>
      <Interrupteur
        valeur={forme.actif}
        onChange={(actif) => maj({ actif })}
        libelle="code actif (proposé dans la fiche matière)"
      />
    </>
  )
}
