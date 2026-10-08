/** Démonstration des graphiques SVG : barres par devise, courbes à la couleur du fil, barres horizontales, sparkline. */
import { nombre } from '../../lib/format'
import { teinteDuFil } from '../../lib/teintes'
import { BarresH } from '../graphiques/BarresH'
import { Barres } from '../graphiques/Barres'
import { Courbes } from '../graphiques/Courbes'
import { Sparkline } from '../graphiques/Sparkline'
import { Carte } from '../mise-en-page/Carte'
import { Page } from '../mise-en-page/Page'
import styles from './Demonstration.module.css'
import { MOIS } from './donnees'

const vague = (base: number, pas: number) =>
  MOIS.map((_, i) => Math.round((base + Math.sin(i / 1.7) * pas + i * pas * 0.15) * 100) / 100)

export function DemoGraphiques() {
  const rouge = teinteDuFil('Rouge') ?? undefined
  const beige = teinteDuFil('Beige') ?? undefined
  return (
    <Page titre="Graphiques">
      <div className={styles.colonnes}>
        <Carte titre="Achats par mois (deux devises : deux axes)">
          <Barres
            libelle="Achats par mois"
            etiquettes={MOIS}
            series={[
              { nom: 'En USD', valeurs: vague(40_000, 12_000), unite: 'USD' },
              { nom: 'En EUR', valeurs: vague(30_000, 9_000), unite: 'EUR' },
            ]}
            hauteur={160}
          />
        </Carte>
        <Carte titre="Prix payés (couleur du fil, trait à teinte égale)">
          <Courbes
            libelle="Prix payés"
            etiquettes={MOIS}
            series={[
              { nom: 'PP Rouge HASIRCI', valeurs: vague(2.8, 0.2), couleur: rouge, unite: 'USD / kg' },
              {
                nom: 'PP Rouge BELKA',
                valeurs: vague(2.6, 0.15).map((v, i) => (i === 4 ? null : v)),
                couleur: rouge,
                unite: 'USD / kg',
              },
              { nom: 'PP Beige HASIRCI', valeurs: vague(2.7, 0.1), couleur: beige, unite: 'USD / kg' },
            ]}
          />
        </Carte>
        <Carte titre="Achats par fournisseur">
          <BarresH
            libelle="Achats par fournisseur"
            unite="MAD"
            format={(v) => nombre(v)}
            lignes={[
              { libelle: 'HASIRCI', valeur: 6_120_000, detail: '42 %' },
              { libelle: 'BELKA', valeur: 3_480_000, detail: '24 %' },
              { libelle: 'FILATURE DU NORD', valeur: 1_910_000, detail: '13 %' },
              { libelle: 'TANNERIE FÈS', valeur: 720_000, detail: '5 %' },
            ]}
          />
        </Carte>
        <Carte titre="Sparkline">
          <p>
            Couverture du PP Rouge : <Sparkline libelle="Couverture" valeurs={vague(30, 8)} couleur={rouge} />
          </p>
        </Carte>
      </div>
    </Page>
  )
}
