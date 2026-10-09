/**
 * Onglet « Qualités » (`/qualites?onglet=qualites`) : une ligne par qualité — poids au m² de
 * chaque rôle utilisé (kg/m², ml/m² pour un rôle au mètre), poids de la recette, coût au m²
 * (absent pour l'alimentation), plan, état de la recette. Recherche et case « avec les
 * arrêtées » sous le titre (P7-26) ; une ligne ouvre la fiche (`/qualites/:id`).
 */
import { useMemo } from 'react'

import { Carte } from '../../composants/mise-en-page/Carte'
import { Badge } from '../../composants/retour/Badge'
import { Interrupteur } from '../../composants/saisie/Interrupteur'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { m2, nombre, prix, VIDE } from '../../lib/format'
import styles from '../catalogue/catalogue.module.css'
import { deux } from '../catalogue/colonnesMatieres'
import { useEtatListe } from '../catalogue/etatListe'
import { recetteJuste, rolesSansMatiere } from './indicateurs'
import type { Qualite } from './types'

/** « Poil 98,0 % · Ruban 0,0 % », « juste · 4 matière(s) », « aucune matière ». */
export function BadgeRecette({ q }: { q: Qualite }) {
  if (!q.recette.length) return <Badge ton="attention">aucune matière</Badge>
  if (recetteJuste(q)) return <Badge ton="ok">{`juste · ${nombre(q.recette.length)} matière(s)`}</Badge>
  const fautes = [
    ...q.controle.ecarts.map((e) => `${e.role} ${nombre(e.somme, 1)} %`),
    ...rolesSansMatiere(q).map((r) => `${r} sans matière`),
  ]
  return <Badge ton="critique">{fautes.join(' · ')}</Badge>
}

/** Une colonne par rôle utilisé par au moins une qualité, dans l'ordre des rôles. */
function colonnesRoles(qualites: readonly Qualite[]): Colonne<Qualite>[] {
  const roles = new Map<number, { role: string; lineaire: boolean }>()
  for (const q of qualites)
    for (const p of q.poids) roles.set(p.role_id, { role: p.role, lineaire: p.lineaire })
  return [...roles.entries()].map(([id, r]) => ({
    cle: `role-${id}`,
    titre: r.role,
    aide: `${r.role} en ${r.lineaire ? 'ml/m²' : 'kg/m²'}`,
    droite: true,
    valeur: (q) => q.poids.find((p) => p.role_id === id)?.poids ?? null,
    rendu: (q) => {
      const p = q.poids.find((x) => x.role_id === id)?.poids
      return p ? nombre(p, 4) : VIDE
    },
  }))
}

function colonnes(qualites: readonly Qualite[], voitPrix: boolean): Colonne<Qualite>[] {
  const qualite: Colonne<Qualite> = {
    cle: 'code',
    titre: 'Qualité',
    rendu: (q) =>
      deux(
        <>
          <span className={q.actif ? styles.code : `${styles.code} ${styles.eteinte}`}>{q.code}</span>
          {q.actif ? null : (
            <>
              {' '}
              <Badge ton="neutre">arrêtée</Badge>
            </>
          )}
        </>,
        q.nom,
      ),
    recherche: (q) => [q.nom],
  }
  const fin: (Colonne<Qualite> | null)[] = [
    {
      cle: 'kg_m2',
      titre: 'Poids recette',
      aide: 'Ce que pèsent les matières de la recette pour un m², en kg',
      droite: true,
      rendu: (q) => nombre(q.kg_m2, 4),
    },
    voitPrix
      ? {
          cle: 'cout_m2_mad',
          titre: 'Coût',
          aide: 'MAD par m², perte matière comprise',
          droite: true,
          rendu: (q) => (q.cout_m2_mad == null ? VIDE : prix(q.cout_m2_mad)),
        }
      : null,
    {
      cle: 'base_mensuelle',
      titre: 'Plan',
      aide: 'm² par mois ordinaire',
      droite: true,
      rendu: (q) => m2(q.base_mensuelle),
    },
    {
      cle: 'recette',
      titre: 'Recette',
      valeur: (q) => (recetteJuste(q) ? 'juste' : 'à corriger'),
      rendu: (q) => <BadgeRecette q={q} />,
    },
  ]
  return [qualite, ...colonnesRoles(qualites), ...fin.filter((c): c is Colonne<Qualite> => c !== null)]
}

export function OngletQualites({
  qualites,
  voitPrix,
  onOuvrir,
}: {
  qualites: readonly Qualite[]
  voitPrix: boolean
  onOuvrir: (id: number) => void
}) {
  const etat = useEtatListe('q', ['arretees'])
  const avecArretees = etat.lire('arretees') === '1'
  const lignes = useMemo(() => qualites.filter((q) => avecArretees || q.actif), [qualites, avecArretees])
  const cols = useMemo(() => colonnes(qualites, voitPrix), [qualites, voitPrix])
  return (
    <Carte titre="Les qualités" serre remplir>
      <DataTable<Qualite>
        libelle="Qualités"
        lignes={lignes}
        colonnes={cols}
        cle={(q) => q.id}
        recherche={etat.recherche}
        choix={etat.choix}
        rechercheCachee={(q) => q.recette.map((l) => l.reference)}
        placeholder="Code, nom, matière de la recette…"
        triInitial={{ cle: 'code', sens: 1 }}
        cliquable={(q) => onOuvrir(q.id)}
        vide={qualites.length ? 'Aucune qualité ne correspond.' : 'Aucune qualité pour le moment.'}
        outils={
          <Interrupteur
            valeur={avecArretees}
            onChange={(v) => etat.choix.poser('arretees', v ? '1' : null)}
            libelle={`avec les arrêtées (${nombre(qualites.length - qualites.filter((q) => q.actif).length)})`}
          />
        }
      />
    </Carte>
  )
}
