/**
 * L'état du montage d'un étage au téléphone : la saisie gardée (avec la version lue), ce qu'elle
 * change (largeur, bobines, poids, effet sur le stock sur les métiers, alertes 30 jours),
 * l'enregistrement confirmé (`confirme_effet_kg`), les conflits (version, effet changé).
 */
import { useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { useSaisieGardee } from '../../composants/atelier/saisieGardee'
import { api, ErreurApi, messageErreur } from '../../lib/api'
import { kgTelephone, nombre } from '../../lib/format'
import { useLecture } from '../../lib/requetes'
import {
  alertesMontage,
  bobinesDe,
  corpsEtage,
  effetDe,
  etageEnregistre,
  largeurDe,
  messageMontage,
  peser,
  poidsRetenu,
  signe,
  type FilSaisi,
  type SaisieEtage,
} from './calculMontage'
import type { MatiereMontage, MetierFiche, ResultatMontage } from './types'

/** Ce que dit un refus à l'enregistrement d'un étage. */
export function texteConflit(e: unknown, etage: number): string {
  if (e instanceof ErreurApi && e.code === 'conflit_version')
    return (
      `L’étage ${etage} a été modifié entre-temps sur un autre poste : rechargez pour repartir de sa ` +
      'dernière version, puis refaites la modification.'
    )
  return messageErreur(e)
}

/** « Étage 2 enregistré : 2 fil(s), 40 kg ; sur les métiers +40,0 kg. » + le texte unique. */
export function texteFait(
  r: ResultatMontage,
  etage: number,
  fils: readonly FilSaisi[],
  poids: (id: number) => number,
) {
  const kg = peser(r.metier, fils, poids)
  return (
    `Étage ${etage} enregistré : ${nombre(fils.length)} fil(s), ${kgTelephone(kg)} ; sur les métiers ` +
    `${signe(r.effet_kg)} kg. ${r.message}`
  )
}

export function useMontageEtage(m: MetierFiche, etage: number, matieres: MatiereMontage[] | undefined) {
  const client = useQueryClient()
  const metiers = useLecture<MetierFiche[]>('/metiers')
  const enregistre = etageEnregistre(m, etage)
  const [s, setS, oublier] = useSaisieGardee<SaisieEtage>(`montage:${m.id}:${etage}`, enregistre)
  const [confirmer, setConfirmer] = useState(false)
  const [fait, setFait] = useState('')
  const [conflit, setConflit] = useState('')
  const poids = (id: number) => poidsRetenu(m, matieres, id)
  const effet = effetDe({ avant: m, apres: m }, enregistre.fils, s.fils, poids)
  const totalAvant = (metiers.data ?? []).filter((x) => x.actif).reduce((t, x) => t + x.sur_les_metiers, 0)
  const sansMetres = s.fils.filter((f) => !(f.metres > 0))
  const poserFils = (fils: FilSaisi[]) => setS((avant) => ({ ...avant, fils }))
  const recharger = async () => {
    const frais = await api.get<MetierFiche>(`/metiers/${m.id}`)
    oublier()
    setS(etageEnregistre(frais, etage))
    setConflit('')
    setConfirmer(false)
    await client.invalidateQueries()
  }
  const enregistrer = async () => {
    setConflit('')
    try {
      const r = await api.put<ResultatMontage>(`/metiers/${m.id}/etages/${etage}`, corpsEtage(s, effet))
      oublier()
      setS(etageEnregistre(r.metier, etage))
      setConfirmer(false)
      setFait(texteFait(r, etage, s.fils, poids))
    } catch (e) {
      setConflit(texteConflit(e, etage))
      // L'effet a changé (poids pesé entre-temps) : la carte reste ouverte, l'effet relu.
      if (!(e instanceof ErreurApi && e.code === 'effet_change')) setConfirmer(false)
    } finally {
      await client.invalidateQueries()
    }
  }
  return {
    s,
    poserFils,
    enregistrer,
    recharger,
    annuler: () => setS(enregistre),
    confirmer,
    setConfirmer,
    fait,
    conflit,
    perimee: s.version < enregistre.version,
    modifie: JSON.stringify(s.fils) !== JSON.stringify(enregistre.fils),
    trop: m.laize > 0 && largeurDe(s.fils) > m.laize + 1e-6,
    sansMetres,
    bobines: s.fils.reduce((t, f) => t + bobinesDe(m, f), 0),
    poids: peser({ ...m, actif: true }, s.fils, poids),
    effet,
    message: messageMontage(m.actif, totalAvant, totalAvant + effet),
    alertes: alertesMontage({ avant: m, apres: m }, enregistre.fils, s.fils, matieres, poids),
  }
}

export type MontageEtage = ReturnType<typeof useMontageEtage>
