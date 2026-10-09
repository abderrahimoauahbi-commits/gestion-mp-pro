/**
 * « 2 · Les matières qui sortent » de la saisie d'un ordre : une matière par groupe de lignes (ce
 * que les recettes en demandent, perte comprise), un lot par ligne avec ce qu'il porte **à la date
 * de l'ordre**, la quantité en kilos, bobines ou palettes (l'arrondi est dit), l'écart à la recette.
 * Un lot qui ne porte pas ce qu'on lui demande est en rouge, et dit pourquoi.
 */
import { Quantite } from '../../composants/saisie/Quantite'
import { Cadre } from '../../composants/tableaux/Cadre'
import { kg, kgEtMetres, nombre, nombreSigne, VIDE } from '../../lib/format'
import styles from '../stock/stock.module.css'
import { EcartRecette, ecartRelatif } from './ecart'
import type { Fil, Prise } from './ordre'
import type { SaisieOrdre } from './useSaisieOrdre'

function AutreLot({ f, s }: { f: Fil; s: SaisieOrdre }) {
  const autres = (f.besoin?.disponibles ?? []).filter((d) => !f.prises.some((p) => p.lot_id === d.lot_id))
  if (!f.besoin || !autres.length) return null
  return (
    <select
      aria-label={`Un autre lot de ${f.reference}`}
      className={styles.selecteur}
      value=""
      onChange={(e) => {
        const d = autres.find((x) => x.lot_id === Number(e.target.value))
        if (d && f.besoin)
          s.ajouter({
            matiere_id: f.matiere_id,
            reference: f.reference,
            designation: f.designation,
            kg_par_ml: f.kg_par_ml,
            poids_bobine: d.poids_bobine || f.besoin.poids_bobine,
            bobines_palette: f.besoin.bobines_palette,
            lot_id: d.lot_id,
            lot: d.lot,
            kg: null,
            unite: 'kg',
          })
      }}
    >
      <option value="">+ un autre lot…</option>
      {autres.map((d) => (
        <option key={d.lot_id} value={d.lot_id}>
          {d.lot} — {kg(d.disponible)}
        </option>
      ))}
    </select>
  )
}

function LignePrise({ p, s, dispo }: { p: Prise; s: SaisieOrdre; dispo: number | undefined }) {
  const trop = dispo != null && (p.kg ?? 0) > dispo + 0.0005
  return (
    <>
      <td className={styles.mono}>{p.lot}</td>
      <td className={styles.droite}>{dispo == null ? '…' : kgEtMetres(dispo, p.kg_par_ml)}</td>
      <td>
        <Quantite
          kg={p.kg}
          onChange={(v) => s.changerKg(p.cle, v)}
          unite={p.unite}
          onUnite={(u) => s.changerUnite(p.cle, u)}
          libelle={`Quantité du lot ${p.lot}`}
          poidsBobine={p.poids_bobine}
          bobinesPalette={p.bobines_palette}
          kgParMl={p.kg_par_ml}
          borne={dispo}
        />
        {trop ? <span className={styles.alerte}>plus que le lot</span> : null}
      </td>
    </>
  )
}

/** La matière et son prévu, sur toutes ses lignes. */
function TeteFil({ f, s, n }: { f: Fil; s: SaisieOrdre; n: number }) {
  const parQualite = f.besoin?.par_qualite ?? []
  return (
    <>
      <td rowSpan={n} title={f.designation}>
        <strong>{f.reference}</strong>
        <span className={styles.dessous}>{f.besoin ? f.besoin.role : 'hors recette'}</span>
        <AutreLot f={f} s={s} />
      </td>
      <td
        rowSpan={n}
        className={styles.droite}
        title={parQualite.map((q) => `${q.qualite} : ${kg(q.kg)}`).join(' · ')}
      >
        {f.besoin ? nombre(f.besoin.prevu, 1) : VIDE}
        {parQualite.length > 1 ? <span className={styles.dessous}>{parQualite.length} qualités</span> : null}
      </td>
    </>
  )
}

function EcartFil({ f, n }: { f: Fil; n: number }) {
  return (
    <td rowSpan={n} className={styles.droite}>
      {f.besoin ? (
        <>
          <EcartRecette relatif={ecartRelatif(f.sorti, f.besoin.prevu)} />
          <span className={styles.dessous}>{nombreSigne(f.ecart, 1)} kg</span>
        </>
      ) : null}
    </td>
  )
}

function LignesFil({ f, s }: { f: Fil; s: SaisieOrdre }) {
  const n = Math.max(1, f.prises.length)
  if (!f.prises.length) {
    const manque = (f.besoin?.manque ?? 0) > 0.05
    return (
      <tr className={manque ? styles.ligneAlerte : undefined}>
        <TeteFil f={f} s={s} n={n} />
        <td colSpan={3} className={styles.note}>
          aucun lot pris{manque ? ' — rien dans ce magasin' : ''}
        </td>
        <EcartFil f={f} n={n} />
        <td />
      </tr>
    )
  }
  return (
    <>
      {f.prises.map((p, i) => {
        const dispo = s.dispo ? (s.dispo.get(p.lot_id) ?? 0) : undefined
        const trop = dispo != null && (p.kg ?? 0) > dispo + 0.0005
        return (
          <tr key={p.cle} className={trop ? styles.ligneAlerte : undefined}>
            {i === 0 ? <TeteFil f={f} s={s} n={n} /> : null}
            <LignePrise p={p} s={s} dispo={dispo} />
            {i === 0 ? <EcartFil f={f} n={n} /> : null}
            <td>
              <button
                type="button"
                className={styles.lien}
                title="Ne pas prendre ce lot"
                onClick={() => s.retirer(p.cle)}
              >
                retirer
              </button>
            </td>
          </tr>
        )
      })}
    </>
  )
}

export function LignesSaisie({ s }: { s: SaisieOrdre }) {
  const totalPrevu = s.besoins.reduce((t, b) => t + b.prevu, 0)
  const totalSorti = s.fils.reduce((t, f) => t + f.sorti, 0)
  return (
    <Cadre hauteur="fenetre">
      <table className={styles.tableSimple} aria-label="Les matières qui sortent">
        <thead>
          <tr>
            <th>Référence</th>
            <th className={styles.droite}>Prévu par la recette (kg)</th>
            <th>Lot</th>
            <th className={styles.droite}>Dans ce lot</th>
            <th>Quantité</th>
            <th className={styles.droite}>Écart</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {s.fils.map((f) => (
            <LignesFil key={f.matiere_id} f={f} s={s} />
          ))}
          {!s.fils.length ? (
            <tr>
              <td colSpan={7} className={styles.note}>
                {s.horsRecette
                  ? 'Ajouter une matière ci-dessous.'
                  : 'Choisir ce qu’on tisse puis « Proposer les matières à sortir » — ou ajouter une matière à la main.'}
              </td>
            </tr>
          ) : null}
        </tbody>
        {s.fils.length ? (
          <tfoot>
            <tr>
              <td>Total</td>
              <td className={styles.droite}>{totalPrevu ? nombre(totalPrevu, 1) : VIDE}</td>
              <td colSpan={2} />
              <td>{kg(totalSorti)}</td>
              <td className={styles.droite}>
                {totalPrevu ? <EcartRecette relatif={ecartRelatif(totalSorti, totalPrevu)} /> : VIDE}
              </td>
              <td />
            </tr>
          </tfoot>
        ) : null}
      </table>
    </Cadre>
  )
}
