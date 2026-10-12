/**
 * Préparer une commande — {fournisseur} (ECRANS-PRO 4.4), en fenêtre très large par-dessus le plan
 * d'achat (`/plan-achat/preparer/:fournisseurId`) ou les commandes (`/commandes/nouvelle?fournisseur=`).
 * Le calcul suggère, l'acheteur arbitre en kilos **et** dans l'unité de commande ; le bon est créé
 * en brouillon, sans numéro (un par devise, dans la même transaction). Il ne porte jamais de prix
 * imprimé : la case ne fait que poser nos prix du catalogue, « à confirmer », sur le bon interne.
 */
import { Champ } from '../../composants/saisie/Champ'
import { DateChamp } from '../../composants/saisie/DateChamp'
import { Nombre } from '../../composants/saisie/Nombre'
import { Selecteur } from '../../composants/saisie/Selecteur'
import { Zone } from '../../composants/saisie/Zone'
import { Fenetre } from '../../composants/mise-en-page/Fenetre'
import { Indicateurs } from '../../composants/mise-en-page/Indicateurs'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { Kpi } from '../../composants/retour/Kpi'
import { Note } from '../../composants/retour/Note'
import { formule } from '../../lib/aide'
import { date, jours, kg, montant, montants, nombre } from '../../lib/format'
import { aujourdhui } from '../../lib/heure'
import styles from './achats.module.css'
import { useDevises, useMatieresDuFournisseur, usePreparation } from './donnees'
import { PiedPreparation } from './PiedPreparation'
import { placeRestante, retenues, totaux } from './calculPreparation'
import { TablePreparation } from './TablePreparation'
import type { CommandeCreee, Preparation as PreparationLue } from './types'
import { useSaisiePreparation, type SaisiePreparation } from './useSaisiePreparation'

function IndicateursPreparation({ s }: { s: SaisiePreparation }) {
  const devises = useDevises()
  const t = totaux(s.lignes, devises.data ?? [])
  const place = placeRestante(t.palettes, s.parConteneur)
  const etrangeres = Object.keys(t.parDevise).some((d) => d !== 'MAD')
  return (
    <Indicateurs>
      <Kpi
        titre="Lignes retenues"
        valeur={`${nombre(retenues(s.lignes).length)} / ${nombre(s.lignes.length)}`}
        formule={formule('preparation_lignes')}
      />
      <Kpi titre="Quantité totale" valeur={kg(t.kilos)} formule={formule('preparation_quantite')} />
      <Kpi
        titre="Palettes"
        valeur={nombre(t.palettes, 1)}
        formule={formule('preparation_palettes')}
        ton={place.libres > 0.05 ? 'attention' : undefined}
        detail={
          place.conteneurs == null ? 'palettes / conteneur ?' : `${nombre(place.conteneurs, 2)} conteneur(s)`
        }
      />
      <Kpi
        titre="Montant indicatif"
        valeur={montants(t.parDevise)}
        formule={formule('preparation_montant')}
        detail={
          etrangeres && t.mad != null ? `≈ ${montant(t.mad, 'MAD')} au cours du jour` : 'au prix du catalogue'
        }
      />
    </Indicateurs>
  )
}

/** « Ajouter une matière de ce fournisseur » : ses matières actives, sauf celles déjà là. */
function AjouterMatiere({ s, p }: { s: SaisiePreparation; p: PreparationLue }) {
  const matieres = useMatieresDuFournisseur(p.fournisseur_id)
  const dejaLa = new Set(s.lignes.map((l) => l.matiere_id))
  const options = (matieres.data ?? [])
    .filter((m) => !dejaLa.has(m.id))
    .map((m) => ({
      id: m.id,
      titre: m.reference,
      sous: [m.designation, m.devise].filter(Boolean).join(' · '),
      recherche: m.couleur ?? '',
    }))
  return (
    <Champ libelle="Ajouter une matière de ce fournisseur" className={styles.champLarge}>
      <Selecteur<number>
        valeur={null}
        options={options}
        placeholder="Référence, couleur, titrage…"
        onChange={(id) => {
          const m = matieres.data?.find((x) => x.id === id)
          if (m) s.ajouter(m)
        }}
      />
    </Champ>
  )
}

function EnTetePreparation({ s, p }: { s: SaisiePreparation; p: PreparationLue }) {
  const t = totaux(s.lignes, [])
  const place = placeRestante(t.palettes, s.parConteneur)
  return (
    <>
      <div className={styles.rangee}>
        <Champ
          libelle="Livraison prévue"
          aide={`vide : date d’envoi + ${jours(p.delai_jours)} (délai du fournisseur)`}
        >
          <DateChamp valeur={s.livraison} onChange={s.setLivraison} min={aujourdhui()} futurPermis />
        </Champ>
        <Champ
          libelle="Palettes par conteneur (aide de calcul)"
          aide="pour le calcul seulement, non enregistré"
        >
          <Nombre
            valeur={s.parConteneur}
            onChange={s.setParConteneur}
            min={0}
            decimales={0}
            placeholder="ex. 20"
            className={styles.champEtroit}
          />
        </Champ>
        <AjouterMatiere s={s} p={p} />
      </div>
      <Champ
        libelle="Remarques au fournisseur — imprimées sur le bon, qui est en anglais : les écrire en anglais"
        large
      >
        <Zone
          valeur={s.observations}
          onChange={s.setObservations}
          lignes={2}
          max={2000}
          placeholder="Deliver in one shipment, attach the certificate of origin…"
        />
      </Champ>
      {place.libres > 0 && s.parConteneur ? (
        <Note>
          {place.nombre === 1 ? 'Le conteneur' : `${nombre(place.nombre)}ᵉ conteneur`} :{' '}
          {nombre(s.parConteneur - place.libres, 0, 1)} palette(s) sur {nombre(s.parConteneur, 0, 1)} — il
          manque <strong>{nombre(place.libres, 0, 1)} palette(s)</strong> pour le remplir.
        </Note>
      ) : null}
    </>
  )
}

function Saisie({
  p,
  onFermer,
  onCree,
}: {
  p: PreparationLue
  onFermer: () => void
  onCree: (c: CommandeCreee[]) => void
}) {
  const s = useSaisiePreparation(p)
  return (
    <Fenetre
      titre={`Préparer une commande — ${p.fournisseur}`}
      sous={
        <span title="Les quantités proposées sont celles du calcul (couverture visée, minimum de commande, arrondi au conditionnement). Cochez les lignes à commander et ajustez-les dans l’unité où vous commandez : le bon est créé en brouillon, sans numéro ; il reçoit son numéro à l’envoi.">
          {[p.pays, p.contact, p.email].filter(Boolean).join(' · ')}
          {p.delai_jours ? ` · délai ${jours(p.delai_jours)}` : ''} · calcul au {date(p.date_reference)}
        </span>
      }
      taille="tresLarge"
      sale={s.sale}
      onFermer={onFermer}
      pied={<PiedPreparation s={s} fournisseurId={p.fournisseur_id} onCree={onCree} />}
    >
      <IndicateursPreparation s={s} />
      <EnTetePreparation s={s} p={p} />
      <TablePreparation lignes={s.lignes} ed={s.ed} />
    </Fenetre>
  )
}

export function Preparation({
  fournisseurId,
  onFermer,
  onCree,
}: {
  fournisseurId: number
  onFermer: () => void
  onCree: (commandes: CommandeCreee[]) => void
}) {
  const lu = usePreparation(fournisseurId)
  if (!lu.data)
    return (
      <Fenetre titre="Préparer une commande" onFermer={onFermer} taille="tresLarge">
        {lu.isError ? (
          <Erreur erreur={lu.error} onReessayer={() => void lu.refetch()} />
        ) : (
          <Chargement quoi="les quantités suggérées" />
        )}
      </Fenetre>
    )
  return <Saisie key={fournisseurId} p={lu.data} onFermer={onFermer} onCree={onCree} />
}
