/**
 * Vue « Recette d'une qualité » (ECRANS-PRO 5.18, `?vue=qualite&qualite=ID&du=&au=`) : on croise
 * la recette d'une qualité (quels fils, dans quelle proportion) avec ce que ces fils ont coûté,
 * rendus usine, dans les dossiers d'importation (`GET analyse/revient/qualites/{id}?du=&au=`).
 */
import { keepPreviousData } from '@tanstack/react-query'
import { Link } from 'react-router'

import { Chargement } from '../../../composants/retour/Chargement'
import { Erreur } from '../../../composants/retour/Erreur'
import { Vide } from '../../../composants/retour/Vide'
import type { OptionSelecteur } from '../../../composants/saisie/Selecteur'
import { DataTable } from '../../../composants/tableaux/DataTable'
import { adresseDocument } from '../../../composants/documents/LienDocument'
import { permis } from '../../../lib/droits'
import { nombre } from '../../../lib/format'
import { useLecture } from '../../../lib/requetes'
import { useSession } from '../../../lib/session'
import { colonnesQualite, PiedQualite, type CoutQualite } from './colonnesQualite'
import type { EtatRevient, Modifier } from './etat'
import { IndicateursQualite } from './Indicateurs'
import { ChoixQualite, Periode } from './FiltresRevient'
import type { Liens } from './liens'
import styles from './revient.module.css'

/** « N matière(s) importée(s) sur M dans la recette », et le lien vers la qualité. */
function NoteRecette({ r, id }: { r: CoutQualite; id: number }) {
  const { role } = useSession()
  const adresse = adresseDocument('qualite', id)
  return (
    <span className={styles.note}>
      {nombre(r.references_importees)} matière(s) importée(s) sur {nombre(r.references_de_la_recette)} dans la
      recette
      {permis(role, adresse) ? (
        <>
          {' · '}
          <Link to={adresse}>voir la qualité {r.qualite}</Link>
        </>
      ) : null}
    </span>
  )
}

export function VueQualite({
  etat,
  modifier,
  qualites,
  liens,
}: {
  etat: EtatRevient
  modifier: Modifier
  qualites: readonly OptionSelecteur[]
  liens: (ids: Readonly<Record<string, number>>) => Liens
}) {
  const lecture = useLecture<CoutQualite>(
    etat.qualite == null ? null : `/analyse/revient/qualites/${etat.qualite}`,
    { du: etat.du || undefined, au: etat.au || undefined },
    { placeholderData: keepPreviousData },
  )
  const r = etat.qualite == null ? undefined : lecture.data
  return (
    <>
      <div className={styles.rangee}>
        <ChoixQualite
          etat={etat}
          modifier={modifier}
          options={qualites}
          placeholder="Choisir une qualité…"
          libelle="Qualité de tapis"
        />
        <Periode etat={etat} modifier={modifier} />
        {r && etat.qualite != null ? <NoteRecette r={r} id={etat.qualite} /> : null}
      </div>
      {etat.qualite == null ? (
        <Vide>
          Choisir une qualité : on croise sa recette (quels fils, dans quelle proportion) avec ce que ces fils
          ont coûté, rendus usine, dans les dossiers d’importation.
        </Vide>
      ) : lecture.isError ? (
        <Erreur erreur={lecture.error} onReessayer={() => void lecture.refetch()} />
      ) : !r ? (
        <Chargement quoi="le coût de la qualité" />
      ) : (
        <TableQualite r={r} liens={liens(r.ids_dossiers)} />
      )}
    </>
  )
}

/** Les indicateurs de la qualité, puis ses fils un à un et le pied par rôle. */
function TableQualite({ r, liens }: { r: CoutQualite; liens: Liens }) {
  return (
    <>
      <IndicateursQualite r={r} />
      <div className={styles.tableau}>
        <DataTable
          libelle="Recette d’une qualité"
          lignes={r.lignes}
          colonnes={colonnesQualite(liens)}
          cle={(g) => `${g.valeur}|${g.role ?? ''}`}
          recherche={false}
          serveur
          pied={r.roles.length ? <PiedQualite r={r} /> : undefined}
          vide="Aucun fil de cette recette n’a encore été importé dans un dossier."
        />
      </div>
    </>
  )
}
