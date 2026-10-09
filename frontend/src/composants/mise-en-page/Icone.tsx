/**
 * Les icônes du système, au trait, sur une grille de 24 (reprises de GMAO PRO) : aucune
 * dépendance, aucune émoticône (REGLES-ECRAN § 5). La couleur est celle du texte (`currentColor`).
 */
import { classes } from './classes'
import styles from './Icone.module.css'

const TRACES = {
  accueil: 'M3 11l9-8 9 8M5 9.5V21h5v-6h4v6h5V9.5',
  aide: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3M12 17h.01',
  attention: 'M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0zM12 9v4M12 17h.01',
  camera: 'M4 7h3l2-3h6l2 3h3v13H4zM12 17a4 4 0 1 0 0-8 4 4 0 0 0 0 8z',
  chevron: 'M9 6l6 6-6 6',
  chevronBas: 'M6 9l6 6 6-6',
  cloche: 'M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.7 21a2 2 0 0 1-3.4 0',
  coche: 'M5 12l5 5L20 7',
  compte: 'M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z',
  croix: 'M18 6L6 18M6 6l12 12',
  deconnexion: 'M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9',
  document: 'M6 3h9l4 4v14H6zM14 3v5h5',
  envoyer: 'M4 12h13M12 6l6 6-6 6M20 4v16',
  imprimer: 'M6 9V3h12v6M6 18H4v-7h16v7h-2M6 14h12v7H6z',
  info: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 16v-4M12 8h.01',
  lots: 'M21 8l-9-5-9 5 9 5zM3 8v8l9 5 9-5V8M12 13v8',
  menu: 'M3 6h18M3 12h18M3 18h18',
  moins: 'M5 12h14',
  piece:
    'M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.8-3.8a6 6 0 0 1-7.9 7.9l-6.9 6.9a2.1 2.1 0 0 1-3-3l6.9-6.9a6 6 0 0 1 7.9-7.9z',
  plus: 'M12 5v14M5 12h14',
  precedent: 'M15 6l-6 6 6 6',
  recherche: 'M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM21 21l-4.3-4.3',
  retour: 'M20 12H7M12 6l-6 6 6 6M4 4v16',
  signaler: 'M4 22V4M4 4h13l-2 4 2 4H4',
  telecharger: 'M12 3v12M7 10l5 5 5-5M5 21h14',
  usine: 'M3 21h18M5 21V9l5 3V9l5 3V5h4v16',
} as const

export type NomIcone = keyof typeof TRACES

/** Une icône décorative (cachée aux lecteurs d'écran : le libellé voisin dit ce qu'elle montre). */
export function Icone({
  nom,
  taille = 16,
  className,
}: {
  nom: NomIcone
  taille?: number
  className?: string
}) {
  return (
    <svg
      className={classes(styles.icone, className)}
      viewBox="0 0 24 24"
      width={taille}
      height={taille}
      aria-hidden="true"
      focusable="false"
    >
      <path d={TRACES[nom]} />
    </svg>
  )
}

/** Les noms d'icônes connus (essais, démonstration). */
export const NOMS_ICONES = Object.keys(TRACES)
