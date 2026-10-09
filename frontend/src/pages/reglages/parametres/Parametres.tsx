/**
 * Réglages › Paramètres (`/reglages?onglet=parametres`) : les réglages de calcul, famille par
 * famille (liste verticale, compteur des modifications ; `?famille=`). La direction écrit, les
 * achats lisent. Bornes et ordres des seuils contrôlés **à la frappe**, avec la phrase du serveur ;
 * « Enregistrer N modification(s) » grisé avec ses raisons ; tout ou rien, à la version lue.
 * Le brouillon vit dans la page Réglages : changer de famille ou d'onglet ne le perd pas (P8-8).
 * La période close et les réglages techniques ont leurs onglets (Réglages › Période close,
 * Administration › Courriel et Technique) ; « Méthode de calcul » est dans l'aide.
 */
import { useSearchParams } from 'react-router'

import { Carte } from '../../../composants/mise-en-page/Carte'
import { Grille } from '../../../composants/mise-en-page/Grille'
import { dire } from '../../../composants/retour/Messages'
import { Note } from '../../../composants/retour/Note'
import { Bouton } from '../../../composants/saisie/Bouton'
import { Confirmer } from '../../../composants/saisie/Confirmer'
import { Cadre } from '../../../composants/tableaux/Cadre'
import { avecParametre } from '../../../lib/adresse'
import { api } from '../../../lib/api'
import { nombre } from '../../../lib/format'
import { useEcriture } from '../../../lib/requetes'
import styles from '../reglages.module.css'
import { ChampReglage } from './ChampReglage'
import { corps, FAMILLES_AILLEURS, poser, refus, type Brouillon, type Reglage } from './logique'

/** Ce que règle chaque famille : une phrase au-dessus de ses champs (ECRANS-PRO P8-18). */
export const PHRASES_FAMILLES: Readonly<Record<string, string>> = {
  'Couverture et statuts':
    'Les couvertures critique et d’ATTENTION ne règlent que le « statut classeur », gardé pour comparaison. Le statut qui décide — Cockpit, plan d’achat, courriel du lundi, quantités à commander — compare le stock projeté à son seuil d’alerte (réglé dans Approvisionnement). Le stock dormant compte les jours sans sortie ni entrée.',
  Approvisionnement:
    'La fenêtre de réapprovisionnement et les marges appliquées au calcul des quantités à commander : délai, couverture d’une commande, sécurité par classe, pertes, croissance du plan. La sécurité par classe et le stock minimum font le seuil d’alerte, qui décide du statut.',
  'Classification ABC / XYZ':
    'ABC classe les matières par valeur consommée : A pour l’essentiel de la dépense, puis B, puis C. XYZ les classe par régularité de la demande mensuelle (CV = écart-type ÷ moyenne) : X régulière, Y variable, Z erratique.',
  "Politique d'achat":
    'Les montants qui classent un bon de commande (groupé ou standard), les tiers de priorité du plan d’achat, et le seuil au-delà duquel la direction approuve une commande avant l’envoi. L’urgence ne vient jamais du montant.',
  'Réceptions et fournisseurs':
    'Les tolérances de réception (pesée, poids de bobine, livraison complète) et la notation des fournisseurs : OTIF = à l’heure × complète × conforme, et les scores qui classent.',
  'Stock et inventaire':
    'La tolérance proposée à l’ouverture d’un inventaire : au-delà, un écart de comptage se justifie avant la validation.',
  Prix: 'Ce qui colore la matrice des prix (forte hausse), borne la comparaison des opportunités (deux prix de la même époque) et contrôle les dossiers d’importation (TVA, TPI, frais, facture).',
  Trésorerie:
    'Le délai client moyen entre dans le cycle de trésorerie du Cockpit (stock + clients − fournisseurs).',
  Société:
    'Ce qui s’imprime sur le papier à en-tête des bons et des documents. La période close a son onglet ; l’adresse des QR et le courriel du lundi se règlent dans l’Administration.',
}

/** Les familles de l'onglet, dans l'ordre du serveur. */
export function familles(reglages: readonly Reglage[]): string[] {
  return [...new Set(reglages.map((r) => r.famille))].filter((f) => !FAMILLES_AILLEURS.has(f))
}

function Familles({ liste, active, brouillon, reglages, onChoisir }: FamillesProps) {
  return (
    <nav className={styles.familles} aria-label="Familles de réglages">
      {liste.map((f) => {
        const n = reglages.filter((r) => r.famille === f && r.cle in brouillon).length
        return (
          <button
            key={f}
            type="button"
            className={f === active ? styles.familleActive : styles.famille}
            aria-current={f === active ? 'true' : undefined}
            title={n ? `${n} modification(s) pas encore enregistrée(s)` : undefined}
            onClick={() => onChoisir(f)}
          >
            {f}
            {n ? <span className={styles.compte}>{nombre(n)}</span> : null}
          </button>
        )
      })}
    </nav>
  )
}

interface FamillesProps {
  liste: readonly string[]
  active: string
  brouillon: Brouillon
  reglages: readonly Reglage[]
  onChoisir: (f: string) => void
}

interface ParametresProps {
  reglages: readonly Reglage[]
  brouillon: Brouillon
  onBrouillon: (b: Brouillon) => void
  ecrit: boolean
  onHistorique?: () => void
}

function Gestes({ reglages, brouillon, onBrouillon, onHistorique }: ParametresProps) {
  const n = Object.keys(brouillon).length
  const raisons = refus(reglages, brouillon)
  const ecrire = useEcriture(() => api.put<Reglage[]>('/parametres', corps(reglages, brouillon)))
  return (
    <>
      {onHistorique ? <Bouton onClick={onHistorique}>Historique des changements</Bouton> : null}
      {n ? (
        <Confirmer
          question={`Abandonner ${n} modification(s) ?`}
          oui="Oui, abandonner"
          onOui={() => onBrouillon({})}
        >
          Annuler
        </Confirmer>
      ) : null}
      <Bouton
        variante="principal"
        grise={n ? undefined : 'Aucune modification'}
        blocages={raisons}
        attente="Enregistrement…"
        onClick={async () => {
          await ecrire.mutateAsync()
          onBrouillon({})
          dire(`${n} paramètre(s) enregistré(s) : tout le pilotage est recalculé.`)
        }}
      >
        {n ? `Enregistrer ${n} modification(s)` : 'Aucune modification'}
      </Bouton>
    </>
  )
}

export function Parametres(props: ParametresProps) {
  const { reglages, brouillon, onBrouillon, ecrit } = props
  const [params, setParams] = useSearchParams()
  const liste = familles(reglages)
  const active = liste.find((f) => f === params.get('famille')) ?? liste[0] ?? ''
  const visibles = reglages.filter((r) => r.famille === active)
  const raisons = refus(reglages, brouillon)
  return (
    <Carte
      titre={active}
      actions={ecrit ? <Gestes {...props} /> : null}
      serre
      remplir
      className={styles.carteListe}
    >
      <div className={styles.parametres}>
        <Familles
          liste={liste}
          active={active}
          brouillon={brouillon}
          reglages={reglages}
          onChoisir={(f) =>
            setParams((p) => avecParametre(p, 'famille', f === liste[0] ? null : f), { replace: true })
          }
        />
        <Cadre hauteur="page">
          <div className={styles.champs}>
            {PHRASES_FAMILLES[active] ? <Note>{PHRASES_FAMILLES[active]}</Note> : null}
            {!ecrit ? (
              <Note ton="attention">Les paramètres se règlent par la direction : lecture seule.</Note>
            ) : null}
            {raisons.length ? <Note ton="critique">{raisons.join(' ')}</Note> : null}
            <Grille colonnes={2}>
              {visibles.map((r) => (
                <ChampReglage
                  key={r.cle}
                  r={r}
                  saisie={brouillon[r.cle]}
                  ecrit={ecrit}
                  onChange={(v) => onBrouillon(poser(brouillon, r, v))}
                />
              ))}
            </Grille>
          </div>
        </Cadre>
      </div>
    </Carte>
  )
}
