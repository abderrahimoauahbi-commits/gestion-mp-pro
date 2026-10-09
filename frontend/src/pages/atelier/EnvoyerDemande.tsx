/**
 * Envoyer aux machines, étape 1 « la demande » : date, magasin, métier, qualités et m² (ou un
 * ordre hors recette), observations. Ce qui manque est écrit sous le bouton grisé (an. 9) ;
 * changer de magasin quand des lots sont choisis le demande (les lots s'effacent).
 */
import { useEffect, useState } from 'react'

import { BandeauBlocages } from '../../composants/atelier/BandeauBlocages'
import { Compteur } from '../../composants/atelier/Compteur'
import { EcranAtelier } from '../../composants/atelier/EcranAtelier'
import { SegmentsTactiles } from '../../composants/atelier/SegmentsTactiles'
import { Note } from '../../composants/retour/Note'
import { Bouton } from '../../composants/saisie/Bouton'
import { Champ } from '../../composants/saisie/Champ'
import { DateChamp } from '../../composants/saisie/DateChamp'
import { Saisie } from '../../composants/saisie/Saisie'
import { Selecteur } from '../../composants/saisie/Selecteur'
import { nombre } from '../../lib/format'
import { useLecture } from '../../lib/requetes'
import { enHaut, Fiche, NoteAtelier } from './briques'
import { magasinsCourants, nomMetier, useBornesDate, useMagasins, useMetiers } from './commun'
import { useEmpechements } from './empechements'
import styles from './atelier.module.css'
import { manqueDemande } from './sortie'
import type { QualiteResume } from './types'
import type { SaisieSortie } from './useSaisieSortie'

function ChoixMagasin({ s }: { s: SaisieSortie }) {
  const magasins = useMagasins()
  const [demande, setDemande] = useState<number | null>(null)
  const courants = magasinsCourants(magasins.data)
  if (courants.length <= 1) return null
  const choisir = (id: number | null) => {
    if (id == null || id === s.magasin) return
    if (s.e.prises.length) setDemande(id)
    else s.changerDemande({ magasin: id })
  }
  const options = courants.map((m) => ({ id: m.id, titre: m.code, sous: m.nom }))
  return (
    <Champ
      groupe
      libelle="Magasin d’où sort la matière"
      aide={s.e.prises.length ? 'changer de magasin efface les lots choisis' : undefined}
    >
      {courants.length <= 3 ? (
        <SegmentsTactiles
          libelle="Magasin d’où sort la matière"
          valeur={s.magasin}
          options={courants.map((m) => ({ valeur: m.id, libelle: m.code }))}
          onChange={choisir}
        />
      ) : (
        <Selecteur valeur={s.magasin} options={options} effacable={false} onChange={choisir} />
      )}
      {demande != null ? (
        <div className={styles.gestes} role="group" aria-label="Confirmation">
          <span>{`Changer de magasin efface les ${nombre(s.e.prises.length)} lots choisis ?`}</span>
          <Bouton taille="atelier" onClick={() => setDemande(null)}>
            Non
          </Bouton>
          <Bouton
            taille="atelier"
            variante="principal"
            onClick={() => {
              s.changerDemande({ magasin: demande, prises: [], besoins: [] })
              setDemande(null)
            }}
          >
            Oui, changer
          </Bouton>
        </div>
      ) : null}
    </Champ>
  )
}

function Fabrications({ s }: { s: SaisieSortie }) {
  const qualites = useLecture<QualiteResume[]>('/qualites')
  const fabs = s.e.fabrications
  const prises = new Set(fabs.map((f) => f.qualite))
  const changer = (i: number, m: Partial<(typeof fabs)[number]>) =>
    s.changerDemande({ fabrications: fabs.map((f, j) => (j === i ? { ...f, ...m } : f)) })
  return (
    <>
      {fabs.map((f, i) => (
        <Fiche key={i} libelle={fabs.length > 1 ? `Qualité n° ${i + 1}` : 'Qualité à fabriquer'}>
          <Champ libelle={fabs.length > 1 ? `Qualité n° ${i + 1}` : 'Qualité à fabriquer'}>
            <Selecteur
              valeur={f.qualite}
              placeholder="Taper le code ou le nom…"
              options={(qualites.data ?? [])
                .filter((q) => q.actif && (q.id === f.qualite || !prises.has(q.id)))
                .map((q) => ({ id: q.id, titre: `${q.code} — ${q.nom}` }))}
              onChange={(id) => changer(i, { qualite: id })}
            />
          </Champ>
          <Champ groupe libelle="Mètres carrés">
            <Compteur
              libelle="Mètres carrés"
              uniteDite="m²"
              decimales={0}
              valeur={f.m2}
              pas={50}
              min={0}
              onChange={(m2) => changer(i, { m2: m2 ?? 0 })}
            />
          </Champ>
          {fabs.length > 1 ? (
            <Bouton
              taille="atelier"
              variante="danger"
              onClick={() => s.changerDemande({ fabrications: fabs.filter((_, j) => j !== i) })}
            >
              Retirer cette qualité
            </Bouton>
          ) : null}
        </Fiche>
      ))}
      <Bouton
        taille="atelier"
        icone="plus"
        onClick={() => s.changerDemande({ fabrications: [...fabs, { qualite: null, m2: 0 }] })}
      >
        Une autre qualité sur le même ordre
      </Bouton>
    </>
  )
}

function libelleCalcul(s: SaisieSortie): string {
  if (s.e.horsRecette) return 'Choisir les fils et les lots'
  return s.e.prises.length ? 'Recalculer les fils et les lots' : 'Voir les fils et les lots à prendre'
}

function ChampsDemande({ s }: { s: SaisieSortie }) {
  const metiers = useMetiers()
  const bornes = useBornesDate()
  const choixMetiers = (metiers.data ?? [])
    .filter((m) => m.actif || m.id === s.e.metier)
    .sort((a, b) => (a.nom || a.code).localeCompare(b.nom || b.code, 'fr', { numeric: true }))
    .map((m) => ({ id: m.id, titre: nomMetier(m) }))
  return (
    <>
      <Champ libelle="Date de la sortie">
        <DateChamp valeur={s.e.jour} {...bornes} onChange={(jour) => s.changerDemande({ jour })} />
      </Champ>
      <ChoixMagasin s={s} />
      <Champ libelle="Métier (facultatif)">
        <Selecteur valeur={s.e.metier} options={choixMetiers} onChange={(metier) => s.poser({ metier })} />
      </Champ>
      <SegmentsTactiles
        libelle="Selon les recettes ou hors recette"
        valeur={s.e.horsRecette ? 'hors' : 'recette'}
        options={[
          { valeur: 'recette', libelle: 'Selon les recettes' },
          { valeur: 'hors', libelle: 'Ordre hors recette' },
        ]}
        onChange={(v) => s.changerDemande({ horsRecette: v === 'hors' })}
      />
      {s.e.horsRecette ? (
        <NoteAtelier>
          Échantillons, série spéciale : pas de qualité ; les fils et les lots se choisissent à la main à
          l’étape suivante.
        </NoteAtelier>
      ) : (
        <Fabrications s={s} />
      )}
      <Champ libelle="Observations (facultatif)">
        <Saisie
          valeur={s.e.commentaire}
          max={300}
          placeholder="Équipe, consigne, incident…"
          onChange={(commentaire) => s.poser({ commentaire })}
        />
      </Champ>
    </>
  )
}

export function EnvoyerDemande({ s }: { s: SaisieSortie }) {
  useEffect(enHaut, [])
  const empechements = useEmpechements(s)
  const manque = manqueDemande({ ...s.e, magasin: s.magasin })
  const revenir = s.e.prises.length > 0 && !s.e.demandeChangee
  return (
    <EcranAtelier
      titre={s.e.id ? 'Modifier l’ordre (brouillon)' : 'Envoyer aux machines'}
      enTete={<BandeauBlocages blocages={empechements} />}
    >
      <div className={styles.pile}>
        {s.repris && !s.e.id && s.e.prises.length ? (
          <NoteAtelier>
            La sortie commencée tout à l’heure est reprise telle quelle ; « Abandonner cette sortie », en bas
            de l’écran des lots, repart à vide.
          </NoteAtelier>
        ) : null}
        <ChampsDemande s={s} />
        {s.erreur ? <Note ton="critique">{s.erreur}</Note> : null}
        {revenir ? (
          <Bouton taille="atelier" variante="principal" bloc onClick={() => s.poser({ etape: 'lots' })}>
            Revenir aux lots
          </Bouton>
        ) : null}
        <Bouton
          taille="atelier"
          variante={revenir ? 'neutre' : 'principal'}
          bloc
          grise={manque || undefined}
          attente="Calcul…"
          onClick={s.proposer}
        >
          {libelleCalcul(s)}
        </Bouton>
        {s.e.prises.length && s.e.demandeChangee && !s.e.horsRecette ? (
          <NoteAtelier>
            Recalculer remplace les lots proposés ; les fils ajoutés à la main sont gardés.
          </NoteAtelier>
        ) : null}
      </div>
    </EcranAtelier>
  )
}
