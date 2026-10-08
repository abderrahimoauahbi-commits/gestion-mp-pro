/**
 * La démonstration : un faux cadre de coque (le vrai est le lot E2), le thème clair, sombre ou
 * du poste, et un onglet par famille de composants. « Atelier » montre un écran de téléphone.
 */
import { useEffect, useState } from 'react'

import { Bascule } from '../mise-en-page/Bascule'
import { Onglets } from '../mise-en-page/Onglets'
import { Messages } from '../retour/Messages'
import styles from './Demonstration.module.css'
import { DemoAtelier } from './DemoAtelier'
import { DemoDocuments } from './DemoDocuments'
import { DemoFenetres } from './DemoFenetres'
import { DemoGraphiques } from './DemoGraphiques'
import { DemoRetour } from './DemoRetour'
import { DemoSaisie } from './DemoSaisie'
import { DemoTableaux } from './DemoTableaux'

type Theme = 'poste' | 'clair' | 'sombre'
type Section = 'tableaux' | 'saisie' | 'retour' | 'fenetres' | 'graphiques' | 'documents' | 'atelier'

const SECTIONS = [
  { cle: 'tableaux', libelle: 'Tableaux', compte: 300 },
  { cle: 'saisie', libelle: 'Saisie' },
  { cle: 'retour', libelle: 'Retour et indicateurs', court: 'Retour' },
  { cle: 'fenetres', libelle: 'Fenêtres et confirmations', court: 'Fenêtres' },
  { cle: 'graphiques', libelle: 'Graphiques' },
  { cle: 'documents', libelle: 'Documents' },
  { cle: 'atelier', libelle: 'Atelier (téléphone)', court: 'Atelier' },
] as const

const lireTheme = (): Theme => {
  try {
    const t = localStorage.getItem('demonstration:theme')
    return t === 'clair' || t === 'sombre' ? t : 'poste'
  } catch {
    return 'poste'
  }
}

export function Demonstration() {
  const [theme, setTheme] = useState<Theme>(lireTheme)
  const [section, setSection] = useState<Section>(() => {
    const h = window.location.hash.slice(1)
    return SECTIONS.find((s) => s.cle === h)?.cle ?? 'tableaux'
  })
  useEffect(() => {
    if (theme === 'poste') document.documentElement.removeAttribute('data-theme')
    else document.documentElement.setAttribute('data-theme', theme)
    try {
      localStorage.setItem('demonstration:theme', theme)
    } catch {
      /* préférence seulement */
    }
  }, [theme])
  useEffect(() => window.history.replaceState(null, '', `#${section}`), [section])
  return (
    <div className={styles.demonstration}>
      <header className={styles.entete}>
        <strong>Gestion MP PRO · composants</strong>
        <span className={styles.pousse} />
        <Bascule
          libelle="Thème"
          valeur={theme}
          onChange={setTheme}
          vues={[
            { cle: 'poste', libelle: 'Poste' },
            { cle: 'clair', libelle: 'Clair' },
            { cle: 'sombre', libelle: 'Sombre' },
          ]}
        />
      </header>
      <main className={styles.principal}>
        <div className={styles.onglets}>
          <Onglets onglets={SECTIONS} actif={section} onChange={setSection} libelle="Familles" />
        </div>
        {section === 'tableaux' ? <DemoTableaux /> : null}
        {section === 'saisie' ? <DemoSaisie /> : null}
        {section === 'retour' ? <DemoRetour /> : null}
        {section === 'fenetres' ? <DemoFenetres /> : null}
        {section === 'graphiques' ? <DemoGraphiques /> : null}
        {section === 'documents' ? <DemoDocuments /> : null}
        {section === 'atelier' ? <DemoAtelier /> : null}
      </main>
      <Messages />
    </div>
  )
}
