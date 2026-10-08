/**
 * Des kilos, et pour un cuir, des franges, un ruban leurs mètres **à titre indicatif** :
 * « 14,3 kg ≈ 1 020 ml » (le stock est toujours en kilos). Au téléphone, les décimales du
 * téléphone (« 445 kg », « 52,4 kg », « 2,49 kg »).
 */
import { kgEtMetres } from '../../lib/format'

export function KgEtMetres({
  kg,
  kgParMl,
  telephone,
}: {
  kg: number | null | undefined
  kgParMl?: number | null
  telephone?: boolean
}) {
  return <span className="nombre">{kgEtMetres(kg, kgParMl, telephone)}</span>
}
