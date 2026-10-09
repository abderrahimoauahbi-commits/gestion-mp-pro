/**
 * Les boutons d'enregistrement du volet ouvert de la fiche commande (Lignes, Prix, Expédition),
 * posés au pied de la fenêtre pour rester visibles. Un conflit de version (409) est rendu à la
 * fiche, qui l'affiche avec « Recharger » ; les autres refus sont dits tels quels.
 */
import { dire } from '../../composants/retour/Messages'
import { Bouton } from '../../composants/saisie/Bouton'
import { Confirmer } from '../../composants/saisie/Confirmer'
import { api } from '../../lib/api'
import { useEcriture } from '../../lib/requetes'
import { messageConflit } from '../catalogue/Conflit'
import { corpsExpedition, type FormeExpedition } from './VoletExpedition'
import { corpsLignes, manquesLignes, type FormeLignes } from './formeLignes'
import { apresModification, apresPrix, apresSuivi } from './messages'
import {
  corpsPrix,
  questionPrix,
  reprendreCatalogue,
  saisis,
  changeantAuCatalogue,
  type FormePrix,
} from './VoletPrix'
import { raison, type CommandeFiche } from './types'
import type { FormeFiche } from './useFormeFiche'

export interface Formes {
  lignes: FormeFiche<FormeLignes>
  prix: FormeFiche<FormePrix>
  expedition: FormeFiche<FormeExpedition>
}

/** Écrit, repart de la fiche rendue ; un 409 de version est rendu à `onConflit` au lieu d'un toast. */
function useSauver(onConflit: (m: string) => void) {
  const m = useEcriture((envoi: () => Promise<CommandeFiche>) => envoi())
  return async (
    envoi: () => Promise<CommandeFiche>,
    apres: (r: CommandeFiche) => void,
    message: (r: CommandeFiche) => string,
  ) => {
    try {
      const r = await m.mutateAsync(envoi)
      apres(r)
      dire(message(r))
    } catch (e) {
      const conflit = messageConflit(e)
      if (!conflit) throw e
      onConflit(conflit)
    }
  }
}

const RIEN = 'Rien n’a changé.'

type Sauver = ReturnType<typeof useSauver>

function SauverLignes({ c, f, sauver }: { c: CommandeFiche; f: Formes; sauver: Sauver }) {
  const fl = f.lignes
  const refus = raison(c, 'modifier')
  return (
    <>
      <Bouton grise={fl.sale ? undefined : RIEN} onClick={fl.reprendre}>
        Annuler les changements
      </Bouton>
      <Bouton
        variante="principal"
        attente="Enregistrement…"
        grise={fl.sale ? undefined : RIEN}
        manque={manquesLignes(fl.forme)}
        blocages={refus ? [refus] : undefined}
        onClick={() =>
          sauver(
            () =>
              api.put<CommandeFiche>(`/commandes/${c.id}`, corpsLignes(fl.forme, fl.initiale, fl.version)),
            (r) => fl.repartir(r),
            (r) => apresModification(c, r),
          )
        }
      >
        Enregistrer
      </Bouton>
    </>
  )
}

function SauverPrix({ c, f, sauver }: { c: CommandeFiche; f: Formes; sauver: Sauver }) {
  const fp = f.prix
  const n = saisis(c, fp.forme).length
  const memeDevise = c.lignes.some((l) => l.devise_catalogue === c.devise && l.prix_catalogue > 0)
  return (
    <>
      <Bouton
        grise={memeDevise ? undefined : 'Le catalogue n’est pas dans la devise du bon.'}
        titre="Remplit les prix vides avec ceux du catalogue — à vérifier avant de confirmer"
        onClick={() => fp.poser(reprendreCatalogue(c, fp.forme))}
      >
        Reprendre les prix du catalogue
      </Bouton>
      <Confirmer
        variante="principal"
        manque={n ? undefined : ['au moins un prix']}
        titre="Enregistre les prix comme confirmés par le fournisseur"
        question={questionPrix(c, fp.forme)}
        oui="Oui, confirmer"
        onOui={() =>
          sauver(
            () => api.post<CommandeFiche>(`/commandes/${c.id}/prix`, corpsPrix(c, fp.forme, fp.version)),
            (r) => fp.repartir(r),
            (r) =>
              apresPrix(
                n,
                fp.forme.catalogue ? changeantAuCatalogue(c, fp.forme).length : 0,
                r.prix_a_confirmer,
              ),
          )
        }
      >
        Confirmer ces prix
      </Confirmer>
    </>
  )
}

function SauverExpedition({ c, f, sauver }: { c: CommandeFiche; f: Formes; sauver: Sauver }) {
  const fe = f.expedition
  return (
    <>
      <Bouton grise={fe.sale ? undefined : RIEN} onClick={fe.reprendre}>
        Annuler les changements
      </Bouton>
      <Bouton
        variante="principal"
        attente="Enregistrement…"
        grise={fe.sale ? undefined : RIEN}
        onClick={() =>
          sauver(
            () =>
              api.put<CommandeFiche>(
                `/commandes/${c.id}/expedition`,
                corpsExpedition(fe.forme, fe.initiale, fe.version),
              ),
            (r) => fe.repartir(r),
            (r) => apresSuivi(c.expedition.eta, r.expedition.eta),
          )
        }
      >
        Enregistrer le suivi
      </Bouton>
    </>
  )
}

export function SauverVolet({
  volet,
  c,
  f,
  onConflit,
}: {
  volet: string
  c: CommandeFiche
  f: Formes
  onConflit: (m: string) => void
}) {
  const sauver = useSauver(onConflit)
  if (volet === 'lignes' && c.modifiable) return <SauverLignes c={c} f={f} sauver={sauver} />
  if (volet === 'prix' && c.parti && !raison(c, 'prix')) return <SauverPrix c={c} f={f} sauver={sauver} />
  if (volet === 'expedition' && c.parti && !raison(c, 'expedition'))
    return <SauverExpedition c={c} f={f} sauver={sauver} />
  return null
}
