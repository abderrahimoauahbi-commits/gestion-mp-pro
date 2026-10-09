/**
 * Les volets en lecture de la fiche commande : les réceptions du bon (ECRANS-PRO 4.11, avec ce que
 * chacune a pesé pour lui) et l'approbation (4.12, la table des décisions et la version partie).
 */
import { Definitions } from '../../composants/mise-en-page/Definitions'
import { Badge } from '../../composants/retour/Badge'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { date, horodatage, montant, nombre, VIDE } from '../../lib/format'
import { statut } from '../../lib/statuts'
import styles from '../plan-achat/achats.module.css'
import { libelleUnite } from '../plan-achat/libelles'
import type { CommandeFiche, Decision, ReceptionDuBon } from './types'

const COLONNES_RECEPTIONS: Colonne<ReceptionDuBon>[] = [
  {
    cle: 'numero',
    titre: 'Réception',
    valeur: (r) => r.numero ?? 'Brouillon',
    lien: (r) => `/receptions/${r.id}`,
  },
  { cle: 'date', titre: 'Arrivée', rendu: (r) => date(r.date) },
  {
    cle: 'statut',
    titre: 'Statut',
    valeur: (r) => statut('document', r.statut).libelle,
    rendu: (r) => <Badge famille="document" valeur={r.statut} />,
  },
  {
    cle: 'pese',
    titre: 'Pesé (kg)',
    aide: 'Pesé pour ce bon (hors refus)',
    droite: true,
    unite: 'kg',
    total: true,
    rendu: (r) => nombre(r.pese),
  },
]

export function VoletReceptions({ c, onOuvrir }: { c: CommandeFiche; onOuvrir: (id: number) => void }) {
  return (
    <div className={styles.tableFenetre}>
      <DataTable<ReceptionDuBon>
        libelle="Réceptions du bon"
        lignes={c.receptions}
        colonnes={COLONNES_RECEPTIONS}
        cle={(r) => r.id}
        recherche={false}
        hauteur="fenetre"
        cliquable={(r) => onOuvrir(r.id)}
        vide="Rien n’est encore arrivé sur ce bon."
      />
    </div>
  )
}

function colonnesDecisions(c: CommandeFiche): Colonne<Decision>[] {
  return [
    { cle: 'quand', titre: 'Le', rendu: (d) => horodatage(d.quand) },
    { cle: 'par', titre: 'Par', valeur: (d) => d.par ?? VIDE },
    {
      cle: 'decision',
      titre: 'Décision',
      valeur: (d) => statut('decision', d.decision).libelle,
      rendu: (d) => <Badge famille="decision" valeur={d.decision} />,
    },
    {
      cle: 'montant',
      titre: 'Montant estimé (MAD)',
      droite: true,
      valeur: (d) => d.montant_apres ?? d.montant_avant ?? null,
      rendu: (d) =>
        d.montant_apres == null
          ? VIDE
          : `${d.montant_avant != null && d.montant_avant !== d.montant_apres ? `${montant(d.montant_avant, 'MAD')} → ` : ''}${montant(d.montant_apres, 'MAD')}`,
    },
    {
      cle: 'envoye',
      titre: 'Envoyé le',
      rendu: (d) => (d.decision === 'approbation' && c.numero ? date(c.date_commande) : VIDE),
    },
    {
      cle: 'motif',
      titre: 'Motif',
      rendu: (d) => (
        <span className={styles.coupe} title={d.motif}>
          {d.motif || VIDE}
        </span>
      ),
    },
  ]
}

export function VoletApprobation({ c }: { c: CommandeFiche }) {
  const v = c.version_partie
  return (
    <div className={styles.volet}>
      <span className={styles.note}>
        Seuil d’approbation : {montant(c.seuil_approbation, 'MAD')}
        {c.cours ? ` · cours du bon : 1 ${c.devise} = ${nombre(c.cours, 4)} MAD` : ''}
      </span>
      <div className={styles.tableFenetre}>
        <DataTable<Decision>
          libelle="Décisions sur le bon"
          lignes={c.decisions}
          colonnes={colonnesDecisions(c)}
          cle={(d) => `${d.quand}-${d.decision}`}
          recherche={false}
          hauteur="court"
        />
      </div>
      {v ? (
        <Definitions
          colonnes={2}
          items={[
            ['Version partie', `figée le ${horodatage(v.figee_le)}${v.motif ? ` (${v.motif})` : ''}`],
            ['Montant de référence', montant(v.montant_reference, c.devise)],
            ...v.lignes.map((l): [string, string] => [
              l.reference,
              `${nombre(l.quantite)} kg · ${libelleUnite(l.unite_achat, l.contenance)}`,
            ]),
          ]}
        />
      ) : null}
    </div>
  )
}
