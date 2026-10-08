/** Démonstration des tableaux : DataTable de 300 lots dans son cadre (hauteur restante), filtres liés, totaux par unité. */
import { useState } from 'react'

import { date, INSECABLE, kg, nombre } from '../../lib/format'
import { Carte } from '../mise-en-page/Carte'
import { Fenetre } from '../mise-en-page/Fenetre'
import { Indicateurs } from '../mise-en-page/Indicateurs'
import { Page } from '../mise-en-page/Page'
import { Badge } from '../retour/Badge'
import { Kpi } from '../retour/Kpi'
import { DataTable } from '../tableaux/DataTable'
import type { Colonne } from '../tableaux/colonnes'
import { useEtatTableAdresse } from '../tableaux/etatAdresse'
import type { Filtre } from '../tableaux/filtrage'
import { LOTS, type LotExemple } from './donnees'

const COLONNES: Colonne<LotExemple>[] = [
  { cle: 'numero', titre: 'Lot', lien: (l) => `/lots/${l.id}` },
  { cle: 'matiere', titre: 'Matière', recherche: (l) => [l.code, l.couleur] },
  { cle: 'fournisseur', titre: 'Fournisseur' },
  { cle: 'magasin', titre: 'Magasin' },
  { cle: 'entree', titre: 'Entré le', rendu: (l) => date(l.entree) },
  { cle: 'statut', titre: 'Statut', rendu: (l) => <Badge famille="lot" valeur={l.statut} /> },
  {
    cle: 'reste',
    titre: 'Reste',
    droite: true,
    unite: (l) => l.unite,
    total: true,
    rendu: (l) => (l.unite === 'kg' ? kg(l.reste) : `${nombre(l.reste, 1)}${INSECABLE}ml`),
  },
]

const FILTRES: Filtre<LotExemple>[] = [
  { cle: 'fournisseur', libelle: 'Fournisseur', valeur: (l) => l.fournisseur },
  { cle: 'couleur', libelle: 'Couleur', valeur: (l) => l.couleur },
  { cle: 'magasin', libelle: 'Magasin', valeur: (l) => l.magasin },
  {
    cle: 'statut',
    libelle: 'Statut',
    valeur: (l) => l.statut,
    libelleValeur: (v) =>
      ({
        disponible: 'Disponible',
        partiel: 'En partie en quarantaine',
        quarantaine: 'En quarantaine',
        epuise: 'Épuisé',
      })[v] ?? v,
  },
]

export function DemoTableaux() {
  const etat = useEtatTableAdresse(FILTRES.map((f) => f.cle))
  const [ouvert, setOuvert] = useState<LotExemple | null>(null)
  return (
    <Page titre="Tableaux">
      <Indicateurs>
        <Kpi
          titre="Lots"
          valeur={nombre(LOTS.length)}
          formule="Nombre de lots dont le reste n’est pas nul, tous magasins."
        />
        <Kpi
          titre="En quarantaine"
          valeur={nombre(LOTS.filter((l) => l.statut === 'quarantaine').length)}
          ton="critique"
          formule="Lots du magasin de quarantaine : en stock, sans compter pour les achats."
        />
        <Kpi
          titre="Reste en kilos"
          valeur={kg(LOTS.filter((l) => l.unite === 'kg').reduce((s, l) => s + l.reste, 0))}
          formule="Σ reste des lots en kilos (les mètres de cuir, franges et ruban à part)."
        />
      </Indicateurs>
      <Carte titre="Lots" sous="Recherche : « rouge frise », « c5n », « fes camel »…" serre remplir>
        <DataTable
          lignes={LOTS}
          colonnes={COLONNES}
          cle={(l) => l.id}
          filtres={FILTRES}
          {...etat}
          cliquable={setOuvert}
          marquee={(l) => l.statut === 'quarantaine'}
          exporter={{ route: '/export/lots', parametres: { onglet: 'lots' } }}
          libelle="Lots"
        />
      </Carte>
      {ouvert ? (
        <Fenetre titre={ouvert.numero} sous={ouvert.matiere} onFermer={() => setOuvert(null)} taille="large">
          <p>
            {ouvert.fournisseur} · {ouvert.magasin} · reste{' '}
            {ouvert.unite === 'kg' ? kg(ouvert.reste) : `${nombre(ouvert.reste, 1)} ml`}
          </p>
        </Fenetre>
      ) : null}
    </Page>
  )
}
