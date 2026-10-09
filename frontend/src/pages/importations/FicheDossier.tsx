/**
 * La fiche d'un dossier d'importation (`/dossiers/:id?onglet=…`, ECRANS-PRO 5.6 à 5.14), en fenêtre
 * très large par-dessus la liste (ou l'écran qui l'a ouverte) : titre et badge (« Ouvert »,
 * « Clos le … », « Annulé le … »), en-tête et gestes, indicateurs, bandeaux, puis huit volets dans
 * l'adresse — familles, marchandises, frais (● si un frais est en cours de saisie), échéancier,
 * pièces jointes, second camion (si une facture attend et le dossier est ouvert), saisie à la main
 * (dossier sans facture, ouvert), historique. Un volet devenu impossible revient aux familles ; un
 * dossier à la main encore vide s'ouvre sur sa saisie. Les brouillons (frais, saisie à la main)
 * vivent ici : ils survivent au changement de volet et gardent la fenêtre.
 */
import { useState } from 'react'
import { useSearchParams } from 'react-router'

import { Historique } from '../../composants/documents/Historique'
import { PiecesJointes, type ModePieces } from '../../composants/documents/PiecesJointes'
import { Fenetre } from '../../composants/mise-en-page/Fenetre'
import { Onglets } from '../../composants/mise-en-page/Onglets'
import { Badge } from '../../composants/retour/Badge'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { Note } from '../../composants/retour/Note'
import { avecParametre } from '../../lib/adresse'
import { horodatage } from '../../lib/format'
import { useLecture } from '../../lib/requetes'
import { FRAIS_VIDE, fraisCommence, type BrouillonFrais } from './AjoutFrais'
import { EnTeteDossier } from './EnTeteDossier'
import styles from './Importations.module.css'
import { BandeauxDossier, IndicateursDossier } from './IndicateursDossier'
import { titreDossier, VOLETS, type DossierFiche, type PosteFiche, type Volet } from './types'
import { useEnregistre, useGestesDossier } from './useDossier'
import { VoletEcheancier } from './VoletEcheancier'
import { VoletFamilles } from './VoletFamilles'
import { VoletFrais } from './VoletFrais'
import { VoletMarchandises } from './VoletMarchandises'
import { mainCommencee, MAIN_VIDE, VoletSaisieMain, type BrouillonMain } from './VoletSaisieMain'
import { VoletSecondCamion } from './VoletSecondCamion'

/** Les volets présents pour ce dossier (le second camion et la saisie, seulement s'ils servent). */
export function voletsPresents(d: DossierFiche): Volet[] {
  const ouvert = d.statut === 'ouvert'
  return VOLETS.filter(
    (v) =>
      (v !== 'facture' || (ouvert && d.a_rattacher.length > 0)) && (v !== 'main' || (ouvert && d.a_la_main)),
  )
}

/** Le volet de l'adresse s'il est présent ; sinon la saisie d'un dossier à la main vide, ou les familles. */
function useVolet(d: DossierFiche) {
  const [params, setParams] = useSearchParams()
  const presents = voletsPresents(d)
  const lu = params.get('onglet')
  const defaut: Volet = presents.includes('main') && !d.lignes.length ? 'main' : 'familles'
  const actif: Volet = presents.find((v) => v === lu) ?? defaut
  const choisir = (v: Volet, q?: string) =>
    setParams((p) => avecParametre(avecParametre(p, 'onglet', v === defaut ? null : v), 'q', q ?? null), {
      replace: true,
    })
  return { presents, actif, choisir }
}

function Badges({ d }: { d: DossierFiche }) {
  if (d.statut === 'clos') return <Badge ton="ok">Clos le {horodatage(d.clos_le)}</Badge>
  if (d.statut === 'annule') return <Badge ton="neutre">Annulé le {horodatage(d.annule_le)}</Badge>
  return <Badge ton="attention">Ouvert</Badge>
}

/** Ouvert : joindre et retirer ; clos : joindre seulement (le serveur refuse le retrait) ; annulé : lecture. */
export function modePieces(statut: string): ModePieces {
  if (statut === 'ouvert') return 'complet'
  return statut === 'clos' ? 'joindre' : 'lecture'
}

const LIBELLES: Record<Volet, { libelle: string; court?: string }> = {
  familles: { libelle: 'Par famille de fil', court: 'Familles' },
  marchandises: { libelle: 'Marchandises' },
  frais: { libelle: 'Frais' },
  echeancier: { libelle: 'Échéancier' },
  pieces: { libelle: 'Pièces jointes' },
  facture: { libelle: 'Second camion de la facture', court: 'Second camion' },
  main: { libelle: 'Saisie à la main' },
  historique: { libelle: 'Historique' },
}

function compte(d: DossierFiche, v: Volet): number | null {
  if (v === 'familles') return d.familles.length
  if (v === 'marchandises') return d.lignes.length
  if (v === 'frais') return d.frais.length
  if (v === 'echeancier') return d.echeancier.length
  if (v === 'pieces') return d.nb_pieces
  if (v === 'facture') return d.a_rattacher.length
  return null
}

interface Brouillons {
  frais: BrouillonFrais
  setFrais: (b: BrouillonFrais) => void
  main: BrouillonMain
  setMain: (b: BrouillonMain) => void
}

function Contenu({
  d,
  volet,
  b,
  noter,
}: {
  d: DossierFiche
  volet: ReturnType<typeof useVolet>
  b: Brouillons
  noter: () => void
}) {
  const g = useGestesDossier(d)
  const postes = useLecture<PosteFiche[]>('/postes-frais')
  const modifiable = d.statut === 'ouvert'
  const versFrais = () => volet.choisir('frais')
  switch (volet.actif) {
    case 'marchandises':
      return <VoletMarchandises d={d} g={g} modifiable={modifiable} noter={noter} />
    case 'frais':
      return (
        <VoletFrais
          d={d}
          g={g}
          postes={postes.data ?? []}
          modifiable={modifiable}
          noter={noter}
          brouillon={b.frais}
          setBrouillon={b.setFrais}
        />
      )
    case 'echeancier':
      return <VoletEcheancier d={d} versFrais={versFrais} />
    case 'pieces':
      return (
        <div className={styles.pile}>
          <Note uneLigne="La facture du fournisseur, la déclaration en douane (DUM), le connaissement, le certificat d’origine, les factures de frais et les quittances : tout ce qui justifie le coût du dossier, même clos.">
            La facture du fournisseur, la déclaration en douane (DUM), le connaissement, le certificat
            d’origine, les factures de frais et les quittances : tout ce qui justifie le coût du dossier, même
            clos.
          </Note>
          <PiecesJointes objet="dossier" id={d.id} mode={modePieces(d.statut)} />
        </div>
      )
    case 'facture':
      return <VoletSecondCamion d={d} g={g} />
    case 'main':
      return <VoletSaisieMain d={d} g={g} b={b.main} setB={b.setMain} />
    case 'historique':
      return <Historique objet="dossier" id={d.id} />
    default:
      return <VoletFamilles d={d} presents={volet.presents} choisir={volet.choisir} />
  }
}

function Fiche({ d, onFermer }: { d: DossierFiche; onFermer: () => void }) {
  const volet = useVolet(d)
  const g = useGestesDossier(d)
  const enregistre = useEnregistre()
  const [panneau, setPanneau] = useState(false)
  const [frais, setFrais] = useState<BrouillonFrais>(FRAIS_VIDE)
  const [main, setMain] = useState<BrouillonMain>(MAIN_VIDE)
  const fraisSale = d.statut === 'ouvert' && fraisCommence(frais)
  const mainSale = d.statut === 'ouvert' && mainCommencee(main)
  return (
    <Fenetre
      taille="tresLarge"
      sale={fraisSale || mainSale}
      onFermer={onFermer}
      titre={
        <span className={styles.rangee}>
          {titreDossier(d)} <Badges d={d} />
        </span>
      }
    >
      <div className={styles.pile}>
        <EnTeteDossier
          d={d}
          g={g}
          panneau={panneau}
          basculerPanneau={() => setPanneau(!panneau)}
          enregistreA={enregistre.a}
          noter={enregistre.noter}
        />
        <IndicateursDossier d={d} versFrais={() => volet.choisir('frais')} />
        <BandeauxDossier d={d} versFrais={() => volet.choisir('frais')} />
        <Onglets
          libelle="Volets du dossier"
          actif={volet.actif}
          onChange={(v) => volet.choisir(v)}
          onglets={volet.presents.map((v) => ({
            cle: v,
            ...LIBELLES[v],
            compte: compte(d, v),
            sale: (v === 'frais' && fraisSale) || (v === 'main' && mainSale),
          }))}
        />
        <Contenu d={d} volet={volet} b={{ frais, setFrais, main, setMain }} noter={enregistre.noter} />
      </div>
    </Fenetre>
  )
}

export function FicheDossier({ id, onFermer }: { id: number; onFermer: (statut?: string | null) => void }) {
  const lu = useLecture<DossierFiche>(`/dossiers/${id}`)
  if (lu.data) return <Fiche key={lu.data.id} d={lu.data} onFermer={() => onFermer(lu.data?.statut)} />
  return (
    <Fenetre titre="Dossier d’importation" taille="tresLarge" onFermer={() => onFermer()}>
      {lu.isError ? (
        <Erreur erreur={lu.error} onReessayer={() => void lu.refetch()} />
      ) : (
        <Chargement quoi="le dossier" />
      )}
    </Fenetre>
  )
}
