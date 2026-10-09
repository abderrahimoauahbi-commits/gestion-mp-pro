# Comparaison avec Gestion MP — Année d'essai simulée (import de l'ERP Fil)

- Faite le **2026-10-09 18:34**, mode **api**.
- Gestion MP servi : `d10180e` · Gestion MP PRO : `0.1.0`.
- Source : `gestion_mp_comparaison` (copie en lecture seule) → base PRO reprise ; 2 date(s) : 2026-09-30, 2026-10-08.
- Empreinte de `gestion_mp` et de la source : inchangées (aucune écriture).
- Même base : signature de la copie `9e5934b0a949e0ed…` = signature de la dernière reprise de PRO `9e5934b0a949e0ed…` — **identique**.

## Chiffre par chiffre, par section

| Section | Valeurs comparées | Expliquées (classe) | À corriger |
| --- | ---: | --- | ---: |
| analyse du revient | 3489 | K1 324 | 0 |
| besoins | 1526 | — | 0 |
| bilan | 1438 | K1 3, K8b 3 | 0 |
| bobines | 5956 | — | 0 |
| cockpit | 1068 | K1 28 | 0 |
| commandes | 53372 | K8b 8, K8d 3, K8h 1934 | 0 |
| controles | 3585 | K1 21 | 0 |
| dossiers | 62480 | K1 3896, K8b 23 | 0 |
| factures | 2844 | — | 0 |
| inventaires | 8880 | K1 33, K8f 360 | 0 |
| matières | 4340 | K8c 2 | 0 |
| mouvements | 250512 | K8a 8747, K8g 1443, K8i 1101 | 0 |
| nomenclature | 4550 | — | 0 |
| opportunites | 1636 | K1 112 | 0 |
| ordres | 196018 | K1 208, K8d 1, K8e 319 | 0 |
| performance | 3064 | K8b 12 | 0 |
| pesées | 37700 | K8b 5, K8d 38 | 0 |
| plan-achat | 3797 | — | 0 |
| prix | 23075 | — | 0 |
| production | 9741 | K1 3 | 0 |
| receptions | 59268 | K8b 24, K8d 1 | 0 |
| soldes | 13440 | — | 0 |
| stock | 30144 | — | 0 |
| valorisation | 5232 | K1 337 | 0 |
| échéancier | 8068 | K1 35 | 0 |

## Différences voulues rencontrées (corrections et traductions déclarées)

- **K1** (5000) — Arrondi à l'échelle des colonnes (MODELE-DONNEES § 10.2) — preuve : Gestion MP recalculé sur ses données arrondies par la règle de la reprise (rejeu du moteur et des routes ; chaîne en base pour les documents).
- **K8a** (8747) — Prix des sorties, transferts, retours machine non repris (R1 n° 1).
- **K8b** (75) — Réception payée en deux devises scindée, une réception par devise (R1 n° 2, lot K8B) — preuve : le dépôt et les routes de Gestion MP relus sur sa copie scindée (même découpe, mêmes identifiants) redonnent PRO ; stocks et valeurs MAD inchangés.
- **K8c** (2) — Unité d'achat sans contenance lue au kilo (R1 n° 3).
- **K8d** (43) — Brouillon numéroté : numéro retiré, gardé au compteur (R1 n° 4).
- **K8e** (319) — Ordre validé sans date : fin de son jour (R1 n° 5).
- **K8f** (360) — Numéro de lot à blancs : blancs → « _ » (R1 n° 8).
- **K8g** (1443) — Entrée de réception de l'ERP Fil : sa réception retrouvée par (lot, date) (R1 n° 7).
- **K8h** (1934) — Prix confirmé sans date : date de création du bon (R1).
- **K8i** (1101) — Entrée en devise sans cours : cours du jour de la reprise figé (V2, V3/V4) — même cours que celui du jour de Gestion MP : aucun calcul ne change.

## Verdict

- Valeurs comparées : **795223**.
- Écarts expliqués (différences voulues) : **19024**.
- **À corriger : 0**.
