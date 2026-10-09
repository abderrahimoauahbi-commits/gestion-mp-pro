/**
 * Le haut de la saisie d'un camion (ECRANS-PRO 4.16) : le n° du bon que le chauffeur apporte (ou le
 * fournisseur), la date d'arrivée, le BL, le contrôle au quai, les factures par devise, les bons du
 * camion à cocher et l'ajout d'une matière hors commande.
 */
import { Grille } from '../../composants/mise-en-page/Grille'
import { Note } from '../../composants/retour/Note'
import { Champ } from '../../composants/saisie/Champ'
import { DateChamp } from '../../composants/saisie/DateChamp'
import { Nombre } from '../../composants/saisie/Nombre'
import { Saisie } from '../../composants/saisie/Saisie'
import { Selecteur } from '../../composants/saisie/Selecteur'
import { date, kg, montant, nombre, part } from '../../lib/format'
import { useSession } from '../../lib/session'
import type { CommandeResume } from '../commandes/types'
import styles from '../plan-achat/achats.module.css'
import { devisesDuCamion } from './calculSaisie'
import { bonOuvert, type Referentiels, type SaisieReception } from './useSaisieReception'

function resumeFacture(s: SaisieReception, devises: readonly string[]): string {
  const faites = devises.map((d) => [d, s.factures[d]] as const).filter(([, f]) => f?.numero.trim())
  if (!faites.length) return 'facultative ici : elle se complète aussi après la validation'
  return faites
    .map(([d, f]) =>
      [
        `n° ${f?.numero}`,
        f?.montant ? montant(f.montant, d) : '',
        f?.echeance ? `échéance ${date(f.echeance)}` : '',
      ]
        .filter(Boolean)
        .join(' · '),
    )
    .join(' ; ')
}

export function FacturesSaisie({ s }: { s: SaisieReception }) {
  const camion = devisesDuCamion(s.lignes)
  const devises = camion.length ? camion : [s.fournisseur?.devise ?? 'MAD']
  const delai = s.fournisseur?.delai_paiement_jours ?? 0
  return (
    <details className={styles.repli}>
      <summary>
        <strong>Facture du fournisseur</strong>{' '}
        <span className={styles.note}>{resumeFacture(s, devises)}</span>
      </summary>
      {devises.map((d) => {
        const f = s.factures[d] ?? { numero: '', date: '', montant: null, echeance: '' }
        const sans = !f.numero.trim()
        return (
          <Grille key={d} colonnes={4}>
            <Champ libelle={devises.length > 1 ? `N° de facture (${d})` : 'N° de facture'}>
              <Saisie valeur={f.numero} onChange={(numero) => s.poserFacture(d, { numero })} max={60} />
            </Champ>
            <Champ libelle="Date de facture" aide={sans ? 'sans n°, pas de facture' : undefined}>
              <DateChamp valeur={f.date} onChange={(v) => s.poserFacture(d, { date: v })} desactive={sans} />
            </Champ>
            <Champ libelle={`Montant de la facture (${d})`}>
              <Nombre
                valeur={f.montant}
                onChange={(montant) => s.poserFacture(d, { montant })}
                min={0}
                decimales={2}
                unite={d}
                desactive={sans}
              />
            </Champ>
            <Champ
              libelle="Échéance"
              aide={
                delai
                  ? `proposée : date de facture + ${nombre(delai)} j`
                  : 'le délai de paiement du fournisseur n’est pas réglé'
              }
            >
              <DateChamp
                valeur={f.echeance}
                onChange={(echeance) => s.poserFacture(d, { echeance })}
                min={f.date || undefined}
                futurPermis
                desactive={sans}
              />
            </Champ>
          </Grille>
        )
      })}
    </details>
  )
}

function BonsDuCamion({ s, bons }: { s: SaisieReception; bons: readonly CommandeResume[] }) {
  const dedans = new Set(s.lignes.map((l) => l.commande_id))
  if (!bons.length)
    return (
      <span className={styles.note} title="Un bon encore en brouillon doit d’abord être marqué comme envoyé">
        Aucun bon envoyé n’attend de livraison chez ce fournisseur : ajoutez les matières hors commande.
      </span>
    )
  return (
    <span className={styles.rangeeCentree} role="group" aria-label="Bons de commande dans ce camion">
      {bons.map((c) => (
        <label key={c.id} className={styles.rangeeCentree}>
          <input
            type="checkbox"
            checked={dedans.has(c.id)}
            onChange={(e) => s.basculerBon(c, e.target.checked)}
          />
          {c.numero} · {kg(c.reste_kg)} à livrer · {part(c.part_livree, 0)} déjà reçu
          {c.statut === 'a_approuver' ? (
            <span className={styles.attention}> (attend l’approbation)</span>
          ) : null}
        </label>
      ))}
    </span>
  )
}

function ChoixBonEtFournisseur({ s, donnees }: { s: SaisieReception; donnees: Referentiels }) {
  const ouverts = donnees.bons.filter(bonOuvert)
  const fournisseurs = donnees.fournisseurs.filter((f) => f.actif || f.id === s.fournisseurId)
  return (
    <>
      <Champ libelle="N° du bon de commande (le chauffeur l’apporte)">
        <Selecteur<number>
          valeur={null}
          options={ouverts.map((c) => ({
            id: c.id,
            titre: `${c.numero} — ${c.fournisseur}`,
            sous: `${kg(c.reste_kg)} à livrer`,
          }))}
          placeholder="ou taper le n° du bon…"
          onChange={(id) => {
            const c = ouverts.find((x) => x.id === id)
            if (c) s.choisirBon(c)
          }}
        />
      </Champ>
      <Champ libelle="Fournisseur">
        <Selecteur<number>
          valeur={s.fournisseurId}
          options={fournisseurs.map((f) => ({ id: f.id, titre: f.nom, sous: f.pays }))}
          placeholder="Taper le nom du fournisseur…"
          effacable={false}
          onChange={(id) => s.choisirFournisseur(donnees.fournisseurs.find((f) => f.id === id) ?? null)}
        />
      </Champ>
    </>
  )
}

function ChampsCamion({ s }: { s: SaisieReception }) {
  const { contexte } = useSession()
  return (
    <>
      <Champ libelle="Date d’arrivée">
        <DateChamp
          valeur={s.entete.date}
          onChange={(v) => s.poserEntete({ date: v })}
          min={contexte.date_cloture ?? undefined}
          raisonMin={contexte.date_cloture ? 'la période est close' : undefined}
        />
      </Champ>
      <Champ libelle="N° du BL (bon de livraison)">
        <Saisie valeur={s.entete.numeroBl} onChange={(numeroBl) => s.poserEntete({ numeroBl })} max={60} />
      </Champ>
      <Champ libelle="Contrôlé au quai par">
        <Saisie
          valeur={s.entete.controlePar}
          onChange={(controlePar) => s.poserEntete({ controlePar })}
          max={80}
        />
      </Champ>
      <Champ libelle="Observations">
        <Saisie
          placeholder="état du camion, retard…"
          valeur={s.entete.observations}
          onChange={(observations) => s.poserEntete({ observations })}
          max={500}
        />
      </Champ>
    </>
  )
}

function HorsCommande({ s, donnees }: { s: SaisieReception; donnees: Referentiels }) {
  const options = [...donnees.matieres]
    .sort(
      (a, b) => Number(b.fournisseur_id === s.fournisseurId) - Number(a.fournisseur_id === s.fournisseurId),
    )
    .map((m) => ({
      id: m.id,
      titre: m.reference,
      sous: [m.designation, m.fournisseur].filter(Boolean).join(' · '),
    }))
  return (
    <Champ
      libelle="Ajouter une matière hors commande (sans bon, échantillon, complément)"
      className={styles.champLarge}
    >
      <Selecteur<number>
        valeur={null}
        options={options}
        placeholder="Référence, couleur, titrage…"
        onChange={(id) => {
          const m = donnees.matieres.find((x) => x.id === id)
          if (m) s.ajouterHorsCommande(m)
        }}
      />
    </Champ>
  )
}

export function EnTeteSaisie({ s, donnees }: { s: SaisieReception; donnees: Referentiels }) {
  const duFournisseur = donnees.bons.filter((c) => bonOuvert(c) && c.fournisseur_id === s.fournisseurId)
  const devises = devisesDuCamion(s.lignes)
  return (
    <>
      <Grille colonnes={3}>
        <ChoixBonEtFournisseur s={s} donnees={donnees} />
        <ChampsCamion s={s} />
      </Grille>
      {s.fournisseur ? (
        <div className={styles.rangee}>
          <Champ libelle="Bons de commande dans ce camion" groupe>
            <BonsDuCamion s={s} bons={duFournisseur} />
          </Champ>
          <HorsCommande s={s} donnees={donnees} />
        </div>
      ) : null}
      {devises.length > 1 ? (
        <Note ton="attention">
          Ce camion porte deux devises ({devises.join(', ')}) : deux réceptions seront enregistrées, une par
          devise, chacune avec sa facture.
        </Note>
      ) : null}
    </>
  )
}
