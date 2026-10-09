/**
 * Volet « Achat » de la fiche matière (direction, achats ; jamais montré à l'alimentation) :
 * fournisseur, prix dans son unité (au kilo par défaut, ou au mètre ramené au kilo par la
 * densité — le stock et tous les calculs sont au kilo), devise, unité d'achat (liste fermée sans
 * « ml », vide = déduite), contenance, minimum de commande, code douanier.
 */
import { Grille } from '../../composants/mise-en-page/Grille'
import { Champ } from '../../composants/saisie/Champ'
import { Nombre } from '../../composants/saisie/Nombre'
import { ChampDensite } from './ChampDensite'
import { Prix } from '../../composants/saisie/Prix'
import { Segments } from '../../composants/saisie/Segments'
import { Selecteur } from '../../composants/saisie/Selecteur'
import { jours, kg, part } from '../../lib/format'
import { BORNES_MATIERE } from './bornes'
import { UNITES_ACHAT, uniteDeduite, type FormeMatiere } from './formeMatiere'
import styles from './catalogue.module.css'
import type { Classification, CodeDouanier, Devise, Fournisseur } from './types'

export interface VoletAchatProps {
  forme: FormeMatiere
  maj: (modif: Partial<FormeMatiere>) => void
  c: Classification
  fournisseurs: readonly Fournisseur[]
  devises: readonly Devise[]
  codes: readonly CodeDouanier[] | null
  creation: boolean
}

function ChampFournisseur({ forme, maj, fournisseurs, creation }: VoletAchatProps) {
  const choisi = fournisseurs.find((f) => f.id === forme.fournisseur_id)
  const options = fournisseurs
    .filter((f) => f.actif || f.id === forme.fournisseur_id)
    .sort((a, b) => a.nom.localeCompare(b.nom, 'fr'))
    .map((f) => ({
      id: f.id,
      titre: f.pays ? `${f.nom} (${f.pays})` : f.nom,
      sous: f.actif ? undefined : 'désactivé',
    }))
  const aide = choisi
    ? `${choisi.pays || 'MAROC'} · délai ${jours(choisi.delai_jours)} · devise par défaut ${choisi.devise}`
    : 'obligatoire pour une matière en service : le plan d’achat sait ainsi à qui la commander'
  return (
    <Champ libelle="Fournisseur" obligatoire={forme.actif} aide={aide}>
      <Selecteur<number>
        valeur={forme.fournisseur_id}
        options={options}
        onChange={(id) => {
          const f = fournisseurs.find((x) => x.id === id)
          maj(creation && f ? { fournisseur_id: id, devise: f.devise } : { fournisseur_id: id })
        }}
        placeholder="— aucun —"
      />
    </Champ>
  )
}

const UNITES_PRIX = [
  { valeur: 'kg', libelle: 'au kilo', titre: 'Le prix se dit au kilo (défaut)' },
  { valeur: 'ml', libelle: 'au mètre', titre: 'Le prix se dit au mètre : ramené au kilo par la densité' },
] as const

function ChampsPrix({ forme, maj, c, devises }: VoletAchatProps) {
  const role = c.roles.find((r) => r.id === forme.role_id)
  const options = devises
    .filter((d) => d.actif || d.code === forme.devise)
    .map((d) => ({ id: d.code, titre: `${d.code} — ${d.nom}` }))
  return (
    <>
      <Champ
        libelle="Prix d’achat"
        aide={
          forme.unite_prix === 'ml'
            ? 'au mètre : saisir la densité pour le ramener au kilo'
            : 'le stock et tous les calculs sont au kilo ; le dernier prix confirmé d’une commande s’y inscrit'
        }
      >
        <div className={styles.rangee}>
          <Prix
            valeur={forme.prix}
            onChange={(v) => maj({ prix: v })}
            devise={forme.devise}
            unite={forme.unite_prix}
            densite={forme.densite}
          />
          <Segments<'kg' | 'ml'>
            libelle="Unité du prix"
            valeur={forme.unite_prix}
            onChange={(u) => maj({ unite_prix: u })}
            options={UNITES_PRIX}
          />
        </div>
      </Champ>
      {forme.unite_prix === 'ml' && !role?.lineaire ? (
        <ChampDensite
          valeur={forme.densite}
          onChange={(v) => maj({ densite: v })}
          aide="obligatoire pour un prix au mètre : il se ramène au kilo par elle"
        />
      ) : null}
      <Champ libelle="Devise" aide="celle du prix ; un bon de commande par devise">
        <Selecteur<string>
          valeur={forme.devise}
          options={options}
          onChange={(d) => maj({ devise: d ?? 'MAD' })}
          effacable={false}
        />
      </Champ>
    </>
  )
}

function ChampsUnite({ forme, maj }: VoletAchatProps) {
  const deduite = uniteDeduite(forme)
  const libelleDeduite = deduite.unite === 'kg' ? 'le kilo' : `${deduite.unite} (${kg(deduite.contenance)})`
  const unite = forme.unite_achat.trim()
  const options = [...new Set([...UNITES_ACHAT, unite].filter((u) => u && u.toLowerCase() !== 'ml'))].map(
    (u) => ({
      id: u,
      titre: u,
    }),
  )
  return (
    <>
      <Champ
        libelle="Unité d’achat"
        aide={
          unite
            ? 'déclarée : le plan d’achat commande dans cette unité'
            : `vide = déduite : ${libelleDeduite} — palette si bobine et bobines par palette, sinon bobine, sinon kilo`
        }
      >
        <Selecteur<string>
          valeur={unite || null}
          options={options}
          onChange={(u) => maj({ unite_achat: u ?? '', contenance_achat: u ? forme.contenance_achat : null })}
          placeholder={`déduite : ${deduite.unite === 'kg' ? 'kilo' : deduite.unite}`}
        />
      </Champ>
      {unite ? (
        <Champ
          libelle={`Contenance (kg par ${unite.toLowerCase()})`}
          obligatoire
          aide="obligatoire pour une unité déclarée : une colle en fûts de 200 kg se déclare, elle ne se devine pas"
        >
          <Nombre
            valeur={forme.contenance_achat}
            onChange={(v) => maj({ contenance_achat: v })}
            min={0}
            max={BORNES_MATIERE.contenance_achat[1]}
            decimales={3}
            unite="kg"
          />
        </Champ>
      ) : null}
      <Champ libelle="Minimum de commande" aide="le plan d’achat ne proposera jamais moins">
        <Nombre
          valeur={forme.minimum_commande}
          onChange={(v) => maj({ minimum_commande: v })}
          min={0}
          max={BORNES_MATIERE.minimum_commande[1]}
          decimales={3}
          unite="kg"
        />
      </Champ>
    </>
  )
}

function ChampCode({ forme, maj, codes }: VoletAchatProps) {
  const choisi = codes?.find((x) => x.id === forme.code_douanier_id)
  const options = (codes ?? [])
    .filter((x) => x.actif || x.id === forme.code_douanier_id)
    .map((x) => ({ id: x.id, titre: `${x.code} — ${x.libelle} (${part(x.taux_droits)})` }))
  return (
    <Champ
      libelle="Code douanier"
      aide={
        codes == null
          ? 'liste des codes douaniers indisponible : réessayer plus tard'
          : choisi
            ? `${choisi.libelle} · droits ${part(choisi.taux_droits)}`
            : 'sert à prévoir et vérifier les droits de douane d’un dossier d’importation'
      }
    >
      <Selecteur<number>
        valeur={forme.code_douanier_id}
        options={options}
        onChange={(id) => maj({ code_douanier_id: id })}
        placeholder="Taper : 5402, fils de PP…"
        desactive={codes == null}
      />
    </Champ>
  )
}

export function VoletAchat(p: VoletAchatProps) {
  return (
    <div className={styles.volet}>
      <Grille colonnes={2}>
        <ChampFournisseur {...p} />
        <ChampsPrix {...p} />
        <ChampsUnite {...p} />
        <ChampCode {...p} />
      </Grille>
    </div>
  )
}
