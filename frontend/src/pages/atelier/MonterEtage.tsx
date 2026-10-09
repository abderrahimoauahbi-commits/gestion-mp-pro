/**
 * Monter un étage (`/atelier/montage?metier=ID&etage=N`) : la largeur montée, les fils (mètres,
 * part bornée 0…100 à la frappe, observations), l'ajout d'un fil au poids de bobine retenu, puis
 * la carte de confirmation qui annonce l'effet sur le stock sur les métiers (texte unique (a),
 * alerte 30 jours). La saisie est gardée avec la version lue (an. 17) ; un conflit se recharge.
 */
import { EcranAtelier } from '../../composants/atelier/EcranAtelier'
import { Note } from '../../composants/retour/Note'
import { Progression } from '../../composants/retour/Progression'
import { Bouton } from '../../composants/saisie/Bouton'
import { Champ } from '../../composants/saisie/Champ'
import { Confirmer } from '../../composants/saisie/Confirmer'
import { Selecteur } from '../../composants/saisie/Selecteur'
import { kgTelephone, nombre } from '../../lib/format'
import { useLecture } from '../../lib/requetes'
import { attente, Fiche, Ligne, NoteAtelier } from './briques'
import { nomMetier } from './commun'
import styles from './atelier.module.css'
import { CarteFil } from './CarteFil'
import { largeurDe, poidsRetenu, raisonEtage, type FilSaisi } from './calculMontage'
import type { MatiereMontage, MetierFiche } from './types'
import { useMontageEtage, type MontageEtage } from './useMontageEtage'

function Largeur({ m, t }: { m: MetierFiche; t: MontageEtage }) {
  const largeur = largeurDe(t.s.fils)
  return (
    <Fiche>
      <Ligne libelle="Largeur montée">{`${nombre(largeur, 2)} / ${nombre(m.laize, 2)} m`}</Ligne>
      <Progression
        libelle="Largeur montée"
        part={m.laize ? largeur / m.laize : 0}
        ton={t.trop ? 'critique' : 'accent'}
      />
      <Ligne libelle={`${nombre(t.bobines)} bobines`}>{kgTelephone(t.poids)}</Ligne>
      {t.trop ? (
        <Note ton="critique">{`Plus large que la laize : ${nombre(largeur - m.laize, 2)} m de trop.`}</Note>
      ) : null}
      {m.densite_a_saisir ? (
        <Note ton="critique">
          La densité de ce métier n’est pas saisie : le poids reste à zéro (direction).
        </Note>
      ) : null}
    </Fiche>
  )
}

function Ajout({
  m,
  t,
  etage,
  matieres,
}: {
  m: MetierFiche
  t: MontageEtage
  etage: number
  matieres?: MatiereMontage[]
}) {
  const deja = new Set(t.s.fils.map((f) => f.matiere_id))
  const options = (matieres ?? [])
    .filter((x) => x.actif && !deja.has(x.matiere_id))
    .map((x) => ({
      id: x.matiere_id,
      titre: x.designation ? `${x.reference} — ${x.designation}` : x.reference,
      sous: x.poids_bobine_compte
        ? `${nombre(x.poids_bobine_compte, 2)} kg / bobine`
        : 'poids de bobine inconnu',
    }))
  const ajouter = (id: number | null) => {
    const x = matieres?.find((y) => y.matiere_id === id)
    if (!x) return
    const fil: FilSaisi = {
      matiere_id: x.matiere_id,
      reference: x.reference,
      designation: x.designation,
      metres: Math.max(0, Math.round((m.laize - largeurDe(t.s.fils)) * 100) / 100),
      pourcentage: 100,
      commentaire: '',
    }
    t.poserFils([...t.s.fils, fil])
  }
  return (
    <Champ libelle={`Monter un fil à l’étage ${etage}`}>
      <Selecteur
        valeur={null}
        placeholder="Taper : rouge 2900, beige…"
        options={options}
        onChange={ajouter}
      />
    </Champ>
  )
}

function Confirmation({ t, etage }: { t: MontageEtage; etage: number }) {
  return (
    <Fiche ton={t.alertes.length ? 'alerte' : undefined} libelle="Confirmation du montage">
      <strong>{t.s.fils.length ? `Enregistrer l’étage ${etage} ?` : `Vider l’étage ${etage} ?`}</strong>
      <span>{t.message}</span>
      {t.alertes.map((a) => (
        <Note key={a} ton="critique">
          <strong>Attention : {a}</strong>
        </Note>
      ))}
      <Bouton taille="atelier" variante="principal" bloc attente="Enregistrement…" onClick={t.enregistrer}>
        {t.s.fils.length ? 'Oui, enregistrer' : 'Oui, vider l’étage'}
      </Bouton>
      <Bouton taille="atelier" bloc onClick={() => t.setConfirmer(false)}>
        Non, revenir au montage
      </Bouton>
    </Fiche>
  )
}

function Gestes({ t, etage }: { t: MontageEtage; etage: number }) {
  const raison = raisonEtage(t)
  return (
    <div className={styles.gestes}>
      {t.conflit ? (
        <>
          <Note ton="critique">{t.conflit}</Note>
          <Bouton taille="atelier" bloc onClick={t.recharger}>
            Recharger l’étage
          </Bouton>
        </>
      ) : null}
      {t.confirmer ? (
        <Confirmation t={t} etage={etage} />
      ) : (
        <Bouton
          taille="atelier"
          variante="principal"
          bloc
          grise={raison || undefined}
          onClick={() => t.setConfirmer(true)}
        >
          {t.sansMetres.length ? 'Saisir les mètres de chaque fil' : `Enregistrer l’étage ${etage}…`}
        </Bouton>
      )}
      {t.modifie ? (
        <Confirmer
          taille="atelier"
          question="Annuler les modifications de l’étage ?"
          oui="Oui, annuler"
          onOui={t.annuler}
        >
          Annuler les modifications
        </Confirmer>
      ) : null}
    </div>
  )
}

function Etage({ m, etage, matieres }: { m: MetierFiche; etage: number; matieres?: MatiereMontage[] }) {
  const t = useMontageEtage(m, etage, matieres)
  return (
    <div className={styles.pile}>
      {t.fait ? <Note ton="ok">{t.fait}</Note> : null}
      {t.perimee ? (
        <>
          <Note ton="attention">L’étage a été modifié ailleurs depuis : le recharger.</Note>
          <Bouton taille="atelier" bloc onClick={t.recharger}>
            Recharger l’étage
          </Bouton>
        </>
      ) : null}
      <Largeur m={m} t={t} />
      <NoteAtelier>
        <strong>Mètres montés</strong> : la largeur de l’étage que ce fil garnit. <strong>Part du fil</strong>{' '}
        : quand deux fils se partagent les mêmes mètres (retors, mélange), la part de celui-ci ; 100 % sinon.
        Bobines = mètres × {nombre(m.bobines_par_metre)} par mètre × part ; poids = bobines × kg par bobine
        pesé au lot.
      </NoteAtelier>
      {!t.s.fils.length ? (
        <NoteAtelier>{`L’étage ${etage} est vide : monter un fil ci-dessous.`}</NoteAtelier>
      ) : null}
      {t.s.fils.map((f) => (
        <CarteFil
          key={f.matiere_id}
          m={m}
          f={f}
          t={t}
          poids={poidsRetenu(m, matieres, f.matiere_id)}
          matieres={matieres}
        />
      ))}
      <Ajout m={m} t={t} etage={etage} matieres={matieres} />
      <Gestes t={t} etage={etage} />
    </div>
  )
}

export function MonterEtage({ id, etage }: { id: number; etage: number }) {
  const metier = useLecture<MetierFiche>(`/metiers/${id}`)
  const matieres = useLecture<MatiereMontage[]>('/montage/matieres')
  const metiers = useLecture<MetierFiche[]>('/metiers')
  const m = metier.data
  const titre = m ? `${nomMetier(m)} · étage ${etage}` : `Étage ${etage}`
  const enAttente = attente([metier, matieres, metiers], 'l’étage')
  return (
    <EcranAtelier titre={titre} retour={`/atelier/montage?metier=${id}`}>
      {enAttente ?? (m ? <Etage m={m} etage={etage} matieres={matieres.data} /> : null)}
    </EcranAtelier>
  )
}
