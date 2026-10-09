/**
 * Le haut de la fiche commande (ECRANS-PRO 4.7) : qui, quand, par qui ; les indicateurs du bon ;
 * les bandeaux (renvoi de la direction, approbation attendue, raison sociale non réglée) — lus sur
 * la fiche du serveur, jamais recalculés.
 */
import { Indicateurs } from '../../composants/mise-en-page/Indicateurs'
import { Kpi } from '../../composants/retour/Kpi'
import { Note } from '../../composants/retour/Note'
import { formule } from '../../lib/aide'
import { cours, date, horodatage, kg, montant, nombre, part, VIDE } from '../../lib/format'
import type { Role } from '../../lib/types'
import type { CommandeFiche } from './types'

/** « Maroc · envoyé le 08/10/2026 · créé par Karim le … · USD · approuvé par … ». */
export function quiQuand(c: CommandeFiche): string {
  return [
    c.pays,
    c.parti ? `envoyé le ${date(c.date_commande)}` : 'pas encore envoyé',
    c.cree_par ? `créé par ${c.cree_par} le ${horodatage(c.cree_le)}` : '',
    c.devise,
    c.approuvee_par ? `approuvé par ${c.approuvee_par} le ${horodatage(c.approuvee_le)}` : '',
    c.solde_origine === 'manuel' && c.solde_par
      ? `soldé à la main par ${c.solde_par} le ${date(c.solde_le)}`
      : '',
  ]
    .filter(Boolean)
    .join(' · ')
}

function detailRecu(c: CommandeFiche): string {
  if (c.livree_le) return `livré en entier le ${date(c.livree_le)}`
  if (c.recu > 0 && c.derniere_reception_le)
    return `${part(c.part_livree, 0)} livré · dernière réception le ${date(c.derniere_reception_le)}`
  return `${part(c.part_livree, 0)} livré`
}

export function IndicateursCommande({ c }: { c: CommandeFiche }) {
  const eta = c.expedition.eta
  const prixDetail = c.prix_a_confirmer ? `${nombre(c.prix_a_confirmer)} prix à confirmer` : 'prix confirmés'
  return (
    <Indicateurs libelle="Indicateurs du bon">
      <Kpi
        titre="Commandé"
        valeur={kg(c.quantite)}
        formule={formule('commande_commande')}
        detail={`${nombre(c.nb_lignes)} ligne(s)`}
      />
      <Kpi
        titre="Reçu"
        valeur={kg(c.recu)}
        formule={formule('commande_recu')}
        ton={c.part_livree >= 0.98 ? 'ok' : c.recu > 0 ? 'attention' : undefined}
        detail={detailRecu(c)}
      />
      <Kpi
        titre={c.prix_a_confirmer ? 'Montant estimé' : 'Montant'}
        valeur={montant(c.montant_estime, c.devise)}
        formule={formule('commande_montant')}
        detail={c.devise === 'MAD' ? prixDetail : `${prixDetail} · ≈ ${montant(c.montant_estime_mad, 'MAD')}`}
      />
      <Kpi
        titre={eta ? 'Arrivée prévue (ETA)' : 'Livraison prévue'}
        valeur={date(eta ?? c.date_livraison_prevue)}
        formule={formule('commande_livraison')}
        detail={c.expedition.conteneur ? `conteneur ${c.expedition.conteneur}` : undefined}
      />
      {c.devise === 'MAD' ? null : (
        <Kpi
          titre="Cours figé"
          valeur={c.cours ? cours(c.cours) : VIDE}
          unite={c.cours ? 'MAD' : undefined}
          formule={formule('commande_cours')}
          detail={
            c.cours
              ? `pour 1 ${c.devise} · à la confirmation du ${date(c.confirme_le)}`
              : `pas encore : cours du jour ${cours(c.taux_du_jour)}`
          }
        />
      )}
    </Indicateurs>
  )
}

/** Le bandeau « à approuver », dit selon le rôle (textes de Gestion MP). */
export function texteAApprouver(c: CommandeFiche, role: Role): string {
  const debut = c.numero
    ? `Ce bon, déjà chez le fournisseur, a changé de montant (≈ ${montant(c.montant_estime_mad, 'MAD')}, seuil ${montant(c.seuil_approbation, 'MAD')}) : `
    : `Ce bon dépasse le seuil d’approbation (${montant(c.seuil_approbation, 'MAD')}) : `
  if (role === 'direction')
    return `${debut}relisez-le, puis « Approuver et envoyer », ou « Renvoyer aux achats » avec un motif.`
  return c.numero
    ? `${debut}il attend l’accord de la direction. Ne confirmez pas le changement au fournisseur avant.`
    : `${debut}il attend l’accord de la direction avant de partir.`
}

export function BandeauxCommande({ c, role }: { c: CommandeFiche; role: Role }) {
  return (
    <>
      {c.renvoi ? (
        <Note ton="attention">
          <strong>Renvoyé aux achats</strong> par {c.renvoi.par} le {horodatage(c.renvoi.le)} : «{' '}
          {c.renvoi.motif} ».{' '}
          {c.numero
            ? 'Le changement n’est pas accepté : le bon reste chez le fournisseur tel qu’il était parti.'
            : 'Corrigez le bon, puis soumettez-le de nouveau — ou supprimez-le.'}
        </Note>
      ) : null}
      {c.statut === 'a_approuver' ? <Note ton="attention">{texteAApprouver(c, role)}</Note> : null}
      {c.raison_sociale_reglee ? null : (
        <Note ton="attention">
          La raison sociale de l’usine n’est pas réglée (Réglages › Paramètres › Société) : elle manque en
          tête du bon.
        </Note>
      )}
    </>
  )
}
