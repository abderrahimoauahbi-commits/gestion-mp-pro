/**
 * Les deux façons de se connecter : par son visage (nom touché, puis code), ou par son identifiant.
 * POST /connexion (route 10) ; un refus est dit sous le champ et le code est vidé.
 */
import { useState, type FormEvent } from 'react'

import { Bouton } from '../../composants/saisie/Bouton'
import { Champ } from '../../composants/saisie/Champ'
import { Saisie } from '../../composants/saisie/Saisie'
import { api, messageErreur } from '../../lib/api'
import { LIBELLES_ROLES } from '../../lib/droits'
import type { Connexion, Moi, Visage } from '../../lib/types-provisoires-s2'
import { classes } from '../../composants/mise-en-page/classes'
import { ChampCode, libelleCode, useEntrer } from './commun'
import styles from './connexion.module.css'

/** L'alimentation entre au 4e chiffre : son code a exactement 4 chiffres (F-01, H-01). */
export function entreeAuQuatrieme(v: Visage): boolean {
  return v.role === 'alimentation' && (v.longueur_code ?? 4) === 4
}

/** Le corps de la connexion depuis un visage : l'identifiant s'il est publié, sinon le compte. */
export function corpsDuVisage(v: Visage, code: string): Connexion {
  return v.identifiant ? { identifiant: v.identifiant, code } : { compte: v.id, code }
}

function useConnecter() {
  const entrer = useEntrer()
  const [occupe, setOccupe] = useState(false)
  const [erreur, setErreur] = useState('')
  const connecter = async (corps: Connexion): Promise<boolean> => {
    if (occupe) return false
    setOccupe(true)
    setErreur('')
    try {
      entrer(await api.post<Moi>('/connexion', corps))
      return true
    } catch (e) {
      setErreur(messageErreur(e))
      return false
    } finally {
      setOccupe(false)
    }
  }
  return { occupe, erreur, setErreur, connecter }
}

function GrilleVisages({
  visages,
  choisi,
  onChoisir,
}: {
  visages: readonly Visage[]
  choisi: Visage | null
  onChoisir: (v: Visage) => void
}) {
  return (
    <div className={styles.visages} role="group" aria-label="Qui êtes-vous ?">
      {visages.map((v) => (
        <button
          type="button"
          key={v.id}
          aria-pressed={choisi?.id === v.id}
          className={classes(styles.visage, choisi?.id === v.id && styles.choisi)}
          onClick={() => onChoisir(v)}
        >
          <strong>{v.nom}</strong>
          <span>{LIBELLES_ROLES[v.role]}</span>
        </button>
      ))}
    </div>
  )
}

export function FormulaireVisages({ visages }: { visages: readonly Visage[] }) {
  const [choisi, setChoisi] = useState<Visage | null>(null)
  const [code, setCode] = useState('')
  const { occupe, erreur, setErreur, connecter } = useConnecter()
  const envoyer = async (secret: string) => {
    if (!choisi || !secret) return
    if (!(await connecter(corpsDuVisage(choisi, secret)))) setCode('')
  }
  const surCode = (v: string) => {
    setCode(v)
    if (choisi && entreeAuQuatrieme(choisi) && /^\d{4}$/.test(v)) void envoyer(v)
  }
  const soumettre = (e: FormEvent) => {
    e.preventDefault()
    void envoyer(code)
  }
  return (
    <form className={styles.formulaire} onSubmit={soumettre}>
      <GrilleVisages
        visages={visages}
        choisi={choisi}
        onChoisir={(v) => {
          setChoisi(v)
          setCode('')
          setErreur('')
        }}
      />
      {choisi ? (
        <>
          <Champ libelle={libelleCode(choisi.nom)} erreur={erreur || undefined}>
            <ChampCode
              valeur={code}
              onChange={surCode}
              numerique={choisi.role === 'alimentation'}
              autoFocus
            />
          </Champ>
          <div className={styles.gestes}>
            <Bouton
              type="submit"
              variante="principal"
              manque={code ? [] : ['votre code']}
              occupe={occupe}
              attente="Connexion…"
            >
              Entrer
            </Bouton>
          </div>
        </>
      ) : null}
    </form>
  )
}

export function FormulaireIdentifiant() {
  const [identifiant, setIdentifiant] = useState('')
  const [code, setCode] = useState('')
  const { occupe, erreur, connecter } = useConnecter()
  const manque = [...(identifiant.trim() ? [] : ['votre identifiant']), ...(code ? [] : ['votre code'])]
  const soumettre = async (e: FormEvent) => {
    e.preventDefault()
    if (manque.length) return
    if (!(await connecter({ identifiant: identifiant.trim().toLowerCase(), code }))) setCode('')
  }
  return (
    <form className={styles.formulaire} onSubmit={(e) => void soumettre(e)}>
      <Champ libelle="Identifiant">
        <Saisie valeur={identifiant} onChange={setIdentifiant} autoComplete="username" autoFocus max={40} />
      </Champ>
      <Champ libelle="Code" erreur={erreur || undefined}>
        <ChampCode valeur={code} onChange={setCode} />
      </Champ>
      <div className={styles.gestes}>
        <Bouton type="submit" variante="principal" manque={manque} occupe={occupe} attente="Connexion…">
          Entrer
        </Bouton>
      </div>
    </form>
  )
}
