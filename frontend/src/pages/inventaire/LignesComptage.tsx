/**
 * Les colonnes de la sous-vue « Lots à compter » (ECRANS-PRO partie 6) : saisie sur la ligne
 * (palettes, bobines, compté, recompté, justification) tant que l'inventaire est ouvert, lecture
 * sinon. Le théorique reste affiché (terme d'inventaire, exception notée au vocabulaire, an. 11).
 */
import { Badge } from '../../composants/retour/Badge'
import { Nombre } from '../../composants/saisie/Nombre'
import { Saisie } from '../../composants/saisie/Saisie'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { bobinesApprochees } from '../../lib/unites'
import { kg, metres, nombre, pourcent, VIDE } from '../../lib/format'
import { EcartKg, ValeurEcart } from './communs'
import type { Brouillon, EtatLigne } from './calculComptage'
import styles from './Inventaire.module.css'
import type { LigneInventaire } from './types'

type C = Colonne<EtatLigne>

export interface OptionsColonnes {
  saisie: boolean
  tousMagasins: boolean
  voitPrix: boolean
  changer: (l: LigneInventaire, modif: Partial<Brouillon>) => void
}

const conditionnement = (l: LigneInventaire) => ({
  poidsBobine: l.poids_bobine,
  bobinesPalette: l.bobines_palette,
})

/** « par {nom} » sous une valeur saisie (premier compteur, recompteur). */
const Par = ({ nom }: { nom: string }) => (nom ? <span className={styles.note}>par {nom}</span> : null)

const reference: C = {
  cle: 'reference',
  titre: 'Référence',
  valeur: (e) => e.ligne.reference,
  recherche: (e) => [e.ligne.designation],
  rendu: (e) => (
    <span className={styles.valeur} title={`${e.ligne.reference} — ${e.ligne.designation}`}>
      <strong className={styles.lot}>{e.ligne.reference}</strong>
      {e.ligne.designation ? <span className={styles.note}>{e.ligne.designation}</span> : null}
    </span>
  ),
}

const lot: C = {
  cle: 'lot',
  titre: 'Lot',
  valeur: (e) => e.ligne.lot,
  lien: (e) => (e.ligne.lot_id ? `/lots/${e.ligne.lot_id}` : null),
  rendu: (e) => (
    <span className={styles.valeur}>
      <span className={`mono ${styles.lot}`}>{e.ligne.lot}</span>
      {e.ligne.lot_trouve ? (
        <span className={styles.note}>
          trouvé, non prévu{e.ligne.lot_id ? '' : ' · créé à la validation'}
        </span>
      ) : null}
    </span>
  ),
}

const magasin: C = { cle: 'magasin', titre: 'Magasin', valeur: (e) => e.ligne.magasin }

const theorique: C = {
  cle: 'theorique',
  titre: 'Théorique (kg)',
  aide: 'Le stock figé à l’ouverture de l’inventaire',
  droite: true,
  unite: 'kg',
  total: true,
  valeur: (e) => e.ligne.theorique,
  rendu: (e) => (
    <span className={styles.enLigne}>
      <span className="nombre">{nombre(e.ligne.theorique, 1)}</span>
      <span className={styles.note}>
        {[
          metres(e.ligne.theorique, e.ligne.kg_par_ml),
          bobinesApprochees(e.ligne.theorique, conditionnement(e.ligne)),
        ]
          .filter(Boolean)
          .join(' · ')}
      </span>
    </span>
  ),
}

function palettes(o: OptionsColonnes): C {
  return {
    cle: 'palettes',
    titre: 'Palettes',
    droite: true,
    valeur: (e) => e.palettes,
    rendu: (e) => {
      const l = e.ligne
      if (!(l.bobines_palette > 0 && l.poids_bobine > 0)) return VIDE
      if (!o.saisie) return nombre(e.palettes)
      return (
        <span className={styles.enLigne}>
          <Nombre
            className={styles.petit}
            valeur={e.palettes}
            onChange={(v) => o.changer(l, { palettes: v })}
            min={0}
            decimales={0}
            libelle={`Palettes de ${l.reference}, lot ${l.lot}`}
          />
          <span className={styles.note}>× {nombre(l.bobines_palette)} bob.</span>
        </span>
      )
    },
  }
}

function bobines(o: OptionsColonnes): C {
  return {
    cle: 'bobines',
    titre: 'Bobines',
    aide: 'Le poids de bobine du lot (sinon celui du catalogue) donne le compté',
    droite: true,
    valeur: (e) => e.bobines,
    rendu: (e) => {
      const l = e.ligne
      if (!(l.poids_bobine > 0)) return VIDE
      if (!o.saisie) return nombre(e.bobines)
      return (
        <span className={styles.enLigne}>
          <Nombre
            className={styles.petit}
            valeur={e.bobines}
            onChange={(v) => o.changer(l, { bobines: v })}
            min={0}
            decimales={0}
            libelle={`Bobines de ${l.reference}, lot ${l.lot}`}
          />
          <span className={styles.note}>× {nombre(l.poids_bobine, 0, 4)} kg</span>
        </span>
      )
    },
  }
}

function compte(o: OptionsColonnes): C {
  return {
    cle: 'compte',
    titre: 'Compté (kg)',
    droite: true,
    unite: 'kg',
    total: true,
    valeur: (e) => e.compte,
    rendu: (e) => (
      <span className={styles.valeur}>
        {o.saisie ? (
          <Nombre
            className={styles.cellule}
            valeur={e.compte}
            onChange={(v) => o.changer(e.ligne, { compte: v })}
            min={0}
            decimales={3}
            placeholder="non compté"
            libelle={`Compté (kg) de ${e.ligne.reference}, lot ${e.ligne.lot}`}
          />
        ) : (
          <span className="nombre">{e.compte == null ? 'non compté' : nombre(e.compte, 1, 3)}</span>
        )}
        <Par nom={e.modifiee && e.compte !== e.ligne.compte ? '' : e.ligne.compte_par} />
      </span>
    ),
  }
}

function recompte(o: OptionsColonnes): C {
  return {
    cle: 'recompte',
    titre: 'Recompté (kg)',
    aide: 'Un écart hors tolérance se recompte, par une autre personne : ce second comptage ajuste',
    droite: true,
    valeur: (e) => e.second,
    rendu: (e) => {
      const ouvert = o.saisie && e.compte != null && (e.recompter || e.second != null)
      return (
        <span className={styles.valeur}>
          {ouvert ? (
            <Nombre
              className={styles.cellule}
              valeur={e.second}
              onChange={(v) => o.changer(e.ligne, { second_compte: v })}
              min={0}
              decimales={3}
              libelle={`Recompté (kg) de ${e.ligne.reference}, lot ${e.ligne.lot}`}
            />
          ) : (
            <span className="nombre">{e.second == null ? VIDE : nombre(e.second, 1, 3)}</span>
          )}
          <Par nom={e.modifiee && e.second !== e.ligne.second_compte ? '' : e.ligne.second_par} />
          {e.quatreYeux ? (
            <Badge ton="attention" titre={e.quatreYeux}>
              {e.quatreYeux.split(' : ')[0]}
            </Badge>
          ) : null}
        </span>
      )
    },
  }
}

const ecart: C = {
  cle: 'ecart',
  titre: 'Écart (kg)',
  droite: true,
  unite: 'kg',
  total: (s) => `${s > 0 ? '+' : ''}${kg(s)}`,
  valeur: (e) => e.ecart,
  rendu: (e) => <EcartKg valeur={e.ecart} colore={e.hors} />,
}

const ecartPourcent: C = {
  cle: 'ecart_pourcent',
  titre: 'Écart (%)',
  droite: true,
  valeur: (e) => (e.ecart == null ? null : e.ligne.theorique > 0 ? e.ecart / e.ligne.theorique : null),
  rendu: (e) => {
    if (e.ecart == null) return VIDE
    const l = e.ligne
    const texte =
      Math.abs(e.ecart) < 0.001
        ? 'juste'
        : l.theorique <= 0
          ? 'non prévu'
          : pourcent((Math.abs(e.ecart) / l.theorique) * 100, 1)
    return <Badge ton={e.hors ? 'critique' : 'neutre'}>{texte}</Badge>
  },
}

function justification(o: OptionsColonnes): C {
  return {
    cle: 'justification',
    titre: 'Justification',
    valeur: (e) => e.justification,
    largeur: 220,
    rendu: (e) =>
      o.saisie ? (
        <span className={e.manque ? styles.manque : undefined}>
          <Saisie
            className={styles.justification}
            valeur={e.justification}
            onChange={(v) => o.changer(e.ligne, { justification: v })}
            max={300}
            placeholder={e.hors ? 'Obligatoire : ce qui a été constaté' : ''}
            libelle={`Justification de ${e.ligne.reference}, lot ${e.ligne.lot}`}
          />
        </span>
      ) : (
        e.justification || VIDE
      ),
  }
}

const valeur: C = {
  cle: 'valeur',
  titre: 'Valeur de l’écart (MAD)',
  aide: 'Au coût moyen (CMUP) tant que l’inventaire est ouvert, au coût de l’ajustement une fois validé',
  droite: true,
  unite: 'MAD',
  total: true,
  valeur: (e) => e.valeur,
  rendu: (e) => <ValeurEcart net={e.valeur} />,
}

/** Les colonnes, selon la saisie, le magasin (tous ou un) et la vue des prix. */
export function colonnesComptage(o: OptionsColonnes): C[] {
  return [
    reference,
    lot,
    ...(o.tousMagasins ? [magasin] : []),
    theorique,
    palettes(o),
    bobines(o),
    compte(o),
    recompte(o),
    ecart,
    ecartPourcent,
    justification(o),
    ...(o.voitPrix ? [valeur] : []),
  ]
}
