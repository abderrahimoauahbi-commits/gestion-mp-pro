/**
 * Les indicateurs de l'analyse (ECRANS-PRO 5.15, 5.18), chacun avec sa formule (`aide.json`).
 *
 * Ce qu'on lit d'abord : le poids et le coût hors TVA — l'achat en MAD plus toutes les charges
 * sauf la TVA, qui se récupère. Les frais saisis sans marchandise où se répartir ne sont dans
 * **aucun** coût : ils se disent à part, en rouge (« + 1 200 MAD non répartis »), et s'ouvrent en
 * une liste de liens, un par dossier qui en porte (Gestion MP n'ouvrait que le premier).
 */
import { Indicateurs } from '../../../composants/mise-en-page/Indicateurs'
import { Kpi } from '../../../composants/retour/Kpi'
import { formule } from '../../../lib/aide'
import { kg, montant, montantCourt, montantPrecis, nombre, part } from '../../../lib/format'
import type { Analyse } from './colonnes'
import type { CoutQualite } from './colonnesQualite'
import { LienDossier, type Liens } from './liens'
import styles from './revient.module.css'

/** Le seuil sous lequel des frais non répartis ne comptent pas (comme le serveur). */
const SEUIL = 0.005

/** « + N MAD non répartis » : la liste des dossiers qui en portent, chacun en lien. */
export function NonRepartis({ r, liens }: { r: Analyse; liens: Liens }) {
  if (Math.abs(r.frais_non_repartis_mad) <= SEUIL || !r.dossiers_non_repartis.length) return null
  const detail = r.dossiers_non_repartis.map((d) => `${d.dossier} (${montant(d.montant, 'MAD')})`).join(', ')
  return (
    <details
      className={styles.nonRepartis}
      title={`Frais saisis sans marchandise où se répartir, dans aucun coût : ${detail}. Cliquer pour voir les dossiers.`}
    >
      <summary>+ {montantCourt(r.frais_non_repartis_mad, 'MAD')} non répartis</summary>
      <ul aria-label="Dossiers aux frais non répartis">
        {r.dossiers_non_repartis.map((d) => (
          <li key={d.dossier}>
            <LienDossier numero={d.dossier} liens={liens} />
            <span>{montantPrecis(d.montant, 'MAD')}</span>
          </li>
        ))}
      </ul>
    </details>
  )
}

/** Poids · Coût hors TVA · Achat · Charges hors TVA · Coût TTC (vues « Regroupé » et « Lot par lot »). */
export function IndicateursRevient({ r, liens }: { r: Analyse; liens: Liens }) {
  const parKg = r.total_poids ? `${nombre(r.total_revient_mad / r.total_poids, 2)} MAD / kg · ` : ''
  return (
    <Indicateurs libelle="Indicateurs du coût de revient">
      <Kpi
        titre="Poids"
        valeur={kg(r.total_poids)}
        formule={formule('import_poids')}
        detail={`${nombre(r.total_lignes)} lot(s)`}
      />
      <Kpi
        titre="Coût hors TVA"
        valeur={montantCourt(r.total_revient_mad, 'MAD')}
        exact={montant(r.total_revient_mad, 'MAD')}
        formule={formule('import_cout')}
        detail={`${parKg}achat + charges`}
        ton="ok"
      />
      <Kpi
        titre="Achat"
        valeur={montantCourt(r.total_marchandise_mad, 'MAD')}
        exact={montant(r.total_marchandise_mad, 'MAD')}
        formule={formule('import_achat')}
        detail="marchandise, en MAD"
      />
      <Kpi
        titre="Charges hors TVA"
        valeur={montantCourt(r.total_charges_mad, 'MAD')}
        exact={montant(r.total_charges_mad, 'MAD')}
        formule={formule('import_charges')}
        ton="attention"
        detail={
          <span className={styles.detailKpi}>
            {r.total_marchandise_mad ? (
              <span>{part(r.total_charges_mad / r.total_marchandise_mad)} de l’achat</span>
            ) : null}
            <NonRepartis r={r} liens={liens} />
          </span>
        }
      />
      <Kpi
        titre="Coût TTC"
        valeur={montantCourt(r.total_decaisse_mad, 'MAD')}
        exact={montant(r.total_decaisse_mad, 'MAD')}
        formule={formule('import_cout_ttc')}
        detail={`dont TVA ${montant(r.total_tva_mad, 'MAD')}`}
      />
    </Indicateurs>
  )
}

/** Coût matière / m² · Coût / kg de tapis · Recette couverte · Poids importé (vue « Recette d'une qualité »). */
export function IndicateursQualite({ r }: { r: CoutQualite }) {
  return (
    <Indicateurs libelle="Indicateurs de la qualité">
      <Kpi
        titre="Coût matière / m²"
        valeur={montantPrecis(r.cout_m2_estime, 'MAD')}
        formule={formule('revient_cout_m2')}
        detail={`recette × coût hors TVA de chaque fil · ${nombre(r.poids_m2, 3)} kg / m²`}
        ton="ok"
      />
      <Kpi
        titre="Coût / kg de tapis"
        valeur={montantPrecis(r.cout_kg_tapis, 'MAD')}
        formule={formule('revient_cout_kg_tapis')}
        detail={
          r.roles_sans_cout.length
            ? `pondéré par la recette · sans ${r.roles_sans_cout.join(', ')}`
            : 'pondéré par la recette (rôles en kilos)'
        }
      />
      <Kpi
        titre="Recette couverte"
        valeur={part(r.couverture, 0)}
        formule={formule('revient_couverture')}
        detail={`du poids : ${nombre(r.references_importees)} fil(s) importé(s) sur ${nombre(r.references_de_la_recette)}`}
        ton={r.couverture < 0.999 ? 'attention' : undefined}
      />
      <Kpi
        titre="Poids importé"
        valeur={kg(r.total_poids)}
        formule={formule('revient_poids_importe')}
        detail={`${nombre(r.total_lignes)} lot(s) · ${montantCourt(r.total_revient_mad, 'MAD')} hors TVA`}
      />
    </Indicateurs>
  )
}
