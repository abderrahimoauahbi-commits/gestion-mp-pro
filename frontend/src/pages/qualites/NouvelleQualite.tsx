/**
 * « Nouvelle qualité » (`/qualites/nouvelle` ; direction) : code (tel qu'il figure sur les ordres
 * de fabrication), nom, poids d'un m² rôle par rôle. Une fois créée, la qualité s'ouvre sur sa
 * recette ; son plan se saisit dans la page Production.
 */
import { useState } from 'react'

import { Fenetre, useFermerFenetre } from '../../composants/mise-en-page/Fenetre'
import { Grille } from '../../composants/mise-en-page/Grille'
import { Chargement } from '../../composants/retour/Chargement'
import { dire } from '../../composants/retour/Messages'
import { Note } from '../../composants/retour/Note'
import { Bouton } from '../../composants/saisie/Bouton'
import { Champ } from '../../composants/saisie/Champ'
import { Saisie } from '../../composants/saisie/Saisie'
import { api } from '../../lib/api'
import { useEcriture } from '../../lib/requetes'
import styles from '../catalogue/catalogue.module.css'
import { useClassification } from '../catalogue/donnees'
import { ChampsPoids, rolesDansLOrdre } from './ChampsPoids'
import { poidsEnvoyes, versFormeQualite, type FormeQualite } from './formeQualite'
import type { QualiteFiche } from './types'

/** Le code d'une qualité tient en 32 caractères (`longueurs.CODE_QUALITE`), le nom en 120. */
export const CODE_MAX = 32
export const NOM_MAX = 120

function Pied({ forme, sale, creer }: { forme: FormeQualite; sale: boolean; creer: () => Promise<void> }) {
  const fermer = useFermerFenetre()
  return (
    <div className={styles.pied}>
      <span className={styles.pousse} />
      <Bouton variante="fantome" onClick={fermer}>
        {sale ? 'Abandonner' : 'Annuler'}
      </Bouton>
      <Bouton
        variante="principal"
        manque={forme.code.trim() ? undefined : ['le code']}
        attente="Création…"
        onClick={creer}
      >
        Créer la qualité
      </Bouton>
    </div>
  )
}

function CodeNom({
  forme,
  setForme,
}: {
  forme: FormeQualite
  setForme: (maj: (f: FormeQualite) => FormeQualite) => void
}) {
  return (
    <Grille colonnes={2}>
      <Champ libelle="Code" obligatoire aide="tel qu’il figure sur les ordres de fabrication">
        <Saisie
          valeur={forme.code}
          onChange={(v) => setForme((f) => ({ ...f, code: v }))}
          max={CODE_MAX}
          autoFocus
        />
      </Champ>
      <Champ libelle="Nom">
        <Saisie valeur={forme.nom} onChange={(v) => setForme((f) => ({ ...f, nom: v }))} max={NOM_MAX} />
      </Champ>
    </Grille>
  )
}

export function NouvelleQualite({
  onFermer,
  onCree,
}: {
  onFermer: () => void
  onCree: (id: number) => void
}) {
  const c = useClassification()
  const [forme, setForme] = useState<FormeQualite>(() => versFormeQualite(null))
  const ecriture = useEcriture((f: FormeQualite) =>
    api.post<QualiteFiche>('/qualites', {
      code: f.code.trim(),
      nom: f.nom.trim(),
      actif: true,
      poids: poidsEnvoyes(f),
    }),
  )
  const sale = Boolean(forme.code.trim() || forme.nom.trim() || poidsEnvoyes(forme).length)
  const creer = async () => {
    const q = await ecriture.mutateAsync(forme)
    setForme(versFormeQualite(null))
    dire(`Qualité « ${q.code} » créée : sa recette se saisit maintenant.`)
    if (q.avertissement) dire(q.avertissement, 'attention')
    onCree(q.id)
  }
  return (
    <Fenetre
      titre="Nouvelle qualité"
      onFermer={onFermer}
      sale={sale}
      taille="large"
      pied={<Pied forme={forme} sale={sale} creer={creer} />}
    >
      <CodeNom forme={forme} setForme={setForme} />
      <strong>Poids d’un m² de tapis, rôle par rôle (laisser à zéro les rôles qui n’entrent pas)</strong>
      {c.data ? (
        <ChampsPoids
          roles={rolesDansLOrdre(c.data.roles)}
          poids={forme.poids}
          onChange={(id, v) => setForme((f) => ({ ...f, poids: { ...f.poids, [id]: v } }))}
        />
      ) : (
        <Chargement quoi="les rôles" />
      )}
      <Note>
        Une fois créée, la qualité s’ouvre sur sa recette. Son plan se saisit ensuite dans la page Production.
      </Note>
    </Fenetre>
  )
}
