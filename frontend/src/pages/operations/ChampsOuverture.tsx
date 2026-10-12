/**
 * La quantité, le prix et la devise d'un stock d'ouverture (la ligne d'ajout, `EncartLigne`).
 */
import { Champ } from '../../composants/saisie/Champ'
import { Prix } from '../../composants/saisie/Prix'
import { Quantite } from '../../composants/saisie/Quantite'
import { Selecteur } from '../../composants/saisie/Selecteur'
import { prixUnite } from '../../lib/format'
import type { Encart, EncartProps } from './EncartLigne'
import styles from './Operations.module.css'

/**
 * Quantité (en kg, bobines ou palettes selon le conditionnement de la matière : le lot créé le
 * reprend), prix au kilo et devise d'un stock d'ouverture.
 */
export function ChampsOuverture({ p, x }: { p: EncartProps; x: Encart }) {
  const { e, poser, m } = x
  return (
    <>
      <Champ libelle="Quantité" groupe>
        <Quantite
          libelle="Quantité"
          kg={e.kg}
          onChange={(v) => poser({ kg: v })}
          unite={e.unite}
          onUnite={(unite) => poser({ unite })}
          poidsBobine={m?.poids_bobine}
          bobinesPalette={m?.bobines_palette}
          kgParMl={m?.kg_par_ml}
        />
      </Champ>
      <Champ
        libelle="Prix d’achat / kg"
        groupe
        aide={m?.prix_kg != null ? `catalogue : ${prixUnite(m.prix_kg, m.devise ?? 'MAD', 'kg')}` : undefined}
      >
        <span className={styles.prixDevise}>
          <Prix
            libelle="Prix d’achat / kg"
            valeur={e.prix}
            onChange={(v) => poser({ prix: v })}
            devise={e.devise}
            unite="kg"
          />
          <Selecteur
            libelle="Devise"
            effacable={false}
            valeur={e.devise}
            options={p.devises
              .filter((d) => d.actif || d.code === e.devise)
              .map((d) => ({ id: d.code, titre: d.code, sous: d.nom }))}
            onChange={(id) => poser({ devise: id ?? 'MAD' })}
          />
        </span>
      </Champ>
    </>
  )
}
