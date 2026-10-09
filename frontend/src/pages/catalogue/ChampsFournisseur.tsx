/**
 * Les champs de la fiche fournisseur, en trois blocs alignés : identité et contact,
 * approvisionnement (délai, couverture, devise, incoterm, port), paiement. Bornes et longueurs du
 * serveur à la frappe.
 */
import { useState } from 'react'

import { Grille } from '../../composants/mise-en-page/Grille'
import { Bouton } from '../../composants/saisie/Bouton'
import { Champ } from '../../composants/saisie/Champ'
import { Nombre } from '../../composants/saisie/Nombre'
import { Saisie } from '../../composants/saisie/Saisie'
import { Selecteur } from '../../composants/saisie/Selecteur'
import { Zone } from '../../composants/saisie/Zone'
import { DELAI_MAX, LONGUEURS, NOTES_MAX } from './bornes'
import styles from './catalogue.module.css'
import { INCOTERMS, MODES_PAIEMENT, type FormeFournisseur } from './formeFournisseur'
import type { Devise } from './types'

export interface ChampsFournisseurProps {
  forme: FormeFournisseur
  maj: (modif: Partial<FormeFournisseur>) => void
  /** Les pays déjà employés (la liste proposée). */
  pays: readonly string[]
  devises: readonly Devise[]
}

const AUTRE = '__autre__'
const liste = (valeurs: readonly string[], actuelle: string) =>
  [...new Set([...valeurs, actuelle].filter(Boolean))].map((v) => ({ id: v, titre: v }))

function ChampPays({ forme, maj, pays }: ChampsFournisseurProps) {
  const [autre, setAutre] = useState(false)
  if (autre)
    return (
      <Champ libelle="Pays" aide="un pays absent de la liste, écrit en majuscules">
        <div className={styles.rangee}>
          <Saisie
            valeur={forme.pays}
            onChange={(v) => maj({ pays: v.toUpperCase() })}
            max={LONGUEURS.PAYS}
            autoFocus
          />
          <Bouton
            taille="petit"
            variante="fantome"
            titre="Revenir à la liste des pays"
            onClick={() => setAutre(false)}
          >
            Liste
          </Bouton>
        </div>
      </Champ>
    )
  return (
    <Champ libelle="Pays" aide="MAROC ou vide : fournisseur local">
      <Selecteur<string>
        valeur={forme.pays || null}
        options={[...liste(pays, forme.pays), { id: AUTRE, titre: 'Autre pays…' }]}
        onChange={(v) => (v === AUTRE ? setAutre(true) : maj({ pays: v ?? '' }))}
        placeholder="— (MAROC)"
      />
    </Champ>
  )
}

export function BlocIdentite(p: ChampsFournisseurProps) {
  const { forme, maj } = p
  return (
    <Grille colonnes={3}>
      <Champ libelle="Nom" obligatoire>
        <Saisie
          valeur={forme.nom}
          onChange={(v) => maj({ nom: v })}
          max={LONGUEURS.NOM_FOURNISSEUR}
          autoFocus
        />
      </Champ>
      <Champ libelle="Code" aide="abréviation interne, facultative">
        <Saisie valeur={forme.code} onChange={(v) => maj({ code: v })} max={LONGUEURS.CODE_FOURNISSEUR} />
      </Champ>
      <ChampPays {...p} />
      <Champ libelle="Contact">
        <Saisie valeur={forme.contact} onChange={(v) => maj({ contact: v })} max={LONGUEURS.CONTACT} />
      </Champ>
      <Champ libelle="Téléphone">
        <Saisie
          valeur={forme.telephone}
          onChange={(v) => maj({ telephone: v })}
          type="tel"
          max={LONGUEURS.TELEPHONE}
        />
      </Champ>
      <Champ libelle="E-mail">
        <Saisie
          valeur={forme.email}
          onChange={(v) => maj({ email: v })}
          type="email"
          max={LONGUEURS.EMAIL_FOURNISSEUR}
        />
      </Champ>
    </Grille>
  )
}

export function BlocApprovisionnement({ forme, maj, devises }: ChampsFournisseurProps) {
  const options = devises
    .filter((d) => d.actif || d.code === forme.devise)
    .map((d) => ({ id: d.code, titre: `${d.code} — ${d.nom}` }))
  return (
    <Grille colonnes={3}>
      <Champ
        libelle="Délai"
        obligatoire
        aide="de la commande à l’arrivée à l’usine : il règle le stock projeté"
      >
        <Nombre
          valeur={forme.delai_jours}
          onChange={(v) => maj({ delai_jours: v })}
          min={1}
          max={DELAI_MAX}
          decimales={0}
          unite="j"
        />
      </Champ>
      <Champ libelle="Couverture" aide="jours de besoin couverts par une commande ; 0 = le réglage général">
        <Nombre
          valeur={forme.couverture_commande_jours}
          onChange={(v) => maj({ couverture_commande_jours: v })}
          min={0}
          max={DELAI_MAX}
          decimales={0}
          unite="j"
        />
      </Champ>
      <Champ
        libelle="Devise par défaut"
        aide="pré-remplit une nouvelle matière ; chaque prix garde la sienne"
      >
        <Selecteur<string>
          valeur={forme.devise}
          options={options}
          onChange={(d) => maj({ devise: d ?? 'MAD' })}
          effacable={false}
        />
      </Champ>
      <Champ libelle="Incoterm">
        <Selecteur<string>
          valeur={forme.incoterm || null}
          options={liste(INCOTERMS, forme.incoterm)}
          onChange={(v) => maj({ incoterm: v ?? '' })}
          placeholder="—"
        />
      </Champ>
      <Champ libelle="Port de chargement" aide="d’où part la marchandise : Mersin, Ningbo…">
        <Saisie
          valeur={forme.port_chargement}
          onChange={(v) => maj({ port_chargement: v })}
          max={LONGUEURS.PORT}
        />
      </Champ>
    </Grille>
  )
}

export function BlocPaiement({ forme, maj }: ChampsFournisseurProps) {
  return (
    <Grille colonnes={3}>
      <Champ libelle="Mode de paiement">
        <Selecteur<string>
          valeur={forme.mode_paiement || null}
          options={liste(MODES_PAIEMENT, forme.mode_paiement)}
          onChange={(v) => maj({ mode_paiement: v ?? '' })}
          placeholder="—"
        />
      </Champ>
      <Champ libelle="Délai de paiement" aide="sert au calcul du crédit fournisseur">
        <Nombre
          valeur={forme.delai_paiement_jours}
          onChange={(v) => maj({ delai_paiement_jours: v })}
          min={0}
          max={DELAI_MAX}
          decimales={0}
          unite="j"
        />
      </Champ>
      <Champ libelle="Banque" aide="la domiciliation du paiement">
        <Saisie valeur={forme.banque} onChange={(v) => maj({ banque: v })} max={LONGUEURS.BANQUE} />
      </Champ>
      <Champ libelle="Conditions" large>
        <Saisie
          valeur={forme.conditions_paiement}
          onChange={(v) => maj({ conditions_paiement: v })}
          max={LONGUEURS.CONDITIONS_PAIEMENT}
          placeholder="30 % à la commande, solde à l’expédition…"
        />
      </Champ>
      <Champ libelle="Observations" large>
        <Zone valeur={forme.notes} onChange={(v) => maj({ notes: v })} max={NOTES_MAX} lignes={2} />
      </Champ>
    </Grille>
  )
}
