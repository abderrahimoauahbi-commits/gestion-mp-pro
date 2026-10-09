/**
 * Le pied de la préparation : arrondir au conditionnement, revenir à la suggestion, poser nos prix
 * du catalogue (jamais imprimés), annuler (gardé si la saisie est sale), et créer le ou les bons
 * en brouillon — un par devise, dans la même transaction (`POST /commandes` rend la liste).
 */
import { useFermerFenetre } from '../../composants/mise-en-page/Fenetre'
import { Bouton } from '../../composants/saisie/Bouton'
import { Interrupteur } from '../../composants/saisie/Interrupteur'
import { api } from '../../lib/api'
import { kg } from '../../lib/format'
import { useEcriture } from '../../lib/requetes'
import styles from './achats.module.css'
import { corps, devisesDe, retenues, totaux } from './calculPreparation'
import type { CommandeCreee } from './types'
import type { SaisiePreparation } from './useSaisiePreparation'

/** « Créer le bon en brouillon · 1 234 kg » ou « Créer 2 bons (un par devise : EUR, USD) · … ». */
export function libelleCreer(devises: readonly string[], kilos: number): string {
  return devises.length > 1
    ? `Créer ${devises.length} bons (un par devise : ${devises.join(', ')}) · ${kg(kilos)}`
    : `Créer le bon en brouillon · ${kg(kilos)}`
}

export function PiedPreparation({
  s,
  fournisseurId,
  onCree,
}: {
  s: SaisiePreparation
  fournisseurId: number
  onCree: (c: CommandeCreee[]) => void
}) {
  const fermer = useFermerFenetre()
  const creer = useEcriture(() =>
    api.post<CommandeCreee[]>(
      '/commandes',
      corps(
        {
          fournisseurId,
          livraison: s.livraison,
          observations: s.observations,
          prixCatalogue: s.prixCatalogue,
        },
        s.lignes,
      ),
    ),
  )
  const kilos = totaux(s.lignes, []).kilos
  return (
    <div className={styles.pied}>
      <Bouton onClick={s.arrondir} titre="Chaque quantité monte au conditionnement entier suivant">
        Arrondir au conditionnement
      </Bouton>
      <Bouton onClick={s.revenir} titre="Retrouver les quantités calculées, sans les lignes ajoutées">
        Revenir à la suggestion
      </Bouton>
      <span title="Le bon envoyé au fournisseur ne porte jamais de prix. Cochée, nos prix du catalogue sont notés sur le bon, ici seulement, à confirmer par le fournisseur">
        <Interrupteur
          valeur={s.prixCatalogue}
          onChange={s.setPrixCatalogue}
          libelle="Pré-remplir nos prix du catalogue (non imprimés)"
        />
      </span>
      <span className={styles.pousse} />
      <Bouton onClick={fermer}>Annuler</Bouton>
      <Bouton
        variante="principal"
        attente="Création…"
        manque={retenues(s.lignes).length ? undefined : ['cochez au moins une ligne avec une quantité']}
        titre="Le bon est créé en brouillon, sans numéro : il se relit, s’imprime et s’envoie depuis l’écran Commandes"
        onClick={async () => onCree(await creer.mutateAsync())}
      >
        {libelleCreer(devisesDe(s.lignes), kilos)}
      </Bouton>
    </div>
  )
}
