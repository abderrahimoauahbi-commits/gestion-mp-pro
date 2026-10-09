/**
 * Page provisoire de `/reglages` (lot F8) : les onglets « Postes de frais » et « Codes douaniers »
 * du lot F5, les autres « à venir » (voir `OngletsHotes.tsx`).
 */
import { PageHote } from './OngletsHotes'
import { CodesDouaniers } from './reglages/CodesDouaniers'
import { PostesFrais } from './reglages/PostesFrais'

const CONTENUS = { postes: PostesFrais, codes: CodesDouaniers }

export default function PageReglages() {
  return <PageHote contenus={CONTENUS} />
}
