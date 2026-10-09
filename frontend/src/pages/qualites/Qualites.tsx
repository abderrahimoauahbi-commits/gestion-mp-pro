/**
 * « Qualités et recettes » (`/qualites?onglet=qualites|nomenclature`) : direction en écriture,
 * achats en lecture (coûts compris), alimentation en lecture sans coût ni prix. La fiche d'une
 * qualité s'ouvre en fenêtre par-dessus la liste à adresse stable (`/qualites/:id`,
 * `/qualites/nouvelle`) ; l'onglet de la liste est gardé dessous (`?liste=`) pendant que la fiche
 * a les siens (`?onglet=recette|plan|versions|historique`), et revient à la fermeture (P7-29).
 * L'ancienne adresse `?qualite=7` mène à `/qualites/7`.
 */
import { useCallback, useEffect } from 'react'
import { useLocation, useNavigate, useSearchParams } from 'react-router'

import { EnTete } from '../../composants/coque/EnTete'
import { Onglets } from '../../composants/mise-en-page/Onglets'
import { Page } from '../../composants/mise-en-page/Page'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { Bouton } from '../../composants/saisie/Bouton'
import { ExportExcel } from '../../composants/tableaux/ExportExcel'
import { avecParametre } from '../../lib/adresse'
import { useSession } from '../../lib/session'
import { useQualites } from './donnees'
import { FicheQualite } from './FicheQualite'
import { IndicateursQualites } from './IndicateursQualites'
import { NouvelleQualite } from './NouvelleQualite'
import { OngletNomenclature } from './OngletNomenclature'
import { OngletQualites } from './OngletQualites'

type OngletListe = 'qualites' | 'nomenclature'

/** La fiche ouverte par l'adresse : un identifiant, « nouvelle », ou rien. */
export function ficheDe(chemin: string): number | 'nouvelle' | null {
  const m = /^\/qualites\/(\d+|nouvelle)$/.exec(chemin)
  if (!m) return null
  return m[1] === 'nouvelle' ? 'nouvelle' : Number(m[1])
}

const lireOnglet = (v: string | null): OngletListe => (v === 'nomenclature' ? 'nomenclature' : 'qualites')

/** Ouvrir une fiche garde l'onglet de la liste dans `?liste=` ; la fermer le rend à `?onglet=`. */
function useNavigationQualites() {
  const navigate = useNavigate()
  const { search } = useLocation()
  const ouvrir = useCallback(
    (id: number | 'nouvelle', onglet?: string, remplacer = false) => {
      const p = new URLSearchParams(search)
      const liste = lireOnglet(p.get('onglet'))
      p.delete('onglet')
      if (liste !== 'qualites') p.set('liste', liste)
      if (onglet) p.set('onglet', onglet)
      navigate(`/qualites/${id}?${p.toString()}`.replace(/\?$/, ''), { replace: remplacer })
    },
    [navigate, search],
  )
  const fermer = useCallback(() => {
    const p = new URLSearchParams(search)
    const liste = p.get('liste')
    p.delete('liste')
    p.delete('onglet')
    if (liste) p.set('onglet', liste)
    navigate(`/qualites?${p.toString()}`.replace(/\?$/, ''))
  }, [navigate, search])
  return { ouvrir, fermer }
}

/** Le sous-titre de la page, selon le rôle. */
export function sousTitre(direction: boolean): string {
  const debut = 'Les qualités de tapis, leurs poids au m² et leurs recettes.'
  return direction
    ? `${debut} Le plan se saisit dans la page Production.`
    : `${debut} Lecture seule : la direction les modifie.`
}

export default function Qualites() {
  const { role } = useSession()
  const { pathname } = useLocation()
  const [params, setParams] = useSearchParams()
  const navigate = useNavigate()
  const direction = role === 'direction'
  const voitPrix = direction || role === 'achats'
  const fiche = ficheDe(pathname)
  const onglet = lireOnglet(fiche == null ? params.get('onglet') : params.get('liste'))
  const nav = useNavigationQualites()
  const qualites = useQualites()
  const ancienne = params.get('qualite')
  useEffect(() => {
    if (ancienne) navigate(`/qualites/${ancienne}`, { replace: true })
  }, [ancienne, navigate])
  const actions = (
    <>
      {voitPrix ? <ExportExcel route="/export/qualites" /> : null}
      {direction ? (
        <Bouton variante="principal" icone="plus" onClick={() => nav.ouvrir('nouvelle')}>
          Nouvelle qualité
        </Bouton>
      ) : null}
    </>
  )
  return (
    <Page titre="Qualités et recettes">
      <EnTete titre="Qualités et recettes" sous={sousTitre(direction)} actions={actions} />
      {qualites.data ? <IndicateursQualites qualites={qualites.data} voitPrix={voitPrix} /> : null}
      <Onglets<OngletListe>
        libelle="Onglets des qualités"
        actif={onglet}
        onChange={(o) =>
          setParams((p) => avecParametre(p, 'onglet', o === 'qualites' ? null : o), { replace: true })
        }
        onglets={[
          { cle: 'qualites', libelle: 'Qualités', compte: qualites.data?.length },
          { cle: 'nomenclature', libelle: 'Nomenclature' },
        ]}
      />
      {qualites.isError ? (
        <Erreur erreur={qualites.error} onReessayer={() => void qualites.refetch()} />
      ) : qualites.isPending ? (
        <Chargement quoi="les qualités" />
      ) : null}
      {qualites.data && onglet === 'qualites' ? (
        <OngletQualites qualites={qualites.data} voitPrix={voitPrix} onOuvrir={(id) => nav.ouvrir(id)} />
      ) : null}
      {onglet === 'nomenclature' ? (
        <OngletNomenclature voitPrix={voitPrix} onOuvrir={(id) => nav.ouvrir(id)} />
      ) : null}
      {fiche === 'nouvelle' && direction ? (
        <NouvelleQualite onFermer={nav.fermer} onCree={(id) => nav.ouvrir(id, 'recette', true)} />
      ) : null}
      {typeof fiche === 'number' ? (
        <FicheQualite key={fiche} id={fiche} role={role} onFermer={nav.fermer} />
      ) : null}
    </Page>
  )
}
