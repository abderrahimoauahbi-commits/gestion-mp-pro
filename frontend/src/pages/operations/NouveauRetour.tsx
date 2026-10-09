/**
 * « Nouveau retour des machines » (ECRANS-PRO partie 6, an. 24 ; direction, alimentation) : on
 * choisit l'ordre validé d'où revient la matière, puis la saisie du retour s'ouvre sur l'ordre
 * (`/ordres/{id}/retour`, écran du lot F2).
 *
 * La forme d'un ordre (`GET ordres?statut=valide`, route 135 du lot D6) n'est pas encore publiée par
 * l'OpenAPI : seuls les champs lus ici sont décrits, à remplacer par `Schema<'OrdreResume'>`.
 */
import { useNavigate } from 'react-router'

import { Fenetre } from '../../composants/mise-en-page/Fenetre'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { DataTable } from '../../composants/tableaux/DataTable'
import { date } from '../../lib/format'
import { useLecture } from '../../lib/requetes'

/** PROVISOIRE : ce que l'écran lit d'un ordre (route 135), en attendant l'OpenAPI du lot D6. */
interface OrdreLu {
  id: number
  numero: string | null
  date: string
  metier?: string | null
  magasin?: string | null
}

export function NouveauRetour({ onFermer }: { onFermer: () => void }) {
  const navigate = useNavigate()
  const ordres = useLecture<OrdreLu[]>('/ordres', { statut: 'valide' })
  return (
    <Fenetre
      titre="Nouveau retour des machines"
      sous="D’où revient la matière ? Choisir l’ordre validé."
      onFermer={onFermer}
    >
      {ordres.isPending ? <Chargement quoi="les ordres validés" /> : null}
      {ordres.isError ? <Erreur erreur={ordres.error} onReessayer={() => void ordres.refetch()} /> : null}
      {ordres.data ? (
        <DataTable
          libelle="Ordres validés"
          lignes={ordres.data}
          cle={(o) => o.id}
          hauteur="fenetre"
          placeholder="Numéro, métier, magasin…"
          cliquable={(o) => navigate(`/ordres/${o.id}/retour`)}
          colonnes={[
            { cle: 'numero', titre: 'Ordre', valeur: (o) => o.numero ?? '' },
            { cle: 'date', titre: 'Date', valeur: (o) => o.date, rendu: (o) => date(o.date) },
            { cle: 'metier', titre: 'Métier', valeur: (o) => o.metier ?? '' },
            { cle: 'magasin', titre: 'Magasin', valeur: (o) => o.magasin ?? '' },
          ]}
          vide="Aucun ordre validé : un retour se rattache à l’ordre d’où la matière revient."
        />
      ) : null}
    </Fenetre>
  )
}
