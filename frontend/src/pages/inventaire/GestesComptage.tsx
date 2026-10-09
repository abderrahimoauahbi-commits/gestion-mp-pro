/**
 * Les gestes de la fenêtre de comptage, à place fixe (ECRANS-PRO partie 6) : feuilles de comptage
 * (à l'aveugle), de recomptage (lignes enregistrées seulement, an. 8), avec le théorique (direction,
 * an. 15) ; lot trouvé ; abandonner (motif exigé) ; annuler un inventaire validé (motif exigé,
 * contre-passation) ; enregistrer ; valider (grisé avec la raison, confirmation qui dit l'effet).
 */
import { BoutonImprimer } from '../../composants/documents/BoutonImprimer'
import { Bouton } from '../../composants/saisie/Bouton'
import { Confirmer, MOTIF_MIN } from '../../composants/saisie/Confirmer'
import { nombre } from '../../lib/format'
import { questionValider, raisonsDeValider, type Totaux } from './calculComptage'
import styles from './Inventaire.module.css'
import type { InventaireFiche } from './types'

export interface GestesProps {
  fiche: InventaireFiche
  t: Totaux
  saisie: boolean
  /** Direction ou achats : annuler un inventaire validé. */
  peutAnnuler: boolean
  /** La direction : la feuille avec le théorique, pour un contrôle. */
  voitTheorique: boolean
  trouveOuvert: boolean
  onTrouve: () => void
  gestes: {
    enregistrer: () => Promise<unknown>
    valider: () => Promise<unknown>
    abandonner: (motif: string) => Promise<unknown>
    annuler: (motif: string) => Promise<unknown>
  }
}

const ROUTE_FEUILLE = (id: number) => `/documents/inventaires/${id}/feuille`

function Feuilles({ fiche, t, voitTheorique }: Pick<GestesProps, 'fiche' | 't' | 'voitTheorique'>) {
  const recomptage =
    t.modifiees > 0
      ? 'Enregistrer d’abord le comptage : la feuille ne lit que ce qui est enregistré'
      : fiche.a_recompter === 0
        ? 'Aucun lot à recompter'
        : ''
  return (
    <>
      <BoutonImprimer
        route={ROUTE_FEUILLE(fiche.id)}
        libelle="Feuille de comptage"
        titre="La feuille à imprimer pour compter sur place, sans le théorique (comptage à l’aveugle)"
      />
      {recomptage ? (
        <Bouton taille="petit" icone="imprimer" grise={recomptage}>
          Feuille de recomptage
        </Bouton>
      ) : (
        <BoutonImprimer
          route={ROUTE_FEUILLE(fiche.id)}
          parametres={{ recomptage: true }}
          libelle="Feuille de recomptage"
          titre={`${nombre(fiche.a_recompter)} lot(s) hors tolérance à recompter, avec le théorique : pour la personne qui recompte`}
        />
      )}
      {voitTheorique ? (
        <BoutonImprimer
          route={ROUTE_FEUILLE(fiche.id)}
          parametres={{ theorique: true }}
          libelle="Feuille avec le théorique"
          titre="Pour un contrôle, pas pour compter (le comptage se fait à l’aveugle)"
        />
      ) : null}
    </>
  )
}

/** Les gestes de la saisie : lot trouvé, abandonner, enregistrer, valider. */
function GestesSaisie(p: GestesProps) {
  const { fiche, t } = p
  return (
    <>
      <Bouton
        taille="petit"
        onClick={p.onTrouve}
        titre={
          p.trouveOuvert ? 'Refermer la saisie du lot trouvé' : 'Un lot trouvé sur place, absent du théorique'
        }
      >
        Lot trouvé…
      </Bouton>
      <Confirmer
        variante="danger"
        motif="exige"
        motifMin={MOTIF_MIN}
        question={`Abandonner ${fiche.numero} ? Rien n’est ajusté, les mouvements reprennent ; l’inventaire reste au statut « Abandonné » avec ses comptages.`}
        oui="Oui, abandonner"
        onOui={p.gestes.abandonner}
      >
        Abandonner
      </Confirmer>
      <Bouton
        onClick={p.gestes.enregistrer}
        grise={t.modifiees ? undefined : 'Rien à enregistrer'}
        titre={`${nombre(t.modifiees)} ligne(s) à enregistrer`}
        attente="Enregistrement…"
      >
        Enregistrer le comptage
      </Bouton>
      <Confirmer
        variante="principal"
        blocages={raisonsDeValider(fiche, t)}
        question={questionValider(t)}
        oui="Oui, valider l’inventaire"
        attente="Validation…"
        onOui={p.gestes.valider}
      >
        Valider l’inventaire
      </Confirmer>
    </>
  )
}

export function GestesComptage(p: GestesProps) {
  const { fiche } = p
  return (
    <div className={styles.gestes}>
      <Feuilles fiche={fiche} t={p.t} voitTheorique={p.voitTheorique} />
      <span className={styles.pousse} />
      {fiche.statut === 'valide' && p.peutAnnuler ? (
        <Confirmer
          variante="danger"
          motif="exige"
          motifMin={MOTIF_MIN}
          titre="Annuler (contre-passation) : chaque ajustement de cet inventaire est contre-passé, avec un motif"
          question={`Annuler l’inventaire ${fiche.numero} ? Ses ajustements sont contre-passés à leur date (refusé en période close ou si la matière est déjà repartie).`}
          oui="Oui, annuler l’inventaire"
          onOui={p.gestes.annuler}
        >
          Annuler l’inventaire
        </Confirmer>
      ) : null}
      {p.saisie ? <GestesSaisie {...p} /> : null}
    </div>
  )
}
