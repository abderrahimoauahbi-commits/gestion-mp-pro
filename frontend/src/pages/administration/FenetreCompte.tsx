/**
 * Fenêtre « Compte de {nom} » / « Nouveau compte » (`/administration?onglet=comptes&compte=ID|
 * nouveau`). Le code suit la règle du rôle, dite à la frappe ; un changement de rôle qui ne
 * convient plus au code gardé en exige un nouveau (le serveur l'exige aussi, P8-11). Désactiver
 * ou réactiver n'envoie que l'état, sur la fiche **telle qu'enregistrée** (P8-10) ; on ne
 * change ni son propre rôle ni son propre état.
 */
import { useState } from 'react'

import { Fenetre, useFermerFenetre } from '../../composants/mise-en-page/Fenetre'
import { Grille } from '../../composants/mise-en-page/Grille'
import { dire } from '../../composants/retour/Messages'
import { Note } from '../../composants/retour/Note'
import { Bouton } from '../../composants/saisie/Bouton'
import { Champ } from '../../composants/saisie/Champ'
import { Confirmer } from '../../composants/saisie/Confirmer'
import { Saisie } from '../../composants/saisie/Saisie'
import { api } from '../../lib/api'
import { useEcriture } from '../../lib/requetes'
import { useSession } from '../../lib/session'
import type { Role, Schema } from '../../lib/types'
import styles from './administration.module.css'
import { consigne, exigeNouveauCode, manquesCompte, ROLES, type FormeCompte } from './compte'

export type Compte = Schema<'UtilisateurFiche'>

const roleDe = (c: Compte | undefined): Role => {
  const r = ROLES.find((x) => x.cle === c?.role)
  return r ? r.cle : 'achats'
}

const formeDe = (c: Compte | undefined): FormeCompte => ({
  nom: c?.nom ?? '',
  identifiant: c?.identifiant ?? '',
  role: roleDe(c),
  email: c?.email ?? '',
  code: '',
  code2: '',
})

function EtatDuCompte({ c, soi, sale }: { c: Compte; soi: boolean; sale: boolean }) {
  const ecrire = useEcriture((actif: boolean) =>
    api.put<Compte>(`/utilisateurs/${c.id}`, {
      nom: c.nom,
      role: c.role,
      email: c.email,
      actif,
      version: c.version,
    }),
  )
  const grise = soi
    ? 'C’est votre compte : vous ne pouvez ni changer votre rôle ni vous désactiver.'
    : sale
      ? 'Une saisie n’est pas enregistrée : l’enregistrer ou l’abandonner d’abord.'
      : undefined
  if (!c.actif) {
    return (
      <Bouton
        grise={grise}
        onClick={async () => {
          await ecrire.mutateAsync(true)
          dire(`Compte de ${c.nom} réactivé.`)
        }}
      >
        Réactiver le compte
      </Bouton>
    )
  }
  return (
    <Confirmer
      variante="danger"
      grise={grise}
      titre="Le compte ne pourra plus se connecter et ses sessions ouvertes sont fermées ; il se réactive plus tard"
      question={`Désactiver ${c.nom} ?`}
      oui="Oui, désactiver"
      onOui={async () => {
        await ecrire.mutateAsync(false)
        dire(`Compte de ${c.nom} désactivé : ses sessions sont fermées.`)
      }}
    >
      Désactiver le compte
    </Confirmer>
  )
}

function Pied({
  c,
  f,
  sale,
  soi,
  onFait,
}: {
  c?: Compte
  f: FormeCompte
  sale: boolean
  soi: boolean
  onFait: () => void
}) {
  const fermer = useFermerFenetre()
  const ecrire = useEcriture(() => {
    const commun = { nom: f.nom.trim(), role: f.role, email: f.email.trim() }
    if (!c)
      return api.post<Compte>('/utilisateurs', { ...commun, identifiant: f.identifiant.trim(), code: f.code })
    return api.put<Compte>(`/utilisateurs/${c.id}`, {
      ...commun,
      actif: c.actif,
      version: c.version,
      code: f.code || null,
    })
  })
  const libelle = !c ? 'Créer le compte' : f.code ? 'Enregistrer et remettre le code' : 'Enregistrer'
  return (
    <>
      {c ? <EtatDuCompte c={c} soi={soi} sale={sale} /> : null}
      <span className={styles.pousse} />
      <Bouton variante="fantome" onClick={fermer}>
        {sale ? 'Abandonner les modifications' : 'Fermer'}
      </Bouton>
      <Bouton
        variante="principal"
        manque={manquesCompte(f, !c, c ? roleDe(c) : null)}
        grise={c && !sale ? 'Aucune modification' : undefined}
        attente="Enregistrement…"
        onClick={async () => {
          await ecrire.mutateAsync()
          dire(
            !c
              ? `Compte créé : ${f.nom.trim()} (identifiant « ${f.identifiant.trim()} »).`
              : f.code
                ? `Compte de ${f.nom.trim()} enregistré, nouveau code remis.`
                : `Compte de ${f.nom.trim()} enregistré.`,
          )
          onFait()
        }}
      >
        {libelle}
      </Bouton>
    </>
  )
}

interface ChampsProps {
  c?: Compte
  f: FormeCompte
  poser: (champ: Partial<FormeCompte>) => void
  soi: boolean
}

function Retaper({ f, poser }: Pick<ChampsProps, 'f' | 'poser'>) {
  return (
    <Champ
      libelle="Retaper le code"
      erreur={f.code2 && f.code !== f.code2 ? 'les deux saisies diffèrent' : null}
    >
      <Saisie
        type="password"
        valeur={f.code2}
        max={128}
        autoComplete="new-password"
        onChange={(v) => poser({ code2: v })}
      />
    </Champ>
  )
}

function ChampsCompte({ c, f, poser, soi }: ChampsProps) {
  const codeRequis = !c || exigeNouveauCode(roleDe(c), f.role)
  const aideIdentifiant = c
    ? 'l’identifiant ne change pas'
    : f.identifiant
      ? `en minuscules, sans espace : il sera « ${f.identifiant} »`
      : 'en minuscules, sans espace (ex. : sara)'
  return (
    <Grille colonnes={2}>
      <Champ libelle="Nom affiché" aide="tel qu’il apparaît à la connexion et dans le journal" obligatoire>
        <Saisie valeur={f.nom} max={80} onChange={(v) => poser({ nom: v })} autoFocus={!c} />
      </Champ>
      <Champ libelle="Identifiant" aide={aideIdentifiant} obligatoire={!c}>
        <Saisie
          valeur={f.identifiant}
          max={40}
          desactive={Boolean(c)}
          onChange={(v) => poser({ identifiant: v.replace(/\s/g, '').toLowerCase() })}
        />
      </Champ>
      <Champ libelle="Rôle" aide={ROLES.find((r) => r.cle === f.role)?.aide}>
        <select
          className={styles.choix}
          value={f.role}
          disabled={soi}
          onChange={(e) => poser({ role: ROLES.find((r) => r.cle === e.target.value)?.cle ?? 'achats' })}
        >
          {ROLES.map((r) => (
            <option key={r.cle} value={r.cle}>
              {r.libelle}
            </option>
          ))}
        </select>
      </Champ>
      <Champ libelle="Courriel (facultatif)">
        <Saisie type="email" valeur={f.email} max={200} onChange={(v) => poser({ email: v })} />
      </Champ>
      <Champ
        libelle={codeRequis ? 'Code' : 'Nouveau code (laisser vide pour le garder)'}
        aide={
          c && codeRequis
            ? `nouveau rôle : un nouveau code est nécessaire, ${consigne(f.role)}`
            : consigne(f.role)
        }
        obligatoire={codeRequis}
      >
        <Saisie
          type="password"
          valeur={f.code}
          max={128}
          autoComplete="new-password"
          onChange={(v) => poser({ code: v })}
        />
      </Champ>
      <Retaper f={f} poser={poser} />
    </Grille>
  )
}

export function FenetreCompte({ c, onFermer }: { c?: Compte; onFermer: () => void }) {
  const { moi } = useSession()
  const [f, setF] = useState(() => formeDe(c))
  const sale = JSON.stringify(f) !== JSON.stringify(formeDe(c))
  const soi = c?.id === moi.id
  const poser = (champ: Partial<FormeCompte>) => setF({ ...f, ...champ })
  return (
    <Fenetre
      titre={c ? `Compte de ${c.nom}` : 'Nouveau compte'}
      taille="large"
      onFermer={onFermer}
      sale={sale}
      pied={<Pied c={c} f={f} sale={sale} soi={soi} onFait={onFermer} />}
    >
      {c && !c.actif ? (
        <Note ton="attention">Ce compte est désactivé : il ne peut plus se connecter.</Note>
      ) : null}
      {soi ? (
        <Note>C’est votre compte : vous ne pouvez ni changer votre rôle ni vous désactiver.</Note>
      ) : null}
      {c?.historique ? (
        <Note ton="attention">
          Ce compte vient de la reprise de Gestion MP : il garde l’histoire et ne se modifie pas.
        </Note>
      ) : null}
      <ChampsCompte c={c} f={f} poser={poser} soi={soi} />
    </Fenetre>
  )
}
