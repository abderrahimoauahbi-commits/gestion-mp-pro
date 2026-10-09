/**
 * La fenêtre « Ouvrir un inventaire » (`/inventaires/nouveau`, ECRANS-PRO partie 6) : libellé
 * (proposé selon le périmètre et le magasin), date bornée, magasin, tolérance bornée à la frappe,
 * périmètre (tout, famille, certaines matières, tournant). « Ouvrir et figer le stock » est grisé
 * avec la raison qui suit l'état, puis confirmé sur place par une question qui dit l'effet.
 */
import { useState } from 'react'

import { Fenetre, useFermerFenetre } from '../../composants/mise-en-page/Fenetre'
import { Grille } from '../../composants/mise-en-page/Grille'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { Note } from '../../composants/retour/Note'
import { Bouton } from '../../composants/saisie/Bouton'
import { Champ } from '../../composants/saisie/Champ'
import { Confirmer } from '../../composants/saisie/Confirmer'
import { DateChamp } from '../../composants/saisie/DateChamp'
import { Nombre } from '../../composants/saisie/Nombre'
import { Saisie } from '../../composants/saisie/Saisie'
import { Segments } from '../../composants/saisie/Segments'
import { Selecteur } from '../../composants/saisie/Selecteur'
import { api } from '../../lib/api'
import { kg, nombre } from '../../lib/format'
import { aujourdhui } from '../../lib/heure'
import { useEcriture } from '../../lib/requetes'
import styles from './Inventaire.module.css'
import { corpsOuverture, manqueOuverture, messageConflit, PERIMETRES, questionOuverture } from './ouverture'
import { CertainesMatieres, ParFamille, Tournant } from './Perimetres'
import type { InventaireFiche } from './types'
import { useCalculsOuverture, useDonneesOuverture, type CalculsOuverture } from './useOuverture'
import type { SaisieOuverture } from './ouverture'

const VIERGE: SaisieOuverture = {
  libelle: '',
  date: '',
  magasin: null,
  tolerance: null,
  perimetre: 'tout',
  roles: [],
  compositions: [],
  classes: [],
  matieres: [],
  ecartees: [],
}

function Pied({ c, ouvrir }: { c: CalculsOuverture; ouvrir: () => Promise<unknown> }) {
  const fermer = useFermerFenetre()
  return (
    <>
      <Bouton onClick={fermer} titre="Fermer sans ouvrir l’inventaire">
        Annuler
      </Bouton>
      <Confirmer
        variante="principal"
        manque={manqueOuverture(c.saisie, c.min)}
        grise={c.grise}
        titre="Ouvre l’inventaire : le théorique est figé, les mouvements des matières comptées attendent"
        question={questionOuverture(c.nbLots, c.code)}
        oui="Oui, ouvrir l’inventaire"
        attente="Ouverture…"
        onOui={ouvrir}
      >
        Ouvrir et figer le stock
      </Confirmer>
    </>
  )
}

/** Libellé, date, magasin, tolérance, périmètre. */
function Champs({ c, poser }: { c: CalculsOuverture; poser: (m: Partial<SaisieOuverture>) => void }) {
  const s = c.saisie
  return (
    <Grille colonnes={4}>
      <Champ libelle="Libellé" large>
        <Saisie
          valeur={s.libelle}
          onChange={(libelle) => poser({ libelle })}
          max={120}
          placeholder={c.libelle}
        />
      </Champ>
      <Champ libelle="Date du comptage" obligatoire>
        <DateChamp
          valeur={s.date}
          onChange={(date) => poser({ date })}
          min={c.min}
          raisonMin="la période est close jusque-là"
        />
      </Champ>
      <Champ libelle="Magasin compté">
        <Selecteur
          effacable={false}
          valeur={s.magasin ?? 0}
          onChange={(id) => poser({ magasin: id ? id : null, matieres: [], ecartees: [] })}
          options={[
            { id: 0, titre: 'Tous les magasins' },
            ...c.magasins.map((g) => ({
              id: g.id,
              titre: `${g.code}${g.type === 'quarantaine' ? ' (quarantaine)' : ''}`,
              sous: kg(g.kg_detenus),
            })),
          ]}
        />
      </Champ>
      <Champ libelle="Tolérance (%)" aide="Au-delà, l’écart se justifie ; proposée par les réglages">
        <Nombre
          valeur={s.tolerance}
          onChange={(v) => poser({ tolerance: v })}
          min={0}
          max={100}
          decimales={2}
          unite="%"
        />
      </Champ>
      <Champ libelle="Ce qu’on compte" groupe large>
        <Segments
          valeur={s.perimetre}
          options={PERIMETRES}
          onChange={(perimetre) => poser({ perimetre })}
          libelle="Ce qu’on compte"
        />
      </Champ>
    </Grille>
  )
}

/** Ce qui sera figé et suspendu ; le conflit avec un inventaire ouvert. */
function Effets({ c, calcul }: { c: CalculsOuverture; calcul: boolean }) {
  return (
    <>
      <Note>
        {calcul
          ? 'Calcul…'
          : c.nbLots == null
            ? 'Les lots des matières retenues seront figés au théorique (la classe ABC se calcule à l’ouverture).'
            : `${nombre(c.nbLots)} lot(s) en stock seront figés au théorique.`}{' '}
        Pendant le comptage, les mouvements <strong>des matières comptées</strong> sont suspendus dans{' '}
        {c.code ? `le magasin ${c.code}` : 'tous les magasins'} : réceptions, sorties vers les machines,
        transferts et retours de ces matières attendront la validation (ou l’abandon) de l’inventaire. Les
        autres matières continuent de bouger. Ouvrir l’inventaire au moment de compter, pas avant.
      </Note>
      {c.conflit ? <Note ton="critique">{messageConflit(c.conflit, c.code)}</Note> : null}
    </>
  )
}

/** Les champs, le périmètre choisi, et ce que l'ouverture va faire. */
function Corps({
  c,
  d,
  poser,
}: {
  c: CalculsOuverture
  d: ReturnType<typeof useDonneesOuverture>
  poser: (m: Partial<SaisieOuverture>) => void
}) {
  const s2 = c.saisie
  if (!d.defauts.data) return null
  return (
    <div className={styles.fenetre}>
      <Champs c={c} poser={poser} />
      {s2.perimetre === 'famille' ? (
        <ParFamille
          defauts={d.defauts.data}
          roles={s2.roles}
          compositions={s2.compositions}
          classes={s2.classes}
          poser={poser}
        />
      ) : null}
      {s2.perimetre === 'matieres' ? (
        <CertainesMatieres
          enStock={c.enStock}
          choisies={s2.matieres}
          stockDe={c.stockDe}
          poser={(matieres) => poser({ matieres })}
        />
      ) : null}
      {s2.perimetre === 'tournant' ? (
        <Tournant
          dues={d.dues}
          ecartees={s2.ecartees}
          basculer={(id) =>
            poser({
              ecartees: s2.ecartees.includes(id) ? s2.ecartees.filter((x) => x !== id) : [...s2.ecartees, id],
            })
          }
        />
      ) : null}
      <Effets c={c} calcul={d.lots.isPending} />
    </div>
  )
}

export function OuvrirInventaire({
  onFermer,
  onOuvert,
}: {
  onFermer: () => void
  onOuvert: (id: number) => void
}) {
  const [modifie, setModifie] = useState(false)
  const [s, setS] = useState<SaisieOuverture>(() => ({ ...VIERGE, date: aujourdhui() }))
  const d = useDonneesOuverture(s)
  const c = useCalculsOuverture(s, d)
  const poser = (modif: Partial<SaisieOuverture>) => {
    setModifie(true)
    setS((x) => ({ ...x, ...modif }))
  }
  const ouverture = useEcriture(() =>
    api.post<InventaireFiche>('/inventaires', corpsOuverture(c.saisie, c.libelle, c.idsDues)),
  )
  const ouvrir = async () => onOuvert((await ouverture.mutateAsync()).id)
  const erreur = d.defauts.error ?? d.magasins.error ?? d.matieres.error
  return (
    <Fenetre
      titre="Ouvrir un inventaire"
      taille="tresLarge"
      sale={modifie}
      onFermer={onFermer}
      pied={<Pied c={c} ouvrir={ouvrir} />}
    >
      {erreur ? <Erreur erreur={erreur} /> : null}
      {!d.defauts.data && !erreur ? <Chargement quoi="ce que propose l’ouverture" /> : null}
      {d.defauts.data ? <Corps c={c} d={d} poser={poser} /> : null}
    </Fenetre>
  )
}
