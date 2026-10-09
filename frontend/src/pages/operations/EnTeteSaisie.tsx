/**
 * Date, motif et observations d'une opération (ECRANS-PRO partie 6), et les notes de la
 * quarantaine : libération (décision des achats ou de la direction, après contrôle) et mise en
 * quarantaine (ce qui est douteux, dans les observations).
 */
import { Grille } from '../../composants/mise-en-page/Grille'
import { Note } from '../../composants/retour/Note'
import { Champ } from '../../composants/saisie/Champ'
import { DateChamp } from '../../composants/saisie/DateChamp'
import { Saisie } from '../../composants/saisie/Saisie'
import { Selecteur } from '../../composants/saisie/Selecteur'
import { motifExige, observationsExigees } from './saisie'
import { LIBERATION, MISE_EN_QUARANTAINE } from './types'
import type { useOperation } from './useOperation'

const PLACEHOLDERS: Record<string, string> = {
  ouverture: 'Comptage du magasin principal, mise en service…',
  ajustement: 'Bobines écrasées au déchargement, palette retrouvée…',
}

/** Les notes de la libération et de la mise en quarantaine. */
function NotesQuarantaine({ libelle }: { libelle: string | undefined }) {
  const motif = { libelle }
  return (
    <>
      {motif?.libelle === LIBERATION ? (
        <Note>
          Libération de quarantaine (décision des achats ou de la direction, après contrôle) : choisir un lot
          dans le magasin de quarantaine ; il retourne au stock courant. Dire dans les observations ce qui a
          été contrôlé.
        </Note>
      ) : null}
      {motif?.libelle === MISE_EN_QUARANTAINE ? (
        <Note>
          Mise en quarantaine : choisir un lot hors quarantaine ; il part vers un magasin de quarantaine et ne
          sort plus aux machines. Dire dans les observations ce qui est douteux.
        </Note>
      ) : null}
    </>
  )
}

export function EnTeteSaisie({ x }: { x: ReturnType<typeof useOperation> }) {
  const { s, poser, motif, modifiable } = x
  const exige = observationsExigees(s.type, motif)
  return (
    <>
      <Grille colonnes={4}>
        <Champ libelle="Date">
          <DateChamp
            valeur={s.date}
            onChange={(date) => poser({ date })}
            min={x.min}
            raisonMin="la période est close jusque-là"
            desactive={!modifiable}
          />
        </Champ>
        {s.type === 'ouverture' ? null : (
          <Champ libelle={motifExige(s.type) ? 'Motif (obligatoire)' : 'Motif'}>
            <Selecteur
              valeur={s.motif_id}
              options={x.motifs.map((m) => ({
                id: m.id,
                titre: m.code_r ? `${m.code_r} · ${m.libelle}` : m.libelle,
              }))}
              onChange={(id) => poser({ motif_id: id })}
              placeholder={s.type === 'transfert' ? 'Sans motif particulier' : 'Choisir le motif…'}
              effacable={s.type === 'transfert'}
              desactive={!modifiable}
            />
          </Champ>
        )}
        <Champ
          libelle={exige ? 'Observations (obligatoires)' : 'Observations'}
          large={s.type === 'ouverture'}
          aide={
            s.type === 'ajustement'
              ? 'ce qui a été constaté, en quelques mots'
              : motif?.libelle === MISE_EN_QUARANTAINE
                ? 'ce qui est douteux'
                : undefined
          }
        >
          <Saisie
            valeur={s.commentaire}
            onChange={(commentaire) => poser({ commentaire })}
            max={300}
            placeholder={PLACEHOLDERS[s.type] ?? ''}
            desactive={!modifiable}
          />
        </Champ>
      </Grille>
      <NotesQuarantaine libelle={motif?.libelle} />
    </>
  )
}
