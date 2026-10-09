/**
 * Le réglage d'un métier (création et onglet « Réglages du métier ») : code, nom, laize d'un étage,
 * densité (bobines par mètre), nombre d'étages, en service, observations. Bornes dites à la
 * frappe ; en lecture pour les achats et l'alimentation.
 */
import { Grille } from '../../composants/mise-en-page/Grille'
import { Champ } from '../../composants/saisie/Champ'
import { Interrupteur } from '../../composants/saisie/Interrupteur'
import { Nombre } from '../../composants/saisie/Nombre'
import { Saisie } from '../../composants/saisie/Saisie'
import { Zone } from '../../composants/saisie/Zone'
import type { FormeMetier } from './formeMetier'

type Props = { f: FormeMetier; maj: (m: Partial<FormeMetier>) => void; lecture?: boolean }

/** Laize, densité, étages, état, observations. */
function ChampsMachine({ f, maj, lecture }: Props) {
  return (
    <>
      <Champ libelle="Laize d’un étage (m)" aide="Largeur utile d’un étage.">
        <Nombre
          valeur={f.laize}
          min={0}
          max={100}
          decimales={2}
          unite="m"
          desactive={lecture}
          onChange={(laize) => maj({ laize })}
        />
      </Champ>
      <Champ libelle="Densité (bobines par mètre)" aide="320 = 320 bobines par mètre de laize monté.">
        <Nombre
          valeur={f.bobines_par_metre}
          min={0}
          max={100000}
          decimales={2}
          desactive={lecture}
          onChange={(bobines_par_metre) => maj({ bobines_par_metre })}
        />
      </Champ>
      <Champ libelle="Nombre d’étages" aide="De 1 à 40 ; six ou huit selon la machine.">
        <Nombre
          valeur={f.etages}
          min={1}
          max={40}
          decimales={0}
          desactive={lecture}
          onChange={(etages) => maj({ etages })}
        />
      </Champ>
      <Champ groupe libelle="État">
        <Interrupteur
          valeur={f.actif}
          desactive={lecture}
          libelle="Métier en service (un métier arrêté ne compte pas dans le stock)"
          onChange={(actif) => maj({ actif })}
        />
      </Champ>
      <Champ libelle="Observations" large>
        <Zone
          valeur={f.commentaire}
          max={2000}
          lignes={2}
          desactive={lecture}
          onChange={(commentaire) => maj({ commentaire })}
        />
      </Champ>
    </>
  )
}

export function ChampsMetier({
  f,
  maj,
  lecture,
}: {
  f: FormeMetier
  maj: (m: Partial<FormeMetier>) => void
  lecture?: boolean
}) {
  return (
    <Grille colonnes={2}>
      <Champ libelle="Code" obligatoire aide="Le repère court, utilisé dans les ordres et les contrôles.">
        <Saisie valeur={f.code} max={32} desactive={lecture} onChange={(code) => maj({ code })} />
      </Champ>
      <Champ libelle="Nom" aide="Celui qu’on emploie à l’atelier.">
        <Saisie
          valeur={f.nom}
          max={120}
          placeholder="Métier du fond, Van de Wiele n° 2…"
          desactive={lecture}
          onChange={(nom) => maj({ nom })}
        />
      </Champ>
      <ChampsMachine f={f} maj={maj} lecture={lecture} />
    </Grille>
  )
}
