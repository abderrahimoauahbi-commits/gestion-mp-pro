/** Démonstration du retour : indicateurs avec formule, badges de la table des statuts, notes, montants, messages. */
import { kg as enKg } from '../../lib/format'
import { STATUTS, type Famille } from '../../lib/statuts'
import { Carte } from '../mise-en-page/Carte'
import { Definitions } from '../mise-en-page/Definitions'
import { Indicateurs } from '../mise-en-page/Indicateurs'
import { Page } from '../mise-en-page/Page'
import { Badge } from '../retour/Badge'
import { Chargement } from '../retour/Chargement'
import { Erreur } from '../retour/Erreur'
import { KgEtMetres } from '../retour/KgEtMetres'
import { Kpi } from '../retour/Kpi'
import { dire } from '../retour/Messages'
import { Montant } from '../retour/Montant'
import { Note } from '../retour/Note'
import { Pastille } from '../retour/Pastille'
import { Progression } from '../retour/Progression'
import { Vide } from '../retour/Vide'
import { ErreurApi, PAS_DE_RESEAU } from '../../lib/api'
import { Bouton } from '../saisie/Bouton'
import styles from './Demonstration.module.css'

function SixIndicateurs() {
  return (
    <Indicateurs>
      <Kpi
        titre="Valeur du stock"
        valeur={<Montant valeur={17_398_184.2} devise="MAD" court />}
        formule="Σ reste des lots × coût moyen pondéré, magasins et métiers."
        lien="/analyse?onglet=valorisation"
      />
      <Kpi
        titre="Ruptures"
        valeur={3}
        ton="rupture"
        detail="3 matières à zéro"
        formule="Matières au statut RUPTURE : disponible nul, consommées."
      />
      <Kpi
        titre="Critiques"
        valeur={7}
        ton="critique"
        detail="couverture < 15 j"
        formule="Couverture pondérée sous le seuil critique."
      />
      <Kpi
        titre="À approuver"
        valeur={2}
        ton="urgent"
        formule="Bons au-delà du seuil d’approbation, en attente de la direction."
      />
      <Kpi
        titre="Commandé"
        valeur={enKg(48_210.5)}
        formule="Σ reste à livrer des bons envoyés et confirmés."
      />
      <Kpi
        titre="Contrôles"
        valeur={0}
        ton="ok"
        detail="tous conformes"
        formule="Contrôles C01 à C38 en anomalie."
      />
    </Indicateurs>
  )
}

const FAMILLES = Object.keys(STATUTS).filter((f): f is Famille => f in STATUTS)

function TableDesStatuts() {
  return (
    <Carte titre="Badge — la table complète des statuts">
      {FAMILLES.map((famille) => (
        <div key={famille} className={styles.rangee}>
          <small>{famille}</small>
          {Object.keys(STATUTS[famille]).map((v) => (
            <Badge key={v} famille={famille} valeur={v} />
          ))}
        </div>
      ))}
    </Carte>
  )
}

export function DemoRetour() {
  return (
    <Page titre="Retour et indicateurs">
      <SixIndicateurs />
      <div className={styles.colonnes}>
        <TableDesStatuts />
        <Carte titre="Notes, chiffres, états">
          <Note>Coût moyen pondéré : chaque entrée recalcule le coût du stock restant.</Note>
          <Note ton="attention">Prix du catalogue, à confirmer par le fournisseur.</Note>
          <Note ton="critique">Frais non répartis : 1 234 MAD à part.</Note>
          <Note ton="ok">Réception validée.</Note>
          <Definitions
            items={[
              ['Cuir', <KgEtMetres key="c" kg={14.3} kgParMl={0.014} />],
              ['Au téléphone', <KgEtMetres key="t" kg={2.4952} telephone />],
              ['Deux devises', <Montant key="m" parDevise={{ USD: 61_888, EUR: 53_132 }} />],
              ['Pastille', <Pastille key="p" nombre={12} titre="ruptures et critiques" />],
              ['Reçu', <Progression key="r" part={0.62} libelle="Reçu" ton="ok" />],
            ]}
          />
          <div className={styles.rangee}>
            <Bouton onClick={() => dire('Réception validée : REC-2026-0042.')}>Dire un succès</Bouton>
            <Bouton
              onClick={() =>
                dire('Cette commande a été modifiée entre-temps par Karim (14:05) : rouvrez-la.', 'erreur')
              }
            >
              Dire un refus
            </Bouton>
          </div>
          <Chargement quoi="les lots" />
          <Erreur
            erreur={new ErreurApi(PAS_DE_RESEAU, 0, 'pas_de_reseau')}
            onReessayer={() => dire('Relu.', 'info')}
          />
          <Vide>Aucun document joint.</Vide>
        </Carte>
      </div>
    </Page>
  )
}
