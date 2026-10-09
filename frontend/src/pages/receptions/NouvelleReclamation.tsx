/**
 * Nouvelle réclamation / Réclamer au fournisseur (`/reclamations/nouvelle?reception=ID&ligne=ID`,
 * ECRANS-PRO 4.23) : sur une réception validée (la ligne en cause est envoyée par son id : la
 * référence reste même sans lot, anom. 4.17), ou sans réception (un retard, une facture fausse).
 * Elle reçoit son numéro tout de suite ; les photos et documents se joignent ensuite.
 */
import { useState } from 'react'

import { Fenetre, useFermerFenetre } from '../../composants/mise-en-page/Fenetre'
import { Grille } from '../../composants/mise-en-page/Grille'
import { Chargement } from '../../composants/retour/Chargement'
import { Note } from '../../composants/retour/Note'
import { Bouton } from '../../composants/saisie/Bouton'
import { Champ } from '../../composants/saisie/Champ'
import { DateChamp } from '../../composants/saisie/DateChamp'
import { Nombre } from '../../composants/saisie/Nombre'
import { Selecteur } from '../../composants/saisie/Selecteur'
import { Zone } from '../../composants/saisie/Zone'
import { api } from '../../lib/api'
import { date, kg } from '../../lib/format'
import { aujourdhui } from '../../lib/heure'
import { useEcriture } from '../../lib/requetes'
import { statut } from '../../lib/statuts'
import styles from '../plan-achat/achats.module.css'
import { useDevises } from '../plan-achat/donnees'
import { useFournisseursActifs, useMotifs, useReception } from './donnees'
import type { LigneReception, ReceptionFiche, ReclamationCreation, ReclamationFiche } from './types'

interface Forme {
  fournisseurId: number | null
  ligneId: number | null
  motif: string
  ouverteLe: string
  quantite: number | null
  montant: number | null
  devise: string
  description: string
}

/** La ligne proposée d'abord : celle de l'adresse, sinon la première non conforme. */
function ligneDeDepart(r: ReceptionFiche | null, ligne: number | null): LigneReception | null {
  if (!r) return null
  return r.lignes.find((l) => l.id === ligne) ?? r.lignes.find((l) => l.qualite !== 'conforme') ?? null
}

function formeDeDepart(r: ReceptionFiche | null, ligne: number | null): Forme {
  const l = ligneDeDepart(r, ligne)
  return {
    fournisseurId: r?.fournisseur_id ?? null,
    ligneId: l?.id ?? null,
    motif: l && l.qualite !== 'conforme' ? 'qualite' : '',
    ouverteLe: aujourdhui(),
    quantite: l?.quantite_pesee ?? null,
    montant: null,
    devise: r?.devise ?? '',
    description: l?.observations ?? '',
  }
}

export function corpsReclamation(f: Forme, r: ReceptionFiche | null): ReclamationCreation {
  const l = r?.lignes.find((x) => x.id === f.ligneId)
  return {
    fournisseur_id: f.fournisseurId ?? 0,
    reception_id: r?.id ?? null,
    reception_ligne_id: l?.id ?? null,
    lot_id: l?.lot_id ?? null,
    motif: f.motif,
    description: f.description.trim(),
    quantite: f.quantite ?? 0,
    montant_demande: f.montant ?? 0,
    devise: f.devise,
    ouverte_le: f.ouverteLe || null,
  }
}

type Maj = (m: Partial<Forme>) => void

/** Ce qui est en cause : une ligne de la réception (ou toute la réception), ou le fournisseur sans réception. */
function EnCause({ r, f, maj }: { r: ReceptionFiche | null; f: Forme; maj: Maj }) {
  const fournisseurs = useFournisseursActifs()
  if (!r)
    return (
      <Champ libelle="Fournisseur">
        <Selecteur<number>
          valeur={f.fournisseurId}
          options={(fournisseurs.data ?? []).map((x) => ({ id: x.id, titre: x.nom, sous: x.pays }))}
          onChange={(id) =>
            maj({
              fournisseurId: id,
              devise: fournisseurs.data?.find((x) => x.id === id)?.devise ?? f.devise,
            })
          }
        />
      </Champ>
    )
  const options = r.lignes.map((x) => ({
    id: x.id,
    titre: x.reference,
    sous: [x.lot_numero ? `lot ${x.lot_numero}` : '', statut('qualite_reception', x.qualite).libelle]
      .filter(Boolean)
      .join(' · '),
  }))
  return (
    <Champ libelle="Ligne en cause">
      <Selecteur<number>
        valeur={f.ligneId}
        placeholder="— toute la réception —"
        options={options}
        onChange={(id) => {
          const x = r.lignes.find((y) => y.id === id)
          maj({
            ligneId: id,
            quantite: x?.quantite_pesee ?? null,
            description: f.description || x?.observations || '',
            motif: f.motif || (x && x.qualite !== 'conforme' ? 'qualite' : ''),
          })
        }}
      />
    </Champ>
  )
}

function Champs({ r, f, maj }: { r: ReceptionFiche | null; f: Forme; maj: Maj }) {
  const motifs = useMotifs()
  const devises = useDevises()
  const l = r?.lignes.find((x) => x.id === f.ligneId)
  return (
    <Grille colonnes={2}>
      <EnCause r={r} f={f} maj={maj} />
      <Champ libelle="Motif">
        <Selecteur<string>
          valeur={f.motif || null}
          options={(motifs.data?.reclamation_motifs ?? []).map((m) => ({ id: m.code, titre: m.libelle }))}
          onChange={(m) => maj({ motif: m ?? '' })}
        />
      </Champ>
      <Champ libelle="Ouverte le">
        <DateChamp
          valeur={f.ouverteLe}
          onChange={(ouverteLe) => maj({ ouverteLe })}
          min={r?.date}
          raisonMin={r ? 'une réclamation ne précède pas la réception qu’elle vise' : undefined}
        />
      </Champ>
      <Champ libelle="Quantité en cause (kg)" aide={l ? `pesé : ${kg(l.quantite_pesee)}` : undefined}>
        <Nombre
          valeur={f.quantite}
          onChange={(quantite) => maj({ quantite })}
          min={0}
          decimales={3}
          unite="kg"
        />
      </Champ>
      <Champ libelle="Montant demandé" aide="avoir ou remise attendue ; vide si on demande un remplacement">
        <Nombre
          valeur={f.montant}
          onChange={(montant) => maj({ montant })}
          min={0}
          decimales={2}
          unite={f.devise || undefined}
        />
      </Champ>
      <Champ libelle="Devise">
        <Selecteur<string>
          valeur={f.devise || null}
          effacable={false}
          options={(devises.data ?? [])
            .filter((d) => d.actif)
            .map((d) => ({ id: d.code, titre: d.code, sous: d.nom }))}
          onChange={(d) => maj({ devise: d ?? '' })}
        />
      </Champ>
    </Grille>
  )
}

function Formulaire({
  r,
  ligne,
  onFermer,
  onCree,
}: {
  r: ReceptionFiche | null
  ligne: number | null
  onFermer: () => void
  onCree: (id: number) => void
}) {
  const [f, setF] = useState(() => formeDeDepart(r, ligne))
  const [initiale] = useState(f)
  const maj: Maj = (m) => setF((x) => ({ ...x, ...m }))
  const ouvrir = useEcriture(() => api.post<ReclamationFiche>('/reclamations', corpsReclamation(f, r)))
  const manque = [...(f.fournisseurId ? [] : ['le fournisseur']), ...(f.motif ? [] : ['le motif'])]
  return (
    <Fenetre
      titre={r ? `Réclamer au fournisseur — ${r.fournisseur}` : 'Nouvelle réclamation'}
      taille="large"
      sale={JSON.stringify(f) !== JSON.stringify(initiale)}
      onFermer={onFermer}
      pied={<Pied manque={manque} onOuvrir={async () => onCree((await ouvrir.mutateAsync()).id)} />}
    >
      {r ? (
        <Note>
          Réception {r.numero ?? 'Brouillon'} du {date(r.date)} · BL {r.numero_bl || '—'}. La réclamation
          reçoit son numéro tout de suite ; joignez ensuite les photos et les documents.
        </Note>
      ) : null}
      <Champs r={r} f={f} maj={maj} />
      <Champ libelle="Ce qui a été constaté" large>
        <Zone
          valeur={f.description}
          onChange={(description) => maj({ description })}
          max={4000}
          placeholder="ex. 12 bobines tachées d’huile sur la palette 4, photos jointes"
        />
      </Champ>
    </Fenetre>
  )
}

function Pied({ manque, onOuvrir }: { manque: string[]; onOuvrir: () => Promise<void> }) {
  const fermer = useFermerFenetre()
  return (
    <div className={styles.pied}>
      <span className={styles.pousse} />
      <Bouton onClick={fermer}>Annuler</Bouton>
      <Bouton
        variante="principal"
        attente="Ouverture…"
        manque={manque.length ? manque : undefined}
        onClick={onOuvrir}
      >
        Ouvrir la réclamation
      </Bouton>
    </div>
  )
}

export function NouvelleReclamation({
  reception,
  ligne,
  onFermer,
  onCree,
}: {
  reception: number | null
  ligne: number | null
  onFermer: () => void
  onCree: (id: number) => void
}) {
  const lu = useReception(reception)
  if (reception && !lu.data)
    return (
      <Fenetre titre="Réclamer au fournisseur" onFermer={onFermer}>
        <Chargement quoi="la réception" />
      </Fenetre>
    )
  return <Formulaire r={lu.data ?? null} ligne={ligne} onFermer={onFermer} onCree={onCree} />
}
