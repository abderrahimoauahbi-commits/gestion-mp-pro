/**
 * Les indicateurs et les bandeaux de la fiche d'un dossier (ECRANS-PRO 5.6) : poids (lots),
 * coût hors TVA (au kilo), achat, charges hors TVA (part de l'achat), coût TTC (dont TVA, ou
 * l'écart des droits et de la TVA qui renvoie aux frais) ; puis les bandeaux : frais non répartis
 * (le dossier ne se clôt pas ainsi), frais hors norme, coût sous zéro, frais visés sur une
 * marchandise, facture ≠ reçu (C36). Les chiffres sont ceux du serveur, sans recalcul.
 */
import { Indicateurs } from '../../composants/mise-en-page/Indicateurs'
import { Kpi } from '../../composants/retour/Kpi'
import { Note } from '../../composants/retour/Note'
import { Bouton } from '../../composants/saisie/Bouton'
import { formule } from '../../lib/aide'
import { montantCourt, montantPrecis, nombre, part, prix } from '../../lib/format'
import { partCharges, SEUIL_NON_REPARTIS, type DossierFiche } from './types'

const lotsDistincts = (d: DossierFiche) => new Set(d.lignes.map((l) => l.lot_id ?? `${l.id}`)).size

/** « droits ≠ attendu », « TVA ≠ attendu », « droits et TVA ≠ attendus », ou rien. */
function ecartsAttendus(d: DossierFiche): string | null {
  const droits = d.droits_ecart_mad != null
  const tva = d.tva_ecart_mad != null
  if (droits && tva) return 'droits et TVA ≠ attendus : voir les frais'
  if (droits) return 'droits ≠ attendu : voir les frais'
  if (tva) return 'TVA ≠ attendu : voir les frais'
  return null
}

export function IndicateursDossier({ d, versFrais }: { d: DossierFiche; versFrais: () => void }) {
  const p = partCharges(d.charges_mad, d.marchandise_mad)
  const ecart = ecartsAttendus(d)
  return (
    <Indicateurs libelle="Indicateurs du dossier">
      <Kpi
        titre="Poids"
        valeur={nombre(d.poids, 0, 2)}
        unite="kg"
        detail={`${nombre(lotsDistincts(d))} lot(s)`}
        formule={formule('import_poids')}
      />
      <Kpi
        titre="Coût hors TVA"
        valeur={montantCourt(d.revient_mad, 'MAD')}
        exact={montantPrecis(d.revient_mad, 'MAD')}
        ton="ok"
        detail={d.revient_kg != null ? `${prix(d.revient_kg)} MAD / kg` : 'achat + charges'}
        formule={formule('import_cout')}
      />
      <Kpi
        titre="Achat"
        valeur={montantCourt(d.marchandise_mad, 'MAD')}
        exact={montantPrecis(d.marchandise_mad, 'MAD')}
        detail="marchandise, en MAD"
        formule={formule('import_achat')}
      />
      <Kpi
        titre="Charges hors TVA"
        valeur={montantCourt(d.charges_mad, 'MAD')}
        exact={montantPrecis(d.charges_mad, 'MAD')}
        ton="attention"
        detail={p == null ? 'toutes les charges sauf la TVA' : `${part(p)} de l’achat`}
        formule={formule('import_charges')}
      />
      <Kpi
        titre="Coût TTC"
        valeur={montantCourt(d.decaisse_mad, 'MAD')}
        exact={montantPrecis(d.decaisse_mad, 'MAD')}
        ton={ecart ? 'urgent' : undefined}
        detail={
          ecart ? (
            <Bouton
              taille="petit"
              variante="fantome"
              titre="Voir les contrôles de l’onglet Frais"
              onClick={versFrais}
            >
              {ecart}
            </Bouton>
          ) : (
            `dont TVA ${montantPrecis(d.tva_mad, 'MAD')}`
          )
        }
        formule={formule('import_cout_ttc')}
      />
    </Indicateurs>
  )
}

function Lien({ texte, versFrais }: { texte: string; versFrais: () => void }) {
  return (
    <Bouton taille="petit" variante="fantome" onClick={versFrais}>
      {texte}
    </Bouton>
  )
}

export function BandeauxDossier({ d, versFrais }: { d: DossierFiche; versFrais: () => void }) {
  const horsTva = Math.abs(d.charges_non_reparties_mad) > SEUIL_NON_REPARTIS
  const tva = Math.abs(d.tva_non_repartie_mad) > SEUIL_NON_REPARTIS
  const ecartees = d.factures.filter((x) => x.ecart?.hors_tolerance)
  return (
    <>
      {horsTva || tva ? (
        <Note ton="critique">
          Frais non répartis : {montantPrecis(d.charges_non_reparties_mad, 'MAD')} hors TVA
          {tva ? ` et ${montantPrecis(d.tva_non_repartie_mad, 'MAD')} de TVA` : ''} ne trouvent pas de
          marchandise où se répartir (dossier vide) : ils ne sont dans aucun coût. Le dossier ne se clôt pas
          ainsi.
        </Note>
      ) : null}
      {d.surcout_aberrant ? (
        <Note ton="critique">
          Frais hors norme : {montantPrecis(d.charges_mad, 'MAD')} de frais pour{' '}
          {montantPrecis(d.marchandise_mad, 'MAD')} de marchandise (au-delà de {part(d.seuil_surcout, 0)},
          réglable dans Réglages › Prix). Un zéro de trop, ou les frais d’un autre dossier ?{' '}
          <Lien texte="les vérifier sur leurs pièces" versFrais={versFrais} />
        </Note>
      ) : null}
      {d.lignes_negatives.length || d.lignes_aberrantes.length ? (
        <Note ton="critique">
          {d.lignes_negatives.length
            ? `Coût sous zéro : ${d.lignes_negatives.join(', ')} — un avoir dépasse ce que la marchandise a coûté. `
            : ''}
          {d.lignes_aberrantes.length
            ? `Frais hors norme sur une seule marchandise : ${d.lignes_aberrantes.join(', ')}. Un frais visé sur une seule ligne nourrit le coût moyen de ce lot : `
            : ''}
          <Lien texte="le vérifier" versFrais={versFrais} />
        </Note>
      ) : null}
      {ecartees.map(({ id, ecart: f }) =>
        f ? (
          <Note key={id} ton="info">
            Facture {f.facture} : {montantPrecis(f.montant, f.devise)} facturés pour{' '}
            {montantPrecis(f.recu, f.devise)} reçus (pesée × prix), soit {part(f.part)} d’écart (tolérance{' '}
            {part(f.tolerance)}, Réglages › Prix). Le coût reste pesée × prix (contrôle C36).
          </Note>
        ) : null,
      )}
    </>
  )
}
