/**
 * Les champs d'un poste de frais (ECRANS-PRO 5.20), alignés deux par rangée : Code (contrôlé à la
 * frappe, figé après la création) et Libellé ; Répartition et Ordre ; puis la nature
 * (« récupérable ») et le message d'un changement de clé (dossiers ouverts recalculés, clos
 * gardés). Une nature figée grise l'interrupteur avec sa raison, redite en note. Les achats
 * lisent le poste (`LecturePoste`) : pas de champs grisés.
 */
import { Definitions } from '../../../composants/mise-en-page/Definitions'
import { Grille } from '../../../composants/mise-en-page/Grille'
import { Note } from '../../../composants/retour/Note'
import { Champ } from '../../../composants/saisie/Champ'
import { Interrupteur } from '../../../composants/saisie/Interrupteur'
import { Nombre } from '../../../composants/saisie/Nombre'
import { Saisie } from '../../../composants/saisie/Saisie'
import { Segments } from '../../../composants/saisie/Segments'
import { nombre, VIDE } from '../../../lib/format'
import type { PosteFiche } from '../types'
import {
  AIDE_SYSTEME,
  CLES,
  erreurCodePoste,
  fraisSaisis,
  lireCle,
  LONGUEUR_CODE,
  LONGUEUR_LIBELLE,
  messageChangementCle,
  nature,
  natureFigee,
  type Cle,
  type FormePoste,
} from './formePoste'
import styles from './reglages.module.css'

const OPTIONS_CLE = (['valeur', 'poids'] as const).map((c) => ({ valeur: c, libelle: CLES[c] }))

function CodeEtLibelle({
  forme,
  maj,
  poste,
}: {
  forme: FormePoste
  maj: (m: Partial<FormePoste>) => void
  poste: PosteFiche | null
}) {
  return (
    <>
      <Champ
        libelle="Code"
        obligatoire={!poste}
        aide={
          poste ? 'le code ne change pas : les frais le portent' : 'lettres, chiffres ou « _ » (ex. MANUT)'
        }
        erreur={poste ? undefined : erreurCodePoste(forme.code) || undefined}
      >
        <Saisie
          valeur={forme.code}
          onChange={(v) => maj({ code: v.toUpperCase() })}
          max={LONGUEUR_CODE}
          desactive={Boolean(poste)}
          className={styles.saisieCode}
        />
      </Champ>
      <Champ libelle="Libellé" obligatoire>
        <Saisie valeur={forme.libelle} onChange={(v) => maj({ libelle: v })} max={LONGUEUR_LIBELLE} />
      </Champ>
    </>
  )
}

/** Le poste lu par les achats : aucune saisie, aucun bouton grisé. */
export function LecturePoste({ poste: p }: { poste: PosteFiche }) {
  const recuperable = p.recuperable
  return (
    <>
      <Definitions
        items={[
          ['Code', <span className={styles.code}>{p.code}</span>],
          ['Libellé', p.libelle],
          ['Répartition', recuperable ? VIDE : CLES[lireCle(p.cle)]],
          ['Ordre', nombre(p.ordre)],
          ['Nature', nature(recuperable)],
          ['Frais saisis', nombre(fraisSaisis(p))],
          ['Dossiers ouverts', nombre(p.dossiers_ouverts)],
          ['Dossiers clos', nombre(p.dossiers_clos)],
        ]}
      />
      {p.systeme ? <Note>{AIDE_SYSTEME}.</Note> : null}
    </>
  )
}

/** Les champs saisis par la direction. */
export function ChampsPoste({
  forme,
  maj,
  poste,
}: {
  forme: FormePoste
  maj: (m: Partial<FormePoste>) => void
  poste: PosteFiche | null
}) {
  const figee = natureFigee(poste)
  const cleChangee = poste && forme.cle !== lireCle(poste.cle)
  return (
    <>
      <Grille colonnes={2}>
        <CodeEtLibelle forme={forme} maj={maj} poste={poste} />
        <Champ
          libelle="Répartition"
          groupe
          aide="au prorata de la valeur de chaque marchandise, ou de ses kilos"
        >
          <Segments<Cle> valeur={forme.cle} options={OPTIONS_CLE} onChange={(cle) => maj({ cle })} />
        </Champ>
        <Champ libelle="Ordre" aide="place dans les listes ; vide : à la fin">
          <Nombre valeur={forme.ordre} onChange={(ordre) => maj({ ordre })} min={0} max={999} decimales={0} />
        </Champ>
      </Grille>
      <Interrupteur
        valeur={forme.recuperable}
        onChange={(recuperable) => maj({ recuperable })}
        libelle="récupérable : hors du coût (comme la TVA)"
        grise={figee ?? undefined}
      />
      {figee ? <Note>{figee}</Note> : null}
      {cleChangee ? <Note ton="attention">{messageChangementCle(poste, forme.cle)}</Note> : null}
    </>
  )
}
