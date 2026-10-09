/**
 * Page provisoire de `/analyse` (lot F8) : l'onglet « Coût de revient » du lot F5, les autres
 * « à venir » (voir `OngletsHotes.tsx`).
 */
import { PageHote } from './OngletsHotes'
import AnalyseRevient from './revient/AnalyseRevient'

const CONTENUS = { revient: AnalyseRevient }

export default function PageAnalyse() {
  return <PageHote contenus={CONTENUS} />
}
