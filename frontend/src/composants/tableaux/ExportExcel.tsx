/**
 * « Exporter en Excel » (REGLES-ECRAN § 3) : le classeur du serveur (`/api/export/...`), qui
 * **respecte la vue** — l'onglet, la recherche et les filtres partent avec la demande. Sans route
 * (une petite liste sans export serveur), `exporterCsv` écrit ce qui est affiché.
 */
import { adresseApi } from '../../lib/api'
import { nombre } from '../../lib/format'
import { aujourdhui } from '../../lib/heure'
import { Icone } from '../mise-en-page/Icone'
import { brute, type Colonne } from './colonnes'
import styles from './ExportExcel.module.css'

type Parametre = string | number | boolean | null | undefined

export function ExportExcel({
  route,
  parametres,
  libelle = 'Exporter en Excel',
}: {
  route: string
  parametres?: Record<string, Parametre>
  libelle?: string
}) {
  return (
    <a
      className={styles.export}
      href={adresseApi(route, parametres)}
      download
      title="Le classeur de ce qui est affiché : onglet, recherche et filtres compris"
    >
      <Icone nom="telecharger" />
      {libelle}
    </a>
  )
}

/** Une cellule CSV : nombre à virgule, texte protégé (une formule saisie ne s'exécute pas dans Excel). */
function cellule(v: unknown): string {
  if (v == null) return ''
  let s =
    typeof v === 'number'
      ? nombre(v, 0, 6)
          .replace(/\u00a0/g, '')
          .replace('−', '-')
      : String(v)
  if (typeof v !== 'number' && /^[=+\-@\t\r]/.test(s)) s = `'${s}`
  return /[;"\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
}

/** Le texte CSV (séparateur « ; », UTF-8 avec BOM pour Excel) des lignes et colonnes exportées. */
export function texteCsv<T>(colonnes: readonly Colonne<T>[], lignes: readonly T[]): string {
  const cols = colonnes.filter((c) => c.exporte !== false)
  const tete = cols.map((c) => cellule(c.titre)).join(';')
  const corps = lignes.map((l) => cols.map((c) => cellule(brute(c, l))).join(';'))
  return `\ufeff${[tete, ...corps].join('\r\n')}`
}

/** Télécharge ce qui est affiché en CSV : « lots-2026-10-08.csv ». */
export function exporterCsv<T>(fichier: string, colonnes: readonly Colonne<T>[], lignes: readonly T[]): void {
  const blob = new Blob([texteCsv(colonnes, lignes)], { type: 'text/csv;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `${fichier}-${aujourdhui()}.csv`
  a.click()
  URL.revokeObjectURL(a.href)
}
