/**
 * Saisie d'ordre (`/ordres/nouveau` ; un brouillon se modifie sur `/ordres/:id`) : la demande et les
 * matières sur le même écran, dans une grande fenêtre gardée (`sale`). Ce que le serveur refusera
 * est dit **avant** l'envoi, avec ses mots, en tête et sur « Valider la sortie » ; « Garder en
 * brouillon » ne demande qu'une ligne. Moteur : `ordre.ts` et `useSaisieOrdre.ts`.
 */
import { Bascule } from '../../composants/mise-en-page/Bascule'
import { Fenetre, useFermerFenetre } from '../../composants/mise-en-page/Fenetre'
import { Grille } from '../../composants/mise-en-page/Grille'
import { dire } from '../../composants/retour/Messages'
import { Note } from '../../composants/retour/Note'
import { Blocages } from '../../composants/saisie/Blocages'
import { Bouton } from '../../composants/saisie/Bouton'
import { Champ } from '../../composants/saisie/Champ'
import { Confirmer } from '../../composants/saisie/Confirmer'
import { DateChamp } from '../../composants/saisie/DateChamp'
import { Nombre } from '../../composants/saisie/Nombre'
import { Saisie } from '../../composants/saisie/Saisie'
import { Selecteur } from '../../composants/saisie/Selecteur'
import { date, jourRelatif, kg, kgEtMetres } from '../../lib/format'
import { ajouterJours } from '../../lib/heure'
import { useSession } from '../../lib/session'
import styles from '../stock/stock.module.css'
import {
  dernierOrdre,
  nomMetier,
  useMetiers,
  useOrdres,
  useQualites,
  type OrdreFiche,
  type QualiteResume,
} from './donnees'
import { LignesSaisie } from './LignesSaisie'
import { aEnvoyer } from './ordre'
import { useSaisieOrdre, type SaisieOrdre as Saisie_ } from './useSaisieOrdre'

/** La borne basse de la date : lendemain de la clôture, et pas avant le dernier ordre validé. */
function borneBasse(cloture: string | null, dernier: string | null) {
  const apresCloture = cloture ? ajouterJours(cloture, 1) : ''
  if (dernier && dernier > apresCloture)
    return {
      min: dernier,
      raison: `un ordre du ${date(dernier)} est déjà validé (les numéros suivent les dates)`,
    }
  return apresCloture
    ? { min: apresCloture, raison: `la période est close jusqu’au ${date(cloture)}` }
    : { min: undefined, raison: undefined }
}

function Demande({ s, sauf }: { s: Saisie_; sauf: number | null }) {
  const { contexte } = useSession()
  const metiers = useMetiers()
  const ordres = useOrdres()
  const borne = borneBasse(contexte.date_cloture, dernierOrdre(ordres.data, sauf))
  return (
    <Grille colonnes={4}>
      <Champ libelle="Date" obligatoire>
        <DateChamp valeur={s.jour} onChange={s.setJour} min={borne.min} raisonMin={borne.raison} />
      </Champ>
      <Champ
        libelle="Magasin de sortie"
        obligatoire
        aide={s.prises.length ? 'changer de magasin efface les lots choisis' : undefined}
      >
        <Selecteur
          valeur={s.magasinChoisi}
          options={s.magasins.map((g) => ({ id: g.id, titre: g.code, sous: g.nom }))}
          onChange={(id) => s.setMagasin(id)}
        />
      </Champ>
      <Champ libelle="Métier">
        <Selecteur
          valeur={s.metier}
          effacable
          options={(metiers.data ?? [])
            .filter((m) => m.actif || m.id === s.metier)
            .map((m) => ({ id: m.id, titre: nomMetier(m) }))}
          onChange={(id) => s.setMetier(id)}
          placeholder="—"
        />
      </Champ>
      <Champ libelle="Commentaire">
        <Saisie
          valeur={s.commentaire}
          onChange={s.setCommentaire}
          max={300}
          placeholder="Équipe, consigne, incident…"
        />
      </Champ>
    </Grille>
  )
}

/** Une qualité de l'ordre : laquelle (une seule fois), ses m², « Retirer ». */
function LigneQualite({ s, i, options }: { s: Saisie_; i: number; options: readonly QualiteResume[] }) {
  const f = s.fabrications[i] ?? { qualite_id: null, m2: null }
  const choisies = new Set(s.fabrications.map((x) => x.qualite_id))
  return (
    <Grille colonnes={3}>
      <Champ libelle={`Qualité ${i + 1}`}>
        <Selecteur
          valeur={f.qualite_id}
          options={options
            .filter((q) => q.id === f.qualite_id || !choisies.has(q.id))
            .map((q) => ({ id: q.id, titre: `${q.code} — ${q.nom}` }))}
          onChange={(id) => s.setFabrication(i, { qualite_id: id })}
          placeholder="Code ou nom de la qualité…"
        />
      </Champ>
      <Champ libelle="m² à tisser">
        <Nombre
          valeur={f.m2}
          onChange={(m2) => s.setFabrication(i, { m2 })}
          min={0}
          decimales={2}
          unite="m²"
        />
      </Champ>
      <Champ libelle="Retirer">
        {s.fabrications.length > 1 ? (
          <Bouton taille="petit" onClick={() => s.retirerFabrication(i)}>
            Retirer
          </Bouton>
        ) : (
          <span className={styles.note}>—</span>
        )}
      </Champ>
    </Grille>
  )
}

function Proposer({ s }: { s: Saisie_ }) {
  const proposes = s.besoins.length > 0
  return (
    <div className={styles.rangee}>
      <Bouton taille="petit" icone="plus" onClick={s.ajouterFabrication}>
        Une autre qualité
      </Bouton>
      <Bouton
        variante={proposes && !s.demandeChangee ? 'neutre' : 'principal'}
        manque={s.manqueProposer}
        occupe={s.proposeEnCours}
        attente="Calcul…"
        titre="Calcule les matières d’après les recettes et propose les lots les plus anciens, tels qu’ils étaient à la date de l’ordre"
        onClick={s.proposer}
      >
        {proposes ? 'Recalculer' : 'Proposer les matières à sortir'}
      </Bouton>
      {proposes && s.demandeChangee ? (
        <span className={styles.note}>
          La demande a changé : recalculer remplace les lots proposés (les matières ajoutées à la main
          restent).
        </span>
      ) : null}
    </div>
  )
}

function CeQuOnTisse({ s }: { s: Saisie_ }) {
  const qualites = useQualites()
  const actives = (qualites.data ?? []).filter((q) => q.actif)
  return (
    <>
      <div className={styles.rangee}>
        <strong>1 · Ce qu’on tisse</strong>
        <Bascule
          vues={[
            { cle: 'recette', libelle: 'Selon les recettes' },
            { cle: 'hors', libelle: 'Ordre hors recette' },
          ]}
          valeur={s.horsRecette ? 'hors' : 'recette'}
          onChange={(v) => s.setHorsRecette(v === 'hors')}
          libelle="Ce qu’on tisse"
        />
        <span className={styles.note}>
          {s.horsRecette
            ? 'Échantillons, série spéciale : ajouter les matières à la main.'
            : 'Une qualité une seule fois ; une matière qui sert plusieurs qualités sort une fois, pour la somme de ses besoins.'}
        </span>
      </div>
      {!s.horsRecette ? (
        <>
          {s.fabrications.map((_, i) => (
            <LigneQualite key={i} s={s} i={i} options={actives} />
          ))}
          <Proposer s={s} />
        </>
      ) : null}
    </>
  )
}

function AjouterMatiere({ s }: { s: Saisie_ }) {
  const pris = new Set(s.prises.map((p) => p.lot_id))
  const options = s.lotsDuMagasin
    .filter((l) => !pris.has(l.lot_id) && (s.dispo?.get(l.lot_id) ?? 0) > 0.0005)
    .map((l) => ({
      id: l.lot_id,
      titre: `${l.reference} · lot ${l.lot}`,
      sous: kgEtMetres(s.dispo?.get(l.lot_id), l.kg_par_ml),
      recherche: l.designation,
    }))
  return (
    <div className={styles.ajout}>
      <Selecteur
        valeur={null}
        options={options}
        libelle={s.horsRecette ? 'Ajouter une matière' : 'Ajouter une matière hors recette'}
        placeholder={
          s.horsRecette
            ? '+ Ajouter une matière : référence ou lot…'
            : '+ Ajouter une matière hors recette : référence ou lot…'
        }
        vide="Aucun lot de ce magasin ne porte de matière à cette date."
        onChange={(id) => {
          const l = s.lotsDuMagasin.find((x) => x.lot_id === id)
          if (l)
            s.ajouter({
              matiere_id: l.matiere_id,
              reference: l.reference,
              designation: l.designation,
              kg_par_ml: l.kg_par_ml,
              poids_bobine: l.poids_bobine,
              bobines_palette: l.bobines_palette,
              lot_id: l.lot_id,
              lot: l.lot,
              kg: null,
              unite: 'kg',
            })
        }}
      />
    </div>
  )
}

function Pied({ s, metier, onFait }: { s: Saisie_; metier: string; onFait: (b: OrdreFiche) => void }) {
  const fermer = useFermerFenetre()
  const total = aEnvoyer(s.prises).reduce((t, p) => t + (p.kg ?? 0), 0)
  const ou = [`le ${date(s.jour)} (${jourRelatif(s.jour)})`, s.magasinCode, metier]
    .filter(Boolean)
    .join(' · ')
  const garder = async () => {
    const b = await s.enregistrer(false)
    dire('Ordre gardé en brouillon : le stock n’a pas bougé.')
    onFait(b)
  }
  const valider = async () => {
    const b = await s.enregistrer(true)
    dire(`Ordre ${b.numero ?? ''} validé : ${kg(b.net || total)} sortis.`)
    onFait(b)
  }
  return (
    <>
      <span className={styles.note}>
        {aEnvoyer(s.prises).length} ligne(s) · {kg(total)}
      </span>
      <span className={styles.pousse} />
      <Bouton titre="Fermer sans enregistrer" onClick={fermer}>
        Fermer
      </Bouton>
      <Bouton
        manque={s.manqueBrouillon}
        titre="Enregistrer sans sortir le stock : l’ordre reste modifiable"
        onClick={garder}
        attente="Enregistrement…"
      >
        Garder en brouillon
      </Bouton>
      <Confirmer
        variante="principal"
        manque={s.manqueBrouillon}
        blocages={s.blocages}
        question={`Sortir ${kg(total)} ${ou} ? Le stock est débité tout de suite.`}
        oui="Oui, valider la sortie"
        titre="Valider : le stock sort et l’ordre reçoit son numéro"
        attente="Enregistrement…"
        onOui={valider}
      >
        Valider la sortie
      </Confirmer>
    </>
  )
}

export function SaisieOrdre({
  fiche,
  onFermer,
  onFait,
}: {
  fiche: OrdreFiche | null
  onFermer: () => void
  onFait: (b: OrdreFiche) => void
}) {
  const s = useSaisieOrdre(fiche)
  const metiers = useMetiers()
  const metier = metiers.data?.find((m) => m.id === s.metier)
  const manques = s.besoins.filter((b) => b.manque > 0.05)
  return (
    <Fenetre
      titre={fiche ? 'Modifier l’ordre — Brouillon' : 'Nouvel ordre — Brouillon'}
      taille="tresLarge"
      sale={s.sale}
      onFermer={onFermer}
      pied={<Pied s={s} metier={metier ? nomMetier(metier) : ''} onFait={onFait} />}
    >
      <Blocages blocages={s.blocages} titre="Sera refusé à la validation :" />
      <Demande s={s} sauf={fiche?.id ?? null} />
      <CeQuOnTisse s={s} />
      <strong>2 · Les matières qui sortent</strong>
      {s.incompletes.map((x) => (
        <Note key={x} ton="critique">
          Recette incomplète — {x}
        </Note>
      ))}
      {manques.length ? (
        <Note>
          Il manque dans ce magasin :{' '}
          {manques.map((b) => `${b.reference} (${kgEtMetres(b.manque, b.kg_par_ml)})`).join(' · ')}. Les
          transférer d’abord, ou sortir ce qu’il y a : l’écart restera visible sur l’ordre.
        </Note>
      ) : null}
      <LignesSaisie s={s} />
      <AjouterMatiere s={s} />
    </Fenetre>
  )
}
