# Comparaison avec Gestion MP — Année d'essai simulée (import de l'ERP Fil)

- Faite le **2026-10-09 18:29**, mode **moteurs**.
- Gestion MP servi : `d10180e` · Gestion MP PRO : `0.1.0 (projet)`.
- Source : `gestion_mp_comparaison` (copie en lecture seule) → base PRO reprise ; 13 date(s) : 2026-10-08, 2025-10-31, 2025-11-30, 2025-12-31, 2026-01-31, 2026-02-28, 2026-03-31, 2026-04-30, 2026-05-31, 2026-06-30, 2026-07-31, 2026-08-31, 2026-09-30.
- Empreinte de `gestion_mp` et de la source : inchangées (aucune écriture).
- Même base : signature de la copie `9e5934b0a949e0ed…` = signature de la dernière reprise de PRO `9e5934b0a949e0ed…` — **identique**.

## Chiffre par chiffre, par section

| Section | Valeurs comparées | Expliquées (classe) | À corriger |
| --- | ---: | --- | ---: |
| a_la_date | 20537 | K8b 7 | 0 |
| aberrantes | 91 | — | 0 |
| achats_dates | 18538 | — | 0 |
| besoins | 13884 | — | 0 |
| cmup_par_reference | 1612 | K1 5 | 0 |
| cockpit | 2985 | — | 0 |
| cockpit_meme_couleur | 2985 | — | 0 |
| controle_recettes | 1092 | — | 0 |
| controles | 9633 | K1 91 | 0 |
| cout_matiere_annuel | 13 | — | 0 |
| couts_du_journal | 219363 | K1 27178 | 0 |
| devises_pratiquees | 169 | — | 0 |
| ecart_facture | 3354 | K1 442 | 0 |
| evolution_bobines | 40017 | — | 0 |
| fils_en_machine | 0 | — | 0 |
| historique_prix | 129766 | — | 0 |
| lots | 175170 | — | 0 |
| lots_disponibles | 7110 | — | 0 |
| negatives | 0 | — | 0 |
| nomenclature | 62205 | — | 0 |
| opportunites | 16860 | — | 0 |
| ordres | 406009 | K1 864 | 0 |
| performance_receptions | 18558 | K8b 31 | 0 |
| pesees | 255771 | K8b 58, K8d 76 | 0 |
| plan_achat | 12390 | — | 0 |
| plan_mensuel | 2808 | — | 0 |
| prix_constates | 4836 | — | 0 |
| realise | 6734 | K1 32 | 0 |
| revient | 276159 | K1 41314 | 0 |
| revient_par_lot | 0 | — | 0 |
| revient_par_reception | 276159 | K1 41314 | 0 |
| scorecard | 2652 | K8b 43 | 0 |
| stock | 128960 | — | 0 |
| stock_en_machine | 0 | — | 0 |
| synthese | 91 | — | 0 |
| tracabilite | 12603 | K8a 1092 | 0 |
| tva_attendue | 1170 | K1 1079 | 0 |
| valorisation | 20956 | K1 1300 | 0 |

## Différences voulues rencontrées (corrections et traductions déclarées)

- **K1** (113619) — Arrondi à l'échelle des colonnes (MODELE-DONNEES § 10.2) — preuve : Gestion MP recalculé sur ses données arrondies par la règle de la reprise (rejeu du moteur et des routes ; chaîne en base pour les documents).
- **K8a** (1092) — Prix des sorties, transferts, retours machine non repris (R1 n° 1).
- **K8b** (139) — Réception payée en deux devises scindée, une réception par devise (R1 n° 2, lot K8B) — preuve : le dépôt et les routes de Gestion MP relus sur sa copie scindée (même découpe, mêmes identifiants) redonnent PRO ; stocks et valeurs MAD inchangés.
- **K8d** (76) — Brouillon numéroté : numéro retiré, gardé au compteur (R1 n° 4).

## Verdict

- Valeurs comparées : **2151240**.
- Écarts expliqués (différences voulues) : **114926**.
- **À corriger : 0**.
