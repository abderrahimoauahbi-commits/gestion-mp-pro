/**
 * Les écritures sur un dossier (routes 190–204) : chacune envoie la `version` lue (celle du dossier,
 * ou celle du frais pour modifier et retirer un frais), rend la fiche relue, et la page relit tout
 * (invalidation globale de `useEcriture`). « Enregistré à HH:MM » (heure du serveur) s'affiche
 * quatre secondes après un champ enregistré en le quittant.
 */
import { useCallback, useEffect, useState } from 'react'

import { api } from '../../lib/api'
import { heureServeur } from '../../lib/heure'
import { useEcriture } from '../../lib/requetes'
import type { DossierFiche, FraisDossier } from './types'

/** Le corps d'un frais (route 199–200) : tous les champs, `version` comprise. */
export interface FraisCorps {
  poste_id: number
  montant: number
  ligne_id: number | null
  piece: string
  prestataire: string
  date_piece: string | null
  echeance: string | null
  commentaire: string
}

/** Le corps d'un frais existant, à modifier champ par champ. */
export const corpsDuFrais = (f: FraisDossier): FraisCorps => ({
  poste_id: f.poste_id,
  montant: f.montant,
  ligne_id: f.ligne_id,
  piece: f.piece,
  prestataire: f.prestataire,
  date_piece: f.date_piece,
  echeance: f.echeance,
  commentaire: f.commentaire,
})

/** Le corps de l'en-tête (route 191, fiche entière). */
export interface EnTeteCorps {
  libelle: string
  banque: string
  commentaire: string
  date_arrivee: string | null
}

/** « Enregistré à 14:05 », quatre secondes. */
export function useEnregistre() {
  const [a, setA] = useState<string | null>(null)
  useEffect(() => {
    if (!a) return
    const t = setTimeout(() => setA(null), 4000)
    return () => clearTimeout(t)
  }, [a])
  const noter = useCallback(() => setA(heureServeur().slice(0, 5)), [])
  return { a, noter }
}

export function useGestesDossier(fiche: DossierFiche) {
  const base = `/dossiers/${fiche.id}`
  const ecrire = useEcriture((faire: () => Promise<DossierFiche>) => faire())
  const avec = (corps: object) => ({ version: fiche.version, ...corps })
  const poster = (geste: string, corps: object = {}) =>
    ecrire.mutateAsync(() => api.post<DossierFiche>(`${base}/${geste}`, avec(corps)))
  return {
    enCours: ecrire.isPending,
    enTete: (corps: EnTeteCorps) => ecrire.mutateAsync(() => api.put<DossierFiche>(base, avec(corps))),
    rattacher: (factureId: number) => poster('rattacher', { facture_id: factureId }),
    saisir: (corps: object) => poster('lignes', corps),
    ligne: (ligneId: number, corps: { cours?: number | null; commentaire?: string }) =>
      ecrire.mutateAsync(() => api.put<DossierFiche>(`${base}/lignes/${ligneId}`, avec(corps))),
    retirerLigne: (ligneId: number) =>
      ecrire.mutateAsync(() =>
        api.supprimer<DossierFiche>(`${base}/lignes/${ligneId}?version=${fiche.version}`),
      ),
    cours: (devise: string, cours: number) =>
      ecrire.mutateAsync(() => api.put<DossierFiche>(`${base}/cours`, avec({ devise, cours }))),
    coursDesBons: () => poster('cours-des-bons'),
    detacher: (receptionId: number) => poster('detacher', { reception_id: receptionId }),
    ajouterFrais: (corps: FraisCorps) => poster('frais', corps),
    modifierFrais: (f: FraisDossier, corps: FraisCorps) =>
      ecrire.mutateAsync(() =>
        api.put<DossierFiche>(`${base}/frais/${f.id}`, { ...corps, version: f.version }),
      ),
    retirerFrais: (f: FraisDossier) =>
      ecrire.mutateAsync(() => api.supprimer<DossierFiche>(`${base}/frais/${f.id}?version=${f.version}`)),
    cloturer: (alertesLues: boolean) => poster('cloturer', { alertes_lues: alertesLues }),
    rouvrir: (motif: string) => poster('rouvrir', { motif }),
    annuler: (motif: string) => poster('annuler', { motif }),
  }
}

export type GestesDossier = ReturnType<typeof useGestesDossier>
