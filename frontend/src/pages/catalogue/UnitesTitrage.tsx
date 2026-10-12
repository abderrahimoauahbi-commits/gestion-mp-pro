/**
 * Les unités de titrage (vue « Unités de titrage » de la classification ; direction, achats ;
 * décision de Mohamed du 12/10/2026) : la même ergonomie que les autres listes — recherche,
 * « Montrer les unités désactivées », « Ajouter une unité », une ligne ouvre l'unité en fenêtre,
 * « Désactiver » confirmé sur la ligne, « Supprimer » grisé avec la raison du serveur tant qu'un
 * titrage l'écrit. Une unité ajoutée se propose aussitôt pour un titrage et se lit dans les
 * références ; désactivée, elle ne se propose plus et ne se lit plus, les titrages la gardent.
 */
import { useMemo, useState } from 'react'

import { Badge } from '../../composants/retour/Badge'
import { dire } from '../../composants/retour/Messages'
import { Note } from '../../composants/retour/Note'
import { Bouton } from '../../composants/saisie/Bouton'
import { Confirmer } from '../../composants/saisie/Confirmer'
import { Interrupteur } from '../../composants/saisie/Interrupteur'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { api } from '../../lib/api'
import { nombre, VIDE } from '../../lib/format'
import { useEcriture } from '../../lib/requetes'
import styles from './catalogue.module.css'
import { useEtatListe } from './etatListe'
import { blocagesUnite, corpsUnite, FenetreUnite } from './FenetreUnite'
import type { Classification, UniteTitrage } from './types'

/** Les gestes d'une unité sur sa ligne : changer son état, la supprimer. */
function useGestesUnite(u: UniteTitrage) {
  const modification = useEcriture((actif: boolean) =>
    api.put<UniteTitrage>(`/classification/unites-titrage/${u.id}`, {
      ...corpsUnite({ code: u.code, libelle: u.libelle, ordre: u.ordre, actif }),
      version: u.version,
    }),
  )
  const suppression = useEcriture(() =>
    api.supprimer(`/classification/unites-titrage/${u.id}?version=${u.version}`),
  )
  return {
    changer: async (actif: boolean) => {
      const r = await modification.mutateAsync(actif)
      if (r.avertissement) dire(r.avertissement, 'attention')
      else
        dire(
          actif
            ? `Unité « ${u.code} » réactivée.`
            : `Unité « ${u.code} » désactivée : elle n’est plus proposée.`,
        )
    },
    supprimer: async () => {
      await suppression.mutateAsync()
      dire(`Unité « ${u.code} » supprimée.`)
    },
  }
}

/** Désactiver (confirmé) ou réactiver, et supprimer (grisé si employée), sur la ligne. */
function GestesUnite({ u }: { u: UniteTitrage }) {
  const { changer, supprimer } = useGestesUnite(u)
  return (
    <span
      className={styles.rangee}
      onClick={(e) => e.stopPropagation()}
      onKeyDown={(e) => e.stopPropagation()}
    >
      {u.actif ? (
        <Confirmer
          taille="petit"
          question={`Désactiver « ${u.code} » ?`}
          oui="Oui, désactiver"
          titre="Ne plus la proposer ni la lire dans une nouvelle référence ; les titrages qui l’écrivent la gardent"
          onOui={() => changer(false)}
        >
          Désactiver
        </Confirmer>
      ) : (
        <Bouton
          taille="petit"
          titre="La proposer de nouveau"
          attente="Réactivation…"
          onClick={() => changer(true)}
        >
          Réactiver
        </Bouton>
      )}
      <Confirmer
        taille="petit"
        variante="danger"
        question={`Supprimer l’unité « ${u.code} » ?`}
        oui="Oui, supprimer"
        blocages={blocagesUnite(u)}
        titre="Supprimer cette unité, qu’aucun titrage n’écrit"
        onOui={supprimer}
      >
        Supprimer
      </Confirmer>
    </span>
  )
}

const etat = (u: UniteTitrage) => (u.actif ? 'active' : 'désactivée')

const COLONNES: Colonne<UniteTitrage>[] = [
  {
    cle: 'code',
    titre: 'Code',
    rendu: (u) => (
      <span className={u.actif ? styles.code : `${styles.code} ${styles.eteinte}`}>{u.code}</span>
    ),
  },
  { cle: 'libelle', titre: 'Libellé', valeur: (u) => u.libelle || VIDE },
  { cle: 'ordre', titre: 'Ordre', droite: true },
  { cle: 'nb_titrages', titre: 'Titrages', aide: 'Titrages qui écrivent cette unité', droite: true },
  { cle: 'nb_matieres', titre: 'Matières', aide: 'Matières qui portent ces titrages', droite: true },
  {
    cle: 'actif',
    titre: 'État',
    valeur: etat,
    rendu: (u) => <Badge ton={u.actif ? 'ok' : 'neutre'}>{etat(u)}</Badge>,
  },
  { cle: 'gestes', titre: '', triable: false, exporte: false, rendu: (u) => <GestesUnite u={u} /> },
]

export function UnitesTitrage({ c }: { c: Classification }) {
  const liste = useEtatListe('cq', ['desactivees'])
  const [ouverte, setOuverte] = useState<UniteTitrage | 'nouvelle' | null>(null)
  const montrer = liste.lire('desactivees') === '1'
  const toutes = c.unites_titrage
  const lignes = useMemo(() => toutes.filter((u) => montrer || u.actif), [toutes, montrer])
  const desactivees = toutes.filter((u) => !u.actif).length
  return (
    <>
      <Note>
        Les unités du titrage, telles qu’elles s’écrivent dans les références : « 2900 Dtex », « 20 Ne », « 8
        lbs ». Une unité ajoutée se choisit aussitôt pour un titrage et se lit dans les références ; employée,
        elle ne se supprime ni ne se renomme : ajouter la nouvelle, désactiver l’ancienne.
      </Note>
      <DataTable<UniteTitrage>
        libelle="Unités de titrage"
        lignes={lignes}
        colonnes={COLONNES}
        cle={(u) => u.id}
        recherche={liste.recherche}
        choix={liste.choix}
        placeholder="Chercher une unité…"
        triInitial={{ cle: 'ordre', sens: 1 }}
        cliquable={(u) => setOuverte(u)}
        vide={toutes.length ? 'Aucune unité ne correspond.' : 'Aucune unité de titrage.'}
        outils={
          <>
            <Interrupteur
              valeur={montrer}
              onChange={(x) => liste.choix.poser('desactivees', x ? '1' : null)}
              libelle={`Montrer les unités désactivées (${nombre(desactivees)})`}
            />
            <Bouton variante="principal" icone="plus" onClick={() => setOuverte('nouvelle')}>
              Ajouter une unité
            </Bouton>
          </>
        }
      />
      {ouverte ? (
        <FenetreUnite unite={ouverte === 'nouvelle' ? null : ouverte} onFermer={() => setOuverte(null)} />
      ) : null}
    </>
  )
}
