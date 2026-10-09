/**
 * Onglet « Matières » (`/catalogue?onglet=matieres`) : tout le catalogue dans son cadre, la
 * recherche à la frappe sur tous les champs (cachés compris), sept filtres liés et l'état, le
 * stock des matières affichées au pied. Une ligne ouvre sa fiche (`/matieres/:id`) par-dessus la
 * liste. Direction et achats : « Exporter en Excel » (avec les filtres posés), « Tableur »,
 * « Nouvelle matière ». L'alimentation lit, sans prix ni geste.
 */
import { useMemo } from 'react'

import { Carte } from '../../composants/mise-en-page/Carte'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { Bouton } from '../../composants/saisie/Bouton'
import { DataTable } from '../../composants/tableaux/DataTable'
import { ExportExcel } from '../../composants/tableaux/ExportExcel'
import { ChoixEtat } from './ChoixEtat'
import { colonnesMatieres, filtresMatieres } from './colonnesMatieres'
import { useMatieres } from './donnees'
import { lireEtat, passeEtat, useEtatListe, type EtatListe } from './etatListe'
import type { Matiere } from './types'

/** Les paramètres de l'adresse propres à l'onglet (ses filtres, son état). */
export const CLES_MATIERES = [
  'role',
  'fournisseur',
  'composition',
  'type',
  'couleur',
  'titrage',
  'unite_titrage',
  'etat',
] as const

const ACTIF = { actives: true, desactivees: false, toutes: undefined } as const

/** « Exporter en Excel » (avec les filtres posés), « Tableur », « Nouvelle matière ». */
function Actions({
  etatListe,
  onOuvrir,
  onTableur,
}: {
  etatListe: EtatListe
  onOuvrir: (id: 'nouvelle') => void
  onTableur: () => void
}) {
  const q = etatListe.recherche.valeur.trim()
  return (
    <>
      <ExportExcel
        route="/export/matieres"
        parametres={{
          q: q || undefined,
          role: etatListe.lire('role') || undefined,
          fournisseur: etatListe.lire('fournisseur') || undefined,
          actif: ACTIF[lireEtat(etatListe.lire('etat'))],
        }}
      />
      <Bouton
        icone="telecharger"
        titre="Télécharger le catalogue en tableur, le corriger, le réimporter avec aperçu"
        onClick={onTableur}
      >
        Tableur
      </Bouton>
      <Bouton variante="principal" icone="plus" onClick={() => onOuvrir('nouvelle')}>
        Nouvelle matière
      </Bouton>
    </>
  )
}

export function OngletMatieres({
  voitPrix,
  ecrit,
  onOuvrir,
  onTableur,
}: {
  voitPrix: boolean
  ecrit: boolean
  onOuvrir: (id: number | 'nouvelle') => void
  onTableur: () => void
}) {
  const matieres = useMatieres()
  const etatListe = useEtatListe('q', CLES_MATIERES)
  const etat = lireEtat(etatListe.lire('etat'))
  const lignes = useMemo(
    () => (matieres.data ?? []).filter((m) => passeEtat(m.actif, etat)),
    [matieres.data, etat],
  )
  const colonnes = useMemo(() => colonnesMatieres(voitPrix), [voitPrix])
  const filtres = useMemo(() => filtresMatieres(matieres.data ?? []), [matieres.data])
  const actions = ecrit ? <Actions etatListe={etatListe} onOuvrir={onOuvrir} onTableur={onTableur} /> : null
  return (
    <Carte titre="Matières" actions={actions} serre remplir>
      {matieres.isPending ? <Chargement quoi="le catalogue" /> : null}
      {matieres.isError ? (
        <Erreur erreur={matieres.error} onReessayer={() => void matieres.refetch()} />
      ) : null}
      {matieres.data ? (
        <DataTable<Matiere>
          libelle="Matières du catalogue"
          lignes={lignes}
          colonnes={colonnes}
          filtres={filtres}
          cle={(m) => m.id}
          recherche={etatListe.recherche}
          choix={etatListe.choix}
          placeholder="Plusieurs mots, dans n’importe quel ordre : « rouge 2900 frisé »…"
          triInitial={{ cle: 'reference', sens: 1 }}
          cliquable={(m) => onOuvrir(m.id)}
          vide={matieres.data.length ? 'Aucune matière dans cet état.' : 'Le catalogue est vide.'}
          outils={
            <ChoixEtat
              valeur={etatListe.lire('etat')}
              onChange={(v) => etatListe.choix.poser('etat', v)}
              libelles={['Actives', 'Actives et désactivées', 'Désactivées']}
            />
          }
        />
      ) : null}
    </Carte>
  )
}
