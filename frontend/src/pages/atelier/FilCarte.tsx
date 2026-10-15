/**
 * La carte d'un fil à l'étape « Lots à prendre » : ce que les recettes en prévoient, ce qu'on en
 * prend lot par lot (kg, bobines, palettes : `Quantite` dit la conversion et l'arrondi), l'écart,
 * le manque, les lots qui débordent, un autre lot à prendre.
 */
import { Badge } from '../../composants/retour/Badge'
import { Note } from '../../composants/retour/Note'
import { Bouton } from '../../composants/saisie/Bouton'
import { Quantite } from '../../composants/saisie/Quantite'
import { Selecteur } from '../../composants/saisie/Selecteur'
import { kgEtMetres, metres, nombreSigne } from '../../lib/format'
import { conditionnement, depasse, ecartLisible, kgDe, priseDe, type Fil, type Prise } from '../../lib/ordre'
import { bobinesApprochees, contenance } from '../../lib/unites'
import { Fiche, NoteAtelier } from './briques'
import styles from './atelier.module.css'
import type { SaisieSortie } from './useSaisieSortie'

const q = (kg: number, kgParMl: number) => kgEtMetres(kg, kgParMl, true)

/** L'écart au prévu : « conforme », ou « +1,2 kg (+3,4 %) » avec son ton ; « — » sans prévu. */
export function EcartFil({
  ecart,
  prevu,
  kgParMl = 0,
}: {
  ecart: number | null
  prevu: number
  kgParMl?: number
}) {
  const e = ecartLisible(ecart, prevu)
  if (!e || ecart == null) return <span>—</span>
  if (e.conforme) return <Badge ton="ok">conforme</Badge>
  const signe = ecart > 0 ? '+' : '−'
  return (
    <Badge
      ton={e.ton}
    >{`${signe}${q(Math.abs(ecart), kgParMl)} (${nombreSigne(e.relatif * 100, 1)} %)`}</Badge>
  )
}

/** « ATL-01 : 12,5 kg · ATL-02 : 3 kg » quand un fil sert plusieurs qualités. */
export function parQualite(f: Fil): string {
  return (f.besoin?.par_qualite ?? []).map((x) => `${x.qualite} : ${q(x.kg, f.kg_par_ml)}`).join(' · ')
}

function LignePrise({ s, p }: { s: SaisieSortie; p: Prise }) {
  const c = conditionnement(p)
  const dispo = s.dispo(p)
  const changer = (m: Partial<Prise>) =>
    s.poser({ prises: s.e.prises.map((x) => (x.cle === p.cle ? { ...x, ...m } : x)) })
  const indicatif = p.unite === 'kg' && p.kg_par_ml ? metres(kgDe(p), p.kg_par_ml) : ''
  return (
    <div className={styles.prise}>
      <div className={styles.ligne}>
        <strong>Lot {p.lot}</strong>
        <span className={styles.note}>
          {dispo >= 0 ? `dispo ${q(dispo, p.kg_par_ml)} ${bobinesApprochees(dispo, c)}` : ''}
        </span>
      </div>
      <Quantite
        tactile
        libelle={`Quantité du lot ${p.lot}`}
        kg={p.kg}
        unite={p.unite}
        poidsBobine={p.poids_bobine}
        bobinesPalette={p.bobines_palette}
        kgParMl={p.kg_par_ml}
        onChange={(kg) => changer({ kg })}
        onUnite={(unite) => changer({ unite })}
      />
      {indicatif ? <span className={styles.note}>{indicatif}, à titre indicatif</span> : null}
      {depasse(p, dispo) ? <Note ton="critique">Plus que ce que porte le lot.</Note> : null}
      {contenance(c, p.unite) == null ? (
        <Note ton="critique">Le poids de bobine n’est pas connu : saisir en kg.</Note>
      ) : null}
      <div className={styles.adroite}>
        <Bouton
          taille="atelier"
          variante="fantome"
          onClick={() => s.poser({ prises: s.e.prises.filter((x) => x.cle !== p.cle) })}
        >
          Retirer ce lot
        </Bouton>
      </div>
    </div>
  )
}

function AutreLot({ s, f }: { s: SaisieSortie; f: Fil }) {
  const autres = (f.besoin?.disponibles ?? []).filter((d) => !f.prises.some((p) => p.lot_id === d.lot_id))
  const besoin = f.besoin
  if (!autres.length || !besoin) return null
  return (
    <Selecteur
      libelle={`Prendre aussi un autre lot de ${f.reference}`}
      placeholder="+ Prendre aussi un autre lot…"
      valeur={null}
      options={autres.map((d) => ({
        id: d.lot_id,
        titre: d.lot,
        sous: `${q(d.disponible, f.kg_par_ml)}${d.fond_de_lot ? ' · fond de lot' : ''}`,
      }))}
      onChange={(id) => {
        const d = autres.find((x) => x.lot_id === id)
        if (d) s.poser({ prises: [...s.e.prises, priseDe(besoin, d)] })
      }}
    />
  )
}

export function FilCarte({ s, f }: { s: SaisieSortie; f: Fil }) {
  const b = f.besoin
  const manque = b && b.manque > 0.05
  const detail = parQualite(f)
  return (
    <Fiche titre={f.reference} ton={manque ? 'alerte' : undefined} libelle={f.reference}>
      {b ? (
        <div className={styles.ligne}>
          <span className={styles.note}>
            {b.role} · prévu {q(b.prevu, f.kg_par_ml)}
            {b.par_qualite.length > 1 ? (
              <>
                <br />
                {detail}
              </>
            ) : null}
          </span>
          <span className={styles.valeur}>
            pris {q(f.sorti, f.kg_par_ml)}
            <br />
            <EcartFil ecart={f.ecart} prevu={b.prevu} kgParMl={f.kg_par_ml} />
          </span>
        </div>
      ) : (
        <NoteAtelier>hors recette · pris {q(f.sorti, f.kg_par_ml)}</NoteAtelier>
      )}
      {manque ? (
        <Note ton="critique">
          Il manque {q(b.manque, f.kg_par_ml)} dans ce magasin (la quarantaine ne compte pas).
        </Note>
      ) : null}
      {f.prises.map((p) => (
        <LignePrise key={p.cle} s={s} p={p} />
      ))}
      <AutreLot s={s} f={f} />
    </Fiche>
  )
}
