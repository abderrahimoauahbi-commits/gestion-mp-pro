# Héritage — les essais automatiques de Gestion MP

Inventaire exhaustif de `~/gestion-mp/tests/` (état du 8 octobre 2026, commit `959aefc`) : chaque
essai, ce qu'il prouve, ses données et ses valeurs attendues clés. But : que Gestion MP PRO
**reprenne chaque preuve** (portée ou réécrite) et l'étende (voir `PLAN-DE-RECETTE-PRO.md`).

## 0. Vue d'ensemble

| | Valeur |
|---|---|
| Fichiers d'essais | 24 (`test_*.py`) + `conftest.py` |
| Lignes | 6 975 |
| Fonctions d'essai | **292** |
| Cas exécutés | **298** (2 paramétrages : `inactif` ×2, `M80` ×6) — `CONFORMITE.md` annonce 297 |
| Essais sautés selon le poste | 2 : `test_parite` (ERP Fil absent), `test_restaurer_depuis_l_ecran…` (pg_restore absent) |
| Essais d'écran (vitest, etc.) | **0** — l'écran de Gestion MP n'a aucun test automatique (seulement `eslint` via `npm run controle`) |
| Base | PostgreSQL `gestion_mp_essai`, schéma détruit et recréé à chaque séance |

### Répartition par domaine

| # | Domaine | Essais |
|---|---|---|
| 1 | Sécurité, droits, sessions, prix masqués | 12 |
| 2 | Référentiels (fournisseurs, matières, classification, qualités et recettes, métiers, magasins, pièces jointes) | 26 |
| 3 | Matières au mètre (kg / ml) et migration « stock en kilos » | 19 |
| 4 | Commandes et approbation | 23 |
| 5 | Réceptions, quarantaine, réclamations | 31 |
| 6 | Performance fournisseurs (ponctualité, complétude, OTIF, score) | 13 |
| 7 | Factures et échéancier | 5 |
| 8 | Importations (dossiers, frais, douane, coût de revient) | 39 |
| 9 | Stock, atelier, inventaires, lots, traçabilité | 36 |
| 10 | Valorisation (CMUP), dates passées, période close | 27 |
| 11 | Plan d'achat, besoins, production | 28 |
| 12 | Pilotage : cockpit, contrôles, analyse, bilan, journal, exports, réglages | 27 |
| 13 | Vérification transversale (vérificateur, parité ERP Fil, restauration) | 6 |
| | **Total** | **292** |

Par nature (un essai peut en avoir plusieurs) : règle métier ≈ 150, calcul chiffré ≈ 95, refus
(422/409) ≈ 120 essais en contiennent au moins un, droits (403/401) ≈ 30, concurrence (fils
parallèles, verrous) **9**, migration (étapes de schéma) **3**, documents et exports ≈ 25.

### Légende des tableaux

Nature : **R** règle métier · **C** calcul chiffré · **X** refus (422/409/400) · **D** droits
(401/403, prix masqués) · **P** concurrence (plusieurs postes, verrous) · **M** migration / reprise ·
**E** export, impression · **S** essai « de fumée » (répond 200, sans chiffre).
Moteur = essai sur `gestion_mp.calcul.moteur` avec des `Donnees` écrites à la main (sans base) ;
API = essai par `TestClient` sur la base d'essai.

## 1. Le socle des essais (`conftest.py`) — à reproduire dans PRO

- `GESTION_MP_BASE` forcée à `postgresql+psycopg:///gestion_mp_essai` ; **assertion** que le nom finit
  par `_essai` (« jamais sur la vraie base ») ; `GESTION_MP_TACHES=0` (pas de tâches planifiées).
- Une fixture `app` de **session** : `DROP SCHEMA public CASCADE; CREATE SCHEMA public`, puis
  `initialiser()` (migrations + données de base : magasins « Stock courant » et « Quarantaine »,
  devises, postes de frais système TPI/ASSUR/DD/TVA/FRET…), puis 3 comptes :
  `direction`/`direction-1`, `achats`/`achats-12`, `alimentation`/`1234`.
- `client_de(app, role)` : `TestClient` avec l'en-tête anti-CSRF `X-Gestion-MP: 1`, connecté par
  `POST /api/connexion`. Fixtures de session `direction`, `achats`, `alimentation`, `anonyme`.
- `ok(r, code=200)` : vérifie le code et rend le JSON.
- **Une seule base pour toute la séance** : chaque module crée ses propres fournisseurs et matières à
  préfixe unique (`ACHAT ESSAI`, `A2 ESSAI`, `CR ESSAI`, `Z2`, `E `, `V2`, `VALO`, `IMP`, `MIG`…) ; les
  réglages globaux modifiés (seuil d'approbation, tolérance de retard, date de clôture, cours des
  devises) sont **remis dans un `finally`**. L'ordre compte : `test_zz_*` passent en dernier (le
  vérificateur juge tout ce que les autres ont écrit).
- Outils d'essai employés : `monkeypatch` (injecter une faute dans le moteur, ralentir une fonction
  pour provoquer une course, rediriger `config.PIECES`), `threading.Barrier` (départ simultané),
  `pg_advisory_lock` tenu par une autre connexion, écritures SQL directes « hors chemin » pour
  fabriquer une incohérence que les contrôles doivent voir.

---

## 2. Domaine 1 — Sécurité, droits, sessions, prix masqués (12)

| Essai | Nat. | Ce qu'il prouve | Données → attendus clés |
|---|---|---|---|
| `test_parcours::test_tout_est_ferme_sans_connexion` | D | Toute route GET de l'OpenAPI répond 401 sans session, sauf 6 publiques | Publiques : `/api/etat`, `/api/visages`, `/api/installation`, `/api/connexion`, `/api/deconnexion`, `/api/sante` ; paramètres `{aid…uid}` remplacés par 1 → chaque autre GET = **401** |
| `test_parcours::test_une_ecriture_sans_entete_est_refusee` | D | Protection CSRF : une écriture sans `X-Gestion-MP` est refusée même connecté | Direction connectée sans l'en-tête, `POST /api/fournisseurs` → **403** |
| `test_parcours::test_chacun_a_sa_place` | D | Périmètre de chaque rôle | Alimentation : `POST articles`, `POST commandes`, `POST operations` (ajustement), `GET utilisateurs` → 403. Achats : `GET utilisateurs`, `PUT parametres`, `PUT qualites/{id}/recette` → 403 ; `POST bons/0/valider` → 403/404 |
| `test_parcours::test_l_atelier_ne_lit_pas_le_pilotage_des_achats` | D | « Ce que le menu cache, le serveur le refuse » | Alimentation → 403 sur cockpit, plan-achat, valorisation, prix/matrice, prix/historique, opportunites, controles, fournisseurs/performance, receptions/pesees, analyse/revient, export/pilotage, controles/soldes ; **200** sur stock, soldes, lots, bons, production/plan |
| `test_achats::test_l_atelier_ne_lit_ni_commandes_ni_receptions` | D | L'atelier ne voit ni bons ni réceptions | Alimentation → 403 sur commandes, receptions, factures, export/commandes, export/receptions, …/pesees, …/bobines |
| `test_exports::test_l_alimentation_n_exporte_pas_un_bon` | D | Seuls achats et direction sortent un bon | Alimentation → 403 ; direction → 200 ; bon inexistant 999999 → **404** |
| `test_exports::test_rien_ne_s_exporte_sans_connexion` | D | Exports fermés aux anonymes | export/pilotage, export/mouvements, export/bon-de-commande/{id} → 401 |
| `test_direction::test_l_etat_du_serveur_est_reserve_a_la_direction` | D | État du serveur : direction seule | `version`, `schema`, base `*_essai` de taille > 0, dossier des sauvegardes, sessions (contient « Direction ») ; achats → 403 |
| `test_referentiels_complets::test_l_alimentation_ne_voit_aucun_prix` | D | Prix masqués par le serveur (référentiels) | `GET articles` alimentation : `prix` = None (achats : 2,5) ; `GET qualites` : `cout_m2_mad`, `prix_kg`, `prix` = None ; `qualites/facteurs-cout` → 403 |
| `test_stock_atelier::test_alimentation_ne_voit_aucun_prix` | D | Prix masqués (stock, journal, lots, opérations, export) | `stock` : `prix_kg`, `prix_unite`, `montant_a_commander_mad` = None, `action` = "" ; `mouvements?avec_valeur` : `prix`, `valeur_mad` = None ; `lots/{id}` et `operations?type=ouverture` sans prix ; export mouvements sans colonne « Prix » |
| `test_audit2_pilotage::test_la_nomenclature_ne_donne_aucun_prix_a_l_alimentation` | D | Dernière fuite fermée (audit G5) | `nomenclature` alimentation : `prix`, `devise`, `prix_kg` vides ; achats : `A2 POIL` prix 2,5 |
| `test_zz_restauration::test_des_echecs_de_connexion_simultanes_ne_font_pas_d_erreur` | P D | 16 mauvais codes en parallèle (8 fils) : jamais de 500, compteur juste | Codes ∈ {401, 429} ; `Tentative('achats').echecs ≥ 5` ; puis compteur supprimé |

Droits vérifiés **à l'intérieur** d'autres essais (à ne pas perdre) : approuver/renvoyer réservé à la
direction (`test_achats`), plan de production écrit par la direction seule (`test_production_plan`),
postes de frais et codes douaniers par la direction (`test_importations`), rôles de classification
par la direction (`test_referentiels_complets`), libération de quarantaine par les achats seuls
(`test_stock_atelier`), validation d'ordres refusée aux achats (`test_brouillons_a_valider…`),
réclamations et pièces de dossier fermées à l'alimentation (`test_suivi`, `test_importations`), journal
et export du journal à la direction (`test_direction`), montage d'étages refusé aux achats, réglage
d'un métier refusé à l'alimentation (`test_referentiels_complets`), valeur d'inventaire masquée à
l'alimentation (`test_valorisation`).

## 3. Domaine 2 — Référentiels (26)

| Essai | Nat. | Ce qu'il prouve | Données → attendus clés |
|---|---|---|---|
| `test_referentiels::test_classer_le_catalogue_lit_les_references` | R D | Le classement automatique lit la référence, l'aperçu n'écrit rien, l'application écrit une fois | « PP FRZ-2900 Dtex-Red 7612-Hs » → composition PP, type FRZ, titrage « 2900 Dtex », couleur Rouge ; seconde lecture : plus rien à proposer ; alimentation → 403 |
| `test_referentiels::test_une_matiere_en_service_a_un_fournisseur` | X | Matière sans fournisseur refusée | 422, message cite « fournisseur » |
| `test_referentiels_complets::test_composition_detaillee_et_commentaire` | R | Listes de classification : composition détaillée, commentaire, désactivation, suppression | PPX « 100 % polypropylène » ; type_fil, titrage, couleur avec commentaire ; actif=False conservé |
| `…::test_les_roles_se_tiennent_par_la_direction` | R X D | Rôles de recette : création (direction), seuls Cuir/Franges/Ruban peuvent être « au mètre », doublon insensible à la casse, rôle de base intouchable, rôle porté insupprimable | achats → 403 ; « Galon » linéaire → 422 « au mètre » ; « velours » après « Velours » → 409 ; renommer/supprimer « Poil » → 409 ; rôle porté par une matière → 409 |
| `…::test_fournisseur_port_banque_empreinte` | R P X | Champs port/banque ; compteurs `articles`=3, `devises`={USD:1, MAD:2} ; **verrou optimiste par empreinte** ; suppression refusée avec matières | Mise à jour avec l'empreinte lue → OK, nouvelle empreinte ; second poste parti de l'ancienne → **409 « entre-temps »** ; DELETE → 409 |
| `…::test_matiere_conditionnement_et_historique` | R | Conditionnement déduit ou déclaré, verrou `version` | Poil 2 kg × 100 bobines → `{Palette, 200, declare False}` ; Carton 25 déclaré ; unité vide → redevient déduite (Palette) |
| `…::test_code_douanier_verifie` | X | Code douanier inconnu refusé | « 9999.99 » → 422 « Code douanier inconnu » ; « 5607.41.00 » accepté |
| `…::test_une_matiere_avec_historique_ne_se_supprime_pas` | X | Matière qui a des opérations : insupprimable, et le dit | `historique` True, raison « opérations » ; DELETE → 409 |
| `…::test_qualite_empreinte_doublon_suppression` | R C X D | Empreinte sur la recette, code unique, kg/m² et coût au m² | Poids Poil 1,2 + Trame 0,4 → **kg_m2 = 1,6** ; `cout_m2_mad = Σ kg_m2 × prix_kg × taux × perte` ; ancienne empreinte → 409 ; code doublon → 409 « existe déjà » ; suppression achats → 403, direction OK |
| `…::test_monter_un_etage_au_telephone` | C X D P | Montage d'un étage : effet sur le stock, journal, poids et bobines du métier, laize, empreinte d'étage | Métier laize 4, densité 10, 3 étages ; 2 m de poil (2 kg/bobine) → stock **avant 0, après 40, écart +40** ; étage 2 : 1,5 m à 50 % → poids = 2×10×2 + 1,5×10×2×0,5 = **55**, bobines **27,5** ; 5 m → 422 laize ; 0 m → 422 ; cuir (au mètre) → 422 ; empreinte périmée → 409 ; achats → 403 |
| `…::test_deplacer_un_fil_d_etage_au_bureau` | R P | Déplacement de fils, empreinte des fils | Étages [1,3] après ; réemploi de l'ancienne empreinte → 409 |
| `…::test_poids_de_bobine_mesure` | C | Le fil monté se pèse au poids mesuré du lot (M43), pas au catalogue | Réception 230 kg, 1 palette (100 bobines) → **2,3 kg/bobine**, écart 0,15 hors tolérance ; `moteur.stock_en_machine` = poids affiché |
| `…::test_regler_et_supprimer_un_metier` | X D P | Réglages d'un métier | Alimentation → 403 ; réduire à 2 étages alors que l'étage 3 est garni → 422 ; laize 1 → 422 ; empreinte périmée → 409 ; suppression avec fils → 409 ; code doublon → 409 |
| `…::test_magasin_contenu` | X | Les magasins système ne se renomment/retypent pas | Renommer en « Quarantaine » / type → 409 |
| `…::test_delai_mesure` | C (faible) | Délai mesuré absent sans commande | `delai_mesure_jours` None, `livraisons_mesurees` 0 |
| `…::test_une_piece_jointe_garde_sa_fiche` | X | Une pièce jointe retient sa matière et son fournisseur | Suppression → 409 « l'en retirer d'abord », puis « pièces jointes » ; compteur `pieces`=1 |
| `…::test_les_exports_des_referentiels` | E D S | Exports matières, fiches fournisseurs, qualités | Classeur (signature `PK`) ; alimentation → 403 |
| `…::test_un_cuir_se_saisit_en_metres_dans_la_recette` | C R | Recette d'un cuir en ml/m², motif au journal | 3 MAD/ml, densité 0,05 → **60 MAD/kg** ; 2 ml/m² → **0,1 kg/m²** ; coût = 2 × 3 × 1,02 = **6,12 MAD/m²** ; journal finit par le motif |
| `…::test_un_pays_s_ecrit_d_une_seule_facon` | R | Normalisation du pays | « turkey » → **TURKEY** |
| `test_zz_restauration::test_une_classification_laissee_vide_n_est_pas_une_erreur` | R | Classification vide = NULL, pas une erreur | composition "" → None |
| `test_suivi::test_une_piece_jointe_se_depose_et_se_relit` | R X | Dépôt et relecture ; extension dangereuse refusée | PDF relu octet pour octet ; `.exe` → 422 |
| `test_suivi::test_chaque_recette_enregistree_garde_sa_version` | R | Versions de recette avec auteur | Lignes [{VERSION POIL, Poil, 100}], par « Direction » |
| `test_parcours::test_une_recette_fausse_ne_s_enregistre_pas` | X | Rôle à 100 % | 60 + 30 → 422 « 100 % » |
| `test_audit2_atelier::test_revenir_a_une_version_remet_parts_et_poids` | R X | Restauration de version : parts **et** poids ; motif obligatoire | Poil 1,0 → 1,3 → restaurer : 1,0 ; une seule version de plus ; motif vide → 422 ; version 999999 → 404 |
| `test_audit2_atelier::test_une_recette_acceptee_n_est_pas_bloquante_le_lendemain` | C X | Tolérance d'arrondi identique à l'enregistrement et au contrôle | 99,995 % accepté et conforme ; 99,9 % → 422 « 100 % » |
| `test_plan_besoins::test_une_recette_qui_oublie_un_role_est_refusee_et_l_atelier_est_prevenu` | X R | Recette qui oublie un rôle pesé refusée ; poids sans matière signalé | 422 « oublie le rôle Franges » ; poids Trame 0,5 ajouté → avertissement, et `recettes_incompletes` de la proposition le dit ; Trame 0 → liste vide |

## 4. Domaine 3 — Matières au mètre et stock en kilos (19)

Décision du 8 octobre 2026 : stock **en kilos** pour toutes les matières ; prix au kilo (défaut) ou au
mètre (`prix_kg = prix ÷ densité`) ; recette des rôles Cuir/Franges/Ruban en ml/m² ; mètres indicatifs.

| Essai | Nat. | Ce qu'il prouve | Données → attendus clés |
|---|---|---|---|
| `test_matieres_au_metre::test_le_prix_au_metre_se_ramene_au_kilo` | C | `prix_kg`, `kg_par_ml` | Cuir 0,5 MAD/ml, 0,014 kg/ml → **35,714 MAD/kg** ; bande 2,5 USD/ml, 0,005 → **500** ; au mètre sans densité → 0 (C15) ; poil `kg_par_ml` 0 ; franges densité 0,02 |
| `…::test_le_besoin_d_un_cuir_est_en_kilos` | C | Besoin en kg | Qualité 8S 1 000 m²/mois : cuir 1 ml/m² → 1000 × 0,014 × (1+perte) ; bande 0,6 ml/m² → 1000×0,6×0,005×(1+p) ; poil 2 kg/m² → 2000×(1+p) ; prix au kilo ou au mètre : même besoin |
| `…::test_la_recette_dit_ses_metres_et_ses_kilos_et_le_cout_au_m2` | C | Nomenclature : ml/m², kg/m², coût au m² | Cuir ml_m2 1, kg_m2 0,014, coût = 1 × 0,5 × (1+p) ; bande coût = 0,6 × 2,5 × **9,5** × (1+p) ; identique si le prix est saisi au kilo |
| `…::test_stock_valeur_et_cmup_en_kilos` | C | Stock, CMUP et valeur en kg | Entrées cuir 28 kg à 30 + 14 kg à 45, sortie 8,4 → stock **33,6** ; CMUP **35** ; valeur 33,6 × 35 ; écart au catalogue 33,6 × (35 − 35,714) ; bande 2,5 kg à 500 USD → valeur 2,5 × 500 × 9,5 |
| `…::test_plan_d_achat_en_kilos_et_au_metre_pour_le_fournisseur` | C | Plan d'achat en kg, quantité d'achat en m pour le fournisseur | Bande : `unite_commande` kg, `quantite_achat` = q ÷ 0,005, montant devise = q × 500 = q_achat × 2,5, MAD = × 9,5 ; « kg » dans la relance ; totaux par fournisseur |
| `…::test_repartition_au_poids_d_un_dossier` | C | Fret au poids sur des kg | 1 000 kg + 100 kg, fret 1 100 → **1 000 / 100** ; bande (50 000 + 100) / 100 = 501 |
| `…::test_consommation_d_un_ordre_en_kilos` | C | Net et prévu d'un ordre en kg | OF-9, 100 m² : sorties 1,5 + 210 → net **211,5** ; prévu 100 × (2 + 0,014 + 0,003) ; cuir prévu **1,4**, écart **0,1** |
| `…::test_creer_une_matiere_au_prix_au_metre_ou_au_kilo` | R X | Fiche matière : densité obligatoire pour un rôle au mètre ou un prix au mètre ; « ml » n'est pas une unité d'achat | Cuir/Franges/Ruban sans densité → 422 « densité » ; poil au prix « ml » sans densité → 422 ; unité « m » → 422 ; franges 3 MAD/kg → passées à 0,06/ml (densité 0,02) → prix_kg **3** ; `unite_achat` « ml » → 422 |
| `…::test_la_recette_se_saisit_en_metres_par_m2` | C | API qualités | Cuir ml_m2 1, kg_m2 0,014 ; poil ml_m2 None, kg_m2 2 |
| `…::test_proposition_de_sortie_en_kilos_avec_les_metres` | C | Proposition de sortie en kg | 1 000 m² : cuir **14 × (1+p)** kg (≈ 1 000 × (1+p) ml), lots proposés = ce total ; total (2 000 + 14) × (1+p) ; pas de `theorique_ml` |
| `…::test_stock_et_valeur_en_kilos` | C | API stock et valorisation | Cuir 42 kg, prix_kg 35,714 ; valeur **42 × 35 = 1 470**, CMUP 35 |
| `…::test_bon_au_prix_au_metre` | C E | Bon de commande d'une matière au mètre | 0,6 kg de bande (120 m) : prix ligne **500 USD/kg**, montant estimé **300** ; impression « 0.6 kg ≈ 120 m », sans prix ni « 300 » ; prix confirmé 520/kg avec mise à jour du catalogue → catalogue **2,6 USD/ml** |
| `…::test_reception_hors_commande_au_prix_du_kilo` | C | Réception hors commande : prix catalogue ramené au kg | prix ligne = prix_kg ; stock 2,5 |
| `…::test_le_bilan_du_mois_est_en_kilos` | C | Bilan en kg | `stock_fin_kg` = Σ quantités du journal ; aucune clé `_ml` ; pas de « ml » dans la page |
| `…::test_l_etape_14_convertit_les_metres_en_kilos` | **M** C | Migration « stock en kilos » sur une base tenue au mètre (rejouée dans une transaction annulée) | Densité 0,014 : quantités × d (mouvements, soldes, commande, réception, opération, bon, prévu figé, version approuvée, inventaire 2480/2500/2490 × d), prix ÷ d, **montants inchangés**, `stock_min` et `poids_bobine` × d, poids des dossiers inchangé, **valeur du stock identique** ; contraintes `ck_article_unite_kg`, `ck_article_unite_prix`, `ck_article_prix_au_metre` présentes, anciennes absentes ; `unite='ml'` → violation |
| `test_valeur_et_dates::test_l_unite_du_prix_se_change_et_le_journal_ne_bouge_pas` | R X | Changer l'unité du prix ne touche pas le journal | 100 kg à 10 ; prix 2,5/ml densité 0,25 → prix_kg 10 ; mouvement toujours (100, 10) ; au mètre sans densité → 422 |
| `test_audit2_achats::test_la_liste_des_bons_compte_tout_en_kilos` | C E | Un seul total en kg sur un bon mixte | 1 000 kg + 300 kg de cuir → quantité **1 300**, reçu 1 000, part livrée 1000/1300 ; export « Commandé (kg) » = 1 300, pas de colonne ml |
| `test_audit2_pilotage::test_les_prix_payes_sont_au_kilo` | C E | Historique des prix au kg | Cuir 0,0011 USD/ml ÷ 0,014 → **0,0786 USD/kg** ; 70 kg ; export « Quantité (kg) », « Prix payé (/ kg) », pas de colonne « Unité » |
| `test_audit2_pilotage::test_le_bilan_detaille_les_annulations_en_kilos` | C | Annulations du bilan en kg, pas de « -0 » | Ouverture de cuir 777,7 annulée → annulations OUVERTURE ≤ −777,7 ; montant formaté dans la page ; ni « -0 » ni « -0,0 » |

## 5. Domaine 4 — Commandes et approbation (23)

| Essai | Nat. | Ce qu'il prouve | Données → attendus clés |
|---|---|---|---|
| `test_achats::test_un_brouillon_n_a_pas_de_numero_et_se_date_a_l_envoi` | R X | Numéro donné à l'envoi, date d'envoi ≤ aujourd'hui, série sans trou | Brouillon `numero` None ; envoi daté demain → 422 « futur » ; daté d'hier → `BC-AAAA-…` ; parti : DELETE → 409 « annuler » ; solder sans réception → **annulee** ; rouvrir → envoyee |
| `…::test_un_brouillon_se_supprime_il_ne_se_solde_pas` | X | Brouillon : ni solde ni expédition, suppression | solder → 409 ; expédition → 409 ; DELETE OK |
| `…::test_au_dela_du_seuil_la_direction_approuve_ou_renvoie` | R C X D | Approbation au-delà du seuil | Seuil 5 000 ; 4 000 kg × 3,20 EUR → `montant_estime` **12 800**, `approbation_requise` ; envoi → `a_approuver`, sans numéro ; achats renvoyer → 403 ; motif vide → 422 ; renvoi → brouillon, `renvoi` {motif, par Direction} ; re-soumis ; double envoi → 409 ; approuvé → envoyee, numéro, `approuvee_par` Direction, `renvoi` effacé |
| `…::test_le_cours_se_fige_a_la_premiere_confirmation` | C R | Cours figé à la 1ʳᵉ confirmation de prix | 1ʳᵉ ligne confirmée 3,1 → cours figé, statut envoyee, 1 prix à confirmer, `confirme_par` Achats ; cours EUR change ; 2ᵉ ligne 3,3 → cours inchangé, statut **confirmee**, `montant_mad` = (500×3,1 + 500×3,3) × cours figé |
| `…::test_les_jalons_de_l_expedition` | R X | Jalons : acompte, embarquement, ETA, arrivée, conteneur | Embarquée demain sans ETA → 422 « ETA » ; jalons gardés, conteneur MSCU1234567 |
| `…::test_un_bon_parti_qui_franchit_le_seuil_repasse_par_la_direction` | R C X | Un bon parti modifié au-delà du seuil repasse par la direction **sans perdre son numéro** ; tolérance jusqu'au montant approuvé ; renvoi = version partie | Seuil 50 000 ; 1 000 kg (2 800 EUR) parti ; 20 000 kg → `a_approuver`, même numéro, « ⚪ Attendu », réception possible avec avertissement « approbation » ; 21 000 → toujours à approuver ; envoi → 409 ; approuvé (58 800) ; 19 000 puis 21 000 → envoyee ; 21 500 → a_approuver ; renvoi → envoyee à **21 000** (dernière version acceptée) |
| `…::test_un_prix_confirme_un_peu_plus_cher_ne_rouvre_pas_l_approbation` | R C | Tolérance de hausse de prix après approbation | 3 000 kg vert approuvé ; +3 % → confirmee ; +20 % → a_approuver ; approuvé → confirmee |
| `…::test_le_bon_imprime_et_l_excel_du_fournisseur` | E R | Bon fournisseur **en anglais, A4, sans aucun prix** | 1 120 kg en bobines de 2,5 kg → « Bobbin of 2.5 kg », **448**, « 1,120 kg », `size:A4`, « Purchase order », « Expected delivery » ; absents : « Livraison », « Price », « Prix », « 3,360 », « EUR » ; Excel `/export/commandes/{id}/bon` : mêmes textes, 1 120 présent, 3 360 absent |
| `test_audit2_achats::test_solder_un_bon_a_approuver_est_refuse_et_rouvrir_repasse_par_la_direction` | X R | Pas de contournement par solder/rouvrir | Bon parti 400 → 2 000 (a_approuver) ; solder → 409 « approbation » ; bon forcé « annulee » en base → rouvrir → **a_approuver**, non approuvé |
| `…::test_un_bon_parti_qui_attend_la_direction_reste_attendu_et_se_recoit` | R C | Attendu = version demandée, réception possible, renvoi = version partie (puis soldé) | Attendu 400 puis 600 ; « ⚪ Attendu » ; DELETE → 409 ; réception 400 (avertie) ; renvoi → quantité **400**, statut **soldee** |
| `…::test_reduire_un_bon_usd_quand_le_dollar_monte_ne_repasse_pas_par_la_direction` | C R | Approbation mesurée au cours figé | USD 9,5, seuil 100 000 ; 3 900 kg × 2,67 confirmé (≈ 98 923 MAD) ; USD à 10, réduit à 3 800 → reste confirmee ; `montant_estime_mad` = **3 800 × 2,67 × 9,5** |
| `…::test_la_date_promise_se_compte_a_l_envoi` | C X | Date promise = date d'envoi + délai | Envoi J−3, délai 10 j → promise **J+7** ; promise J−1 avant envoi → 422 « précède » ; envoyé J−5 → garde J−1 ; modifier à J−6 → 422 |
| `…::test_la_promesse_se_confirme_avec_les_prix_puis_se_fige` | R X | Date promise modifiable jusqu'à la confirmation, figée ensuite | J+1 → J+20 accepté ; confirmation avec J+25 → J+25 ; puis J+40 → 422 « ETA » |
| `…::test_une_fiche_qui_change_de_devise_ne_fausse_pas_le_prix_du_bon` | C | Prix estimé converti dans la devise du bon | Bon USD ; fiche passée à 1,6 EUR → montant estimé = 100 × 1,6 × taux EUR ÷ taux USD ; même prix sur la réception |
| `…::test_le_cockpit_compte_les_bons_partis_sans_prix_au_prix_du_catalogue` | C | Engagé = bons partis, sans prix confirmé au catalogue | +100 kg à 10 MAD → `montant_bc_en_cours_mad` et `montant_bc_estime_mad` **+1 000** |
| `…::test_un_prix_confirme_change_par_la_modification_redemande_confirmation` | R X | Prix changé par modification → re-confirmation ; prix confirmé > 0 | Prix 21 → 2 : `prix_confirme` faux, statut envoyee, `confirme_par` "" ; confirmer 0 → 422 |
| `…::test_l_unite_de_commande_est_celle_de_la_fiche` | C X | Unité d'achat et contenance cohérentes avec la fiche | Palette de 7 kg alors que 2,5 × 100 = 250 → 422 (cite 250) ; « Fût » → 422 ; Palette 250 → **4 unités** pour 1 000 kg |
| `test_commandes_receptions::test_un_brouillon_n_est_attendu_de_personne` | R | Un brouillon n'est ni attendu, ni en retard, ni engagé | Brouillon daté J−30 : livraison "" ; `bc_en_cours` et `bc_hors_horizon` 0 ; cockpit inchangé (bons actifs, montant) ; absent de C06 |
| `…::test_le_retard_tolere_vaut_a_l_ecran_et_dans_c06` | R | Tolérance de retard identique à l'écran et dans C06 | Promis J−2 : « 🔴 En retard » et dans C06 ; tolérance 5 j → « ⚪ Attendu », sorti de C06 |
| `…::test_l_approbation_ne_se_contourne_pas_par_paliers` | C R | Tolérance mesurée au **montant approuvé**, pas à la veille | 600 kg × 10 = 6 000 approuvé ; 10,49 (+4,9 %) → confirmee ; 11,0 → **a_approuver** |
| `…::test_un_bon_confirme_modifie_attend_le_prix_de_sa_nouvelle_ligne` | R | Ligne ajoutée → statut envoyee | `prix_a_confirmer` = 1 |
| `test_exports::test_le_bon_de_commande_part_chez_le_fournisseur` | E | Excel `/export/bon-de-commande/{id}` (version **française avec prix**) et sécurité de cellule | En-tête « TAPIS ESSAI SARL », « ICE 001122334455667 », « Bon de commande BC-… » ; 1 800 kg en palettes de 200 → **9**, 1 800 kg, montant **1 800 × 2,55** ; observation `=HYPERLINK(...)` stockée en **texte** (`data_type` "s") |
| `test_audit2_pilotage::test_le_bon_suit_le_papier_a_en_tete_de_l_usine` | E | Papier à en-tête | POLYFASHIONS CARPET S.A.R.L, capital, SIEGE SOCIAL, TANGER, banques, ICE, R.C, N.I.F, C.N.S.S, PATENTE présents dans l'impression |

## 6. Domaine 5 — Réceptions, quarantaine, réclamations (31)

| Essai | Nat. | Ce qu'il prouve | Données → attendus clés |
|---|---|---|---|
| `test_achats::test_on_ne_recoit_pas_sur_un_bon_qui_n_est_pas_parti` | X | Réception sur bon brouillon refusée | 422 « envoyé » |
| `…::test_reception_partielle_avec_une_ligne_sous_reserve` | R C | Réception partielle, quarantaine, solde automatique à la libération | Bon 960 + 960 ; camion 1 : bleu 478 (BL 480), vert 960 « réserve » → brouillon sans numéro, `controle_par` Karim ; validé `REC-…` ; reçu **1 438**, reste **482**, partiel (`livree_le` None) ; camion 2 : `deja_recu` 478, `quantite_attendue` 482 ; « 🟡 Reçu sous réserve », `en_quarantaine` 960, lot V-1 disponible 0 ; transfert de libération → **soldee**, « 🟢 Livré », `livree_le` aujourd'hui |
| `…::test_un_brouillon_annonce_ce_qui_bloquerait` | X | Blocages annoncés sur le brouillon = refus à la validation | Pesée 0, lot vide, sans magasin → **3 blocages** ; validation → 422 avec le 1ᵉʳ |
| `…::test_le_prix_paye_hors_commande_est_retenu` | C | Prix saisi hors commande sur le mouvement | 2,65 EUR → mouvement à 2,65 |
| `…::test_une_reception_toute_refusee_reste_une_trace` | R | Réception 100 % refusée : numérotée, aucun stock | `pese` 0, stock total inchangé |
| `…::test_la_facture_se_complete_apres_la_validation` | R C X | Facture après coup ; échéance par défaut ; facture effacée ; réception annulée non facturable | Échéance avant facture → 422 ; défaut = date + **60 j** (délai fournisseur) ; montant 224 → 230, échéance demain ; numéro "" → facture None ; annulée → 409 |
| `…::test_une_reception_ne_mele_pas_deux_devises` | X | Une réception = une devise ; une facture = une devise | EUR + USD → 422 « deux devises » ; facture USD sur réception EUR → 422 « en EUR » ; correction en USD → 422 ; même n° de facture sur la réception USD → 422 « une devise » |
| `…::test_le_lot_interne_est_numerote_a_la_validation` | R | Lot « LOT INTERNE » numéroté à la validation, pas les refus | `LOT-AAAA-NNNN` (4 chiffres) ; ligne refusée garde « LOT INTERNE » ; numéro suivant = +1 |
| `…::test_l_annulation_dit_qui_quand_et_pourquoi` | R | Annulation tracée | `annulation` {par Achats, motif « lot saisi deux fois »} |
| `…::test_les_listes_s_exportent_comme_a_l_ecran` | E | Exports commandes/réceptions/pesées/bobines avec les filtres de l'écran | Commandes onglet « clos » : feuilles [Commandes, Lignes], bandeau « onglet « Soldées / annulées » », statuts Soldée/Annulée ; Réceptions validées : lots B-1, V-1 ; Pesées écarts : qualité « Sous réserve » ; Bobines : [Par matière, Mesures], ACHAT ESSAI BLEU |
| `test_audit2_achats::test_deux_lots_sur_une_ligne_de_bon_ne_depassent_pas_l_excedent` | X C | Excédent toléré compté **tous lots ensemble** | Bon 1 000 : 700 + 700 → blocage « tous lots ensemble », 422 ; 1 000 + 50 → reçu **1 050** |
| `…::test_deux_postes_ne_franchissent_pas_l_excedent_a_deux` | **P** X | Deux validations simultanées ne franchissent pas l'excédent | 2 brouillons de 1 000 sur un bon de 1 000, `Barrier(2)` → codes **[200, 422]**, reçu 1 000 |
| `…::test_un_brouillon_ne_se_valide_pas_sur_un_bon_annule_entre_temps` | X | Bon annulé après le brouillon | Blocage « annulé », validation 422 |
| `…::test_annuler_une_reception_ne_rouvre_pas_un_bon_solde_a_la_main` | R | Solde manuel respecté | 600 + 100 reçus, soldé à la main, annuler la 2ᵉ → soldee, reçu **600**, reste **0** |
| `…::test_annuler_une_reception_recale_le_bon_sans_le_contredire` | R | Solde automatique recalculé | 1 000 + 30 : annuler 30 → toujours soldee « 🟢 Livré » ; annuler 1 000 → **confirmee** |
| `…::test_hors_commande_la_devise_se_choisit_sur_la_reception` | C | Devise hors commande | Défaut : devise du fournisseur (MAD, prix 20) ; USD choisi (prix 2) ; sans prix : catalogue converti **2 × taux USD** |
| `…::test_une_reception_ne_precede_pas_l_envoi_de_son_bon` | X | Date de réception ≥ envoi du bon | Bon envoyé J−5, réception J−30 → 422 « précède » |
| `…::test_une_reclamation_reste_dans_le_reel` | X | Réclamation bornée par le reçu, la date, la validation ; close garde son issue | 5 000 kg sur 100 reçus → 422 ; ouverte J+90 → 422 ; sur un brouillon → 422 ; close puis issue "" → 422 |
| `…::test_lire_les_receptions_n_ecrit_rien` | R | Lecture sans effet de bord | `quantite_attendue` recalée à 400 à l'affichage ; valeur en base inchangée |
| `test_commandes_receptions::test_un_retour_au_fournisseur_rouvre_le_bon_solde_de_lui_meme` | R C | Reçu **net des retours** | 1 000 reçus → soldee ; retour 300 → **confirmee**, reçu **700**, reste 300, réception `retourne` 300, attendu au stock 300 ; retour annulé → soldee |
| `…::test_un_bon_solde_a_la_main_le_reste_apres_un_retour` | R | Solde manuel conservé après retour | 600 reçus, soldé, retour 100 → soldee, reçu **500** |
| `…::test_une_ligne_sur_dix_livree_dix_fois_n_est_ni_complete_ni_livree` | X C R | Excédent par ligne (10 %) ; une ligne sur 10 n'est pas « livré » | 1 000 sur une ligne de 100 → blocage « excédent » ; tolérance portée à 10 (×) → validée ; in_full 0, otif 0 ; non livré, confirmee |
| `…::test_un_excedent_dans_la_tolerance_passe` | C | +8 % accepté | 1 080 / 1 000 → in_full 1, soldee |
| `…::test_recevoir_sur_un_bon_solde_avertit` | R | Avertissement (pas blocage) | « soldé » dans les avertissements |
| `…::test_une_livraison_partielle_sans_bl_n_est_pas_un_ecart` | C | Écart de pesée seulement face à un BL | 500 sans BL → `ecart` None, hors C08 ; 450 pour BL 500 → écart relatif **−0,1**, hors tolérance |
| `…::test_une_reclamation_vise_ce_que_le_fournisseur_a_livre` | X R | Réclamation : bon fournisseur, devise connue, close/rouverte | Autre fournisseur → 422 (cite le bon fournisseur) ; lot non livré par lui → 422 ; devise XYZ → 422 ; compléter une close la laisse close ; `rouvrir` → ouverte |
| `test_parcours::test_la_reception_entre_en_stock` | C R | Entrée en stock, poids de bobine mesuré, quarantaine | Rouge 998 kg / 5 palettes × 100 bobines → poids bobine **998/500** ; noir réserve : quarantaine 600, disponible 0 ; bon « 🟡 Reçu sous réserve » |
| `…::test_un_brouillon_se_modifie_puis_se_supprime` | R | Brouillon modifiable | Pesée 10 → 12 ; suppression |
| `…::test_une_annulation_contrepasse_tout` | R X | Contre-passation, double annulation refusée | Lot J-ANN à 0 ; journal [−40, +40] ; 2ᵉ annulation → 409 |
| `test_suivi::test_une_reclamation_se_suit_jusqu_a_sa_cloture` | R X D | Numérotation `RCL-`, clôture motivée | Clore sans issue → 422 ; avoir 250 → close ; alimentation → 403 |
| `test_suivi::test_l_atelier_signale_un_besoin_que_les_achats_traitent` | R D | Signalement atelier → achats | Alimentation crée (urgente) ; ne traite pas (403) ; achats traitent → sort de la liste |

## 7. Domaine 6 — Performance fournisseurs (13)

| Essai | Nat. | Ce qu'il prouve | Données → attendus clés |
|---|---|---|---|
| `test_camion_plusieurs_bons::test_chaque_pesee_garde_son_bon` | C (moteur) | Une pesée garde son bon | REC-1 sur BC-1 et BC-2 → `numero_bc` [BC-1, BC-2] |
| `…::test_a_l_heure_si_chaque_bon_l_est` | C (moteur) | Camion de plusieurs bons : à l'heure si chacun l'est | Prévus 20/09 et 10/09 ; arrivée 05/09 → on_time 1 ; 11/09 + tolérance → **0** |
| `test_commandes_receptions::test_l_eta_saisie_apres_coup_n_efface_pas_le_retard` | R C X | Ponctualité jugée sur la date promise | Promise J−10 : la repousser → 422 « ETA » ; ETA du jour ; réception → on_time **0**, in_full 1, otif **0** |
| `…::test_une_reception_hors_commande_n_entre_pas_dans_l_otif` | R | Rien de dû, rien de jugé | in_full None, otif None |
| `…::test_l_otif_moyen_ne_compte_que_les_receptions_notees` | C (moteur) | Moyenne sur les réceptions notées ; score | 1 réception notée + 1 hors commande → otif 1, in_full 1, receptions 2 ; délai 4 j → score **100** |
| `…::test_l_in_full_se_juge_sur_les_lignes_dues` | C (moteur) | 1 ligne sur 10 livrée 10 fois | in_full **0**, otif 0 |
| `…::test_le_score_ne_se_gagne_plus_d_office` | C (moteur) | Formule du score : OTIF × 60 + retours (20 pts à 0 %, 0 à 5 %) + délai (20 pts jusqu'à 15 j) | `points_score(0.18, 0, 4)` = **50,8** (< standard 65 ; ancienne formule 69,4) ; (1, 0, 4) = 100 ; (1, 0.014, 15) = 60 + 20 × (1 − 0,014/0,05) + 20 ; (1, 0.2, 200) = **60** |
| `test_audit2_achats::test_solder_un_bon_tout_renvoye_le_solde_et_garde_sa_note` | R | Bon tout renvoyé : soldé (pas annulé), note gardée | Promise J−10, 600 reçus → (0,0,0) ; retour 600, solder → **soldee** ; in_full/otif 0 |
| `…::test_apres_un_solde_a_la_main_la_livraison_suivante_n_est_pas_notee` | R X | Après solde manuel, livraison non notée ; excédent bloqué | 300 sur bon soldé → avertie, in_full/otif None ; 5 000 → blocage « excédent » |
| `…::test_une_seule_tolerance_pour_le_bon_livre_et_le_camion_complet` | C | Même tolérance pour « Livré » et in_full | 500 + 485 sur 1 000 → « 🟢 Livré » et in_full **1** |
| `…::test_le_camion_de_remplacement_apres_un_retour_est_note` | C | Après retour, le dû renaît | 1 000 reçus (J−12, promise J−10), retour 600, camion de 200 → (0, 0, 0) |
| `…::test_le_score_ne_compte_pas_les_bons_annules` | C | Bon annulé hors du score | `nb_commandes` +1 puis revenu ; `montant_mad` inchangé |
| `test_audit2_pilotage::test_l_otif_moyen_n_a_qu_une_definition` | C | Photo du jour = moyenne des réceptions notées | `photographier_indicateurs()['otif_moyen']` = moyenne des `otif` non nuls de `performance_receptions` |

## 8. Domaine 7 — Factures et échéancier (5)

| Essai | Nat. | Ce qu'il prouve | Données → attendus clés |
|---|---|---|---|
| `test_commandes_receptions::test_l_echeancier_suit_les_paiements` | C R X | Montant estimé, retard, paiement, annulation du paiement | Facture CR-F1 datée J−40, sans montant : **2 000** (200 × 10) estimé, en retard ; payée demain → 422 ; payée aujourd'hui → sort des lignes, `echu_mad` − 2 000, dans `reglees` ; paiement annulé → redevient due |
| `…::test_une_facture_sans_date_est_a_dater_et_s_exporte` | C E | Facture sans date : « à dater », estimée, exportée | 30 × 10 = **300** ; feuille « À dater » contient CR-F-AD |
| `…::test_la_facture_d_une_reception_annulee_n_est_plus_due` | R | Réception annulée → facture écartée | CR-F-AN sort des lignes, entre dans `ecartees` |
| `test_audit2_achats::test_une_facture_reglee_dont_la_reception_est_annulee_reste_visible` | R X | Facture réglée puis réception annulée : écartée « avoir », paiement gardé ; brouillon non dû ; paiement pas avant la facture | `ecartees` raison « avoir », `payee_le` ; facture d'un brouillon absente ; payée 2001-01-01 → 422 |
| `test_direction::test_recette_l_echeancier_liste_ce_qui_est_a_dater` | S | Clé `a_dater` présente | (faible) |

## 9. Domaine 8 — Importations (39)

Règle structurante : **un dossier = une facture = une livraison** (un second camion de la même facture
rejoint son dossier). Coût hors TVA = marchandise (valeur devise × cours) + frais non récupérables ;
TVA à part ; frais répartis au poids (kg) ou à la valeur selon le poste.

| Essai | Nat. | Ce qu'il prouve | Données → attendus clés |
|---|---|---|---|
| `test_importations::test_un_dossier_par_facture` | R X | Toute la facture entre ; une facture = un dossier ; rien d'autre n'entre ; aucune ligne ne sort | IMP-FAC-1 (3 lignes) → `nb_lignes` 3, `pieces` [{facture, réception}] ; 2ᵉ dossier → 409 (cite le n°) ; rattacher IMP-FAC-2 → 409 « une facture » ; ligne d'une autre facture → 409 ; retirer une ligne → 409 ; ligne manuelle → 409 |
| `…::test_cours_commentaire_et_frais_au_poids_ou_a_la_valeur` | C D | Cours du dossier, frais à la valeur puis au poids | 1000×2 + 500×4 + 2000×1 = 6 000 USD × 10 = **60 000 MAD** ; fret 3 500 à la valeur → rouge (20 000/60 000) **1 166,67** ; échéancier : facture + fret ; clé au poids (direction seule, achats 403) → rouge 3 500 × 1000/3500 = **1 000** ; revient **63 500** |
| `…::test_droits_attendus_par_code_douanier_et_tva` | C X D | Droits attendus par code, matière sans code ou code inactif, TVA attendue douane | Code « PP » → 422 ; jute sans code → `droits_attendus` None, `matieres_sans_code` [IMP JUTE] ; codes 10 % et 2,5 % → (21 000 + 20 500) × 0,10 + 22 000 × 0,025 = **4 700** ; code inactif → None ; code porté insupprimable (409), renommé → matières suivent ; DD 4 150 ; TVA attendue = (63 500 × 1,0025 + 4 150) × taux ; tolérance 5 % ; TPI saisie 200 → (63 500 + 4 150 + 200) × taux ; postes système TPI, ASSUR non récupérables, TPI insupprimable ; TVA_TR récupérable hors comparaison : `tva_saisie` 13 560, `tva_mad` **14 560**, pas de C29 |
| `…::test_ligne_a_la_main_lot_inconnu_numero_saisi` | C X | Dossier repris saisi à la main | N° « 07/19 » doublon → 409 ; ligne 100 × 400 USD × 9,5 = **3 800** ; lot inconnu créé sans stock ; frais affecté à la ligne → ligne insupprimable ; poste XYZ → 422 (liste les postes) |
| `…::test_cloture_fige_cours_et_cle` | R C X | Clôture : cours du jour écrit ; frais refusés ; changement de clé sans effet sur un clos | Ligne cours 0 → > 0 ; frais sur clos → 409 ; FRET repassé à la valeur → `dossiers_figes` ≥ 1, revient par ligne inchangé (±0,01), fret total 3 500 ; poste « manut » → code MANUT ; TVA non récupérable sur poste porté → 409 ; DD insupprimable ; rouvrir → ouvert |
| `…::test_analyse_combinaisons_qualite_et_recherche` | R D | Analyse du coût de revient : recherche sans accents et mots dans le désordre, combinaisons, filtre qualité | « frise rouge » → IMP FRISÉ ROUGE ; total poids = Σ détail ; qualité IMPQ ∩ références → seulement le noir ; `references_importees` 2 ; export [Par référence, Lot par lot] ; alimentation → 403 |
| `…::test_export_des_dossiers` | E | Export | Feuilles [Dossiers, Marchandises, Frais, Échéancier] |
| `…::test_documents_du_dossier` | R D | Pièces jointes du dossier | DUM-2026-118.pdf relu ; alimentation → 403 ; suppression |
| `…::test_les_fournisseurs_marocains_n_ont_pas_de_dossier` | R | Factures locales masquées par défaut | REC-LOC-1 absente ; compteur `locaux` ; `?locaux=true` → `local` True |
| `…::test_deux_devises_un_cours_chacune_et_cours_du_bon` | C | Valeur par devise ; ligne de bon au cours figé ; « cours des bons » | EUR **3 300**, USD **1 950** ; PES au cours du bon ; SBR cours 0 ; cours 10,95 ; ligne 9,62 puis « cours des bons » → cours figé |
| `…::test_frais_sans_marchandise_a_part_partout` | C | Frais sans marchandise non répartis, à part dans la liste et l'analyse | 80/19, DD 6 547 654 → charges 0, revient 0, `charges_non_reparties` 6 547 654 ; total charges liste = analyse ; dossier dans `dossiers_non_repartis` |
| `…::test_cout_d_une_qualite_pondere_par_la_recette` | C | Coût d'une qualité = Σ part × coût unitaire | IMPQ 60/40 : `cout_m2` = 0,6 × rouge + 0,4 × noir ; couverture 1 ; Σ parts = 100 |
| `…::test_un_second_camion_de_la_meme_facture_rejoint_son_dossier` | R C X | Second camion → même dossier | IMP-FAC-3 : 300 puis 200 ; le second dit son dossier ; création → 409 ; rattacher → 2 lignes, poids **500** |
| `…::test_une_reception_sans_facture_attend_sa_facture` | R | Réception sans facture en attente ; facture ajoutée → dossier | `sans_facture` valeur USD 100 ; IMP-FAC-9 → dossier 1 ligne |
| `…::test_une_facture_d_un_dossier_repris_n_ouvre_pas_un_second_dossier` | R X | Dossier repris mêlant 2 factures : détacher/rattacher sans contournement | Retirer une ligne → 409 « Détacher la réception » ; détacher RA1 → frais gardés ; FA ne peut ouvrir un 2ᵉ dossier (409 « 50/25 ») ; FC refusée « propre dossier » ; FA détachée entière → nouveau dossier 2 lignes ; réception absente → 404 |
| `…::test_annuler_une_reception_d_un_dossier_passe_par_detacher` | X R | Annulation/facture d'une réception en dossier → message de chemin | 409 « Détacher la réception » + n° ; détachée : dossier vide garde 90 non répartis, TVA/droits attendus None ; suppression → `frais_perdus` 1, **90 MAD** |
| `…::test_la_reprise_relie_les_dossiers_a_leur_facture` | M R | `relier_dossiers_aux_factures` idempotent | 1ʳᵉ passe ≥ 1, 2ᵉ = 0 ; dossier mono-facture → REP-FB ; dossier mêlé → None |
| `…::test_trois_creations_simultanees_un_seul_dossier` | **P** X | 3 postes, une facture : un seul dossier ; course rattrapée par l'index unique | Codes **[201, 409, 409]** ; course simulée (monkeypatch) → 409 « Un autre poste » + n° du gagnant, jamais 500 |
| `…::test_un_fournisseur_marocain_se_confirme` | X | Dossier pour un local : confirmation explicite | 409 « marocain » ; `local_confirme` → 201 |
| `…::test_des_frais_aberrants_se_signalent` | C | C35 frais > 100 % de la marchandise | 3 300 EUR × 10,95 = 36 135 ; transit 3 000 000 → `surcout_aberrant`, surcoût > 50 ; C35 le liste avec « quoi faire » ; supprimé → normal |
| `…::test_la_cloture_dit_le_cours_du_bon_et_trace_le_cours_fige` | R C | Cours figés tracés ; cours disparates signalés | `lignes_cours_bon` 1 ; clôture → commentaire « palette · cours du jour … figé à la clôture » ; second camion après hausse +0,5 → `cours_disparates` [{USD, [c, c+0,5]}] |
| `…::test_une_ligne_en_dirhams_n_a_pas_de_cours` | C M (moteur) | Ligne MAD : cours ignoré ; reprise rend la devise ; dossier vide sans TVA | 1 000 MAD au cours 9,58 → **1 000** ; `devise_ligne_dossier` : (MAD, 9,58, 1000, (USD, 1000)) → (USD, 9,58, 1000) ; sans réception → (MAD, 0, 9 580) ; `tva_attendue` dossier sans marchandise = 0 |
| `test_importations_second_audit::test_un_dossier_pese_en_kilos` | C | Poids en kg, bande comprise | 100 kg fil + 100 kg bande ; manutention 2 000 au poids → 1 000 chacun ; bande revient **3 000**, **30 MAD/kg** |
| `…::test_l_analyse_additionne_des_kilos` | C E | Analyse en kg (défaut SOFIA 367 919 kg à 4,17 au lieu de 49 514 à 30,96) | Fournisseur : 200 kg, unité kg, **6 000/200 = 30** ; par référence bande 100 kg à 30 ; exports « Poids (kg) » 200, « Coût hors TVA / kg » 30 ; « Quantité (kg) », pas « Unité » |
| `…::test_corriger_la_densite_ne_bouge_pas_un_dossier_clos` | R | Densité 0,05 → 0,5 : dossier clos inchangé | revient par référence identique, poids 200 |
| `…::test_changer_la_cle_garde_une_piece_et_son_reglement` | R C | Clé changée sur clos : répartition figée, pièce unique, réglée | 1 000 × 2 × 12 = 24 000, 100 × 10 × 12 = 12 000, transit 3 000 à la valeur → **26 000 / 13 000** ; au poids : inchangé ; une pièce, `parts` [1 000, 2 000], réglée ; échéancier : dans `reglees` 3 000 ; rouvert, montant 1 100 → parts vidées, au poids **1 000 / 100** |
| `…::test_les_morceaux_d_un_ancien_eclatement_redeviennent_une_piece` | **M** | Étape 13 `_importations_figees` recolle, idempotente | 750 (réglé) + 250 « réparti … » → une pièce de **1 000**, `ligne_id` None, commentaire « facture tardive », réglée, parts {l1: 750, l2: 250} |
| `…::test_un_lot_saisi_a_la_main_ne_donne_pas_son_cout_a_une_reception` | C X | Coût d'une réception hors dossier = son prix, pas celui d'un dossier manuel au même n° de lot | Dossier manuel 10 kg à 10 000 MAD ; réception 100 kg × 2 USD → coût unitaire **2 × taux USD** (≠ 1 000) ; ligne manuelle sur lot reçu → 409 « réception » |
| `…::test_la_saisie_a_la_main_est_reservee_aux_dossiers_d_avant` | X | Dossier qui porte des réceptions : pas de saisie manuelle | 409 « porte des réceptions » |
| `…::test_frais_aberrant_sur_une_ligne_et_avoir_negatif` | C X | C35 par ligne ; avoir qui rend une ligne négative refusé | 5 000 sur une ligne de 22 USD (≈ 220 MAD) → `lignes_aberrantes` [A2 FIL], C35 ; avoir −6 000 → 409 « négatif » ; modification à −300 → 409 |
| `…::test_la_facture_se_rapproche_de_la_marchandise_recue` | C | C36 facture ≠ reçu (tolérance 2 %) | 2 541,91 kg × 2 = **5 083,82** reçus pour 4 598 facturés : écart **−485,82**, part −0,0956, hors tolérance ; marchandise **50 838,2 MAD** ; C36 ; facture 5 100 → dans la tolérance |
| `…::test_echeanciers_regle_estime_et_clos_a_dater` | C | Échéancier du dossier et général | Facture marchandise estimée 50 × 2 = **100** ; frais non réglé d'un clos → « à dater » 700 |
| `…::test_les_frais_non_repartis_suivent_les_filtres` | R | Filtres de l'analyse s'appliquent aux non répartis | A2/VIDE présent sans filtre, absent filtré fournisseur, présent par recherche |
| `…::test_une_ligne_en_dirhams_se_fige_a_sa_valeur` | C | `_figer_clos` n'applique pas de cours à une ligne MAD | 1 000 et 3 000 MAD (cours 9,58 parasite) + 400 → **1 100 / 3 300**, inchangés après changement de clé |
| `…::test_ouvrir_pendant_qu_on_annule_la_reception` | **P** | L'ouverture tient la réception ; l'annulation attend puis refuse | Ouverture ralentie (monkeypatch) ; annulation vivante 0,5 s ; ouverture 201, annulation **409** « Détacher » ; réception validee |
| `…::test_corriger_la_facture_pendant_qu_on_ouvre_le_dossier` | **P** | La correction de facture passe d'abord ; l'ouverture relit et refuse | Correction 200, ouverture **409** ; marchandise attend sa vraie facture |
| `test_parcours::test_le_dossier_d_importation_depuis_la_facture` | C X | Dossier depuis la facture : n° `NN/AA`, TVA hors coût | (998 + 600 + 805) × 2,6 × 10 = marchandise ; DD 6 000, TVA 13 000 → revient = marchandise + **6 000**, décaissé = + **19 000** ; Σ charges lignes 6 000 ; double rattachement → 409 ; réception en dossier non annulable → 409 ; clos → frais 409 |
| `test_parcours::test_un_frais_au_poids_suit_les_kilos` | C (moteur) | Fret au poids, DD à la valeur | 100 kg/9 000 et 300 kg/1 000 : fret 400 → **100 / 300** ; DD 1 000 → **900 / 100** |
| `test_valeur_et_dates::test_corriger_la_densite_ne_bouge_pas_un_dossier_clos` | C | Prix au mètre ramené au kg à la réception ; densité corrigée sans effet sur un clos | 0,02 USD/ml ÷ 0,01 = **2 USD/kg** ; densité 0,5 → revient inchangé, poids 50 |

## 10. Domaine 9 — Stock, atelier, inventaires, lots (36)

| Essai | Nat. | Ce qu'il prouve | Données → attendus clés |
|---|---|---|---|
| `test_stock_atelier::test_sortie_plusieurs_qualites_et_unites` | C X R | Proposition multi-qualités ; unités ; brouillon modifiable ; hors recette | Poil pour E1 et E2 (`par_qualite`) ; même qualité deux fois → 422 « une fois » ; 1 palette (50 × 2) = **100**, 5 bobines = **10**, 30 kg → [100, 10, 30] ; « ml » → 422 « kilos » ; bobines sur franges sans poids → 422 ; brouillon → hors recette 12 kg ; validé `OF-` |
| `…::test_sortie_refuse_quarantaine_et_date_ancienne` | X | Pas de sortie depuis la quarantaine ni à date trop ancienne | 422 « quarantaine » ; 1999-12-31 → 422 « ancienne » |
| `…::test_retour_en_bobines_et_deplacement` | C R | Retour en bobines, motif codé | 3 bobines × 2 = **6 kg**, code **R1** ; `revenu` 6 |
| `…::test_quarantaine_liberee_par_les_achats_seulement` | D X | Libération : achats seulement, motif dédié | Alimentation crée → 403, valide → 403 ; motif « Rangement » → 422 « Libération » ; `TRF-` ; lot disponible 100 |
| `…::test_ajustement_en_palettes` | C | Ajustement en bobines | −2 bobines → **−4 kg**, pas de numéro au brouillon |
| `…::test_brouillons_a_valider_et_tout_valider` | R X D | « À valider » et validation groupée : refus individuels, brouillons intacts | Liste triée par date ; achats voient sans `peut_valider` ; validation groupée → validés {bon, ajustement} ; refus : ordre d'hier « antérieure », trop grand « seulement » ; refusé reste brouillon |
| `…::test_lots_historique_statut_et_tracabilite` | C | Lot : entré/sorti, ordres, traçabilité | E-L1 entré **500**, sorti **100**, disponible ; traçabilité mêmes totaux |
| `…::test_journal_pagine_et_valorise` | C | Pagination et valeur des mouvements | Page de 2, `suivant` 2 ; ouverture 500 × 20 = **10 000** ; sortie au CMUP du moment **20 < c < 22**, valeur −100 × c ; page 2 = 3ᵉ ligne |
| `…::test_inventaire_tolerance_perimetre_et_feuille` | R X C | Inventaire : défauts, périmètre par rôle, feuille sans théorique, inventaire tournant | Tolérance **2 %** ; article inconnu → 422 ; rôle Franges → E FRANGE ; feuille sans « Théorique » (sauf option) ; ligne inconnue → 422 ; −50 justifié → validé ; E FRANGE sort des « à compter » |
| `…::test_inventaire_second_comptage` | R C X | Recomptage | Second sans premier → 422 ; −40 → `a_recompter` ; recompte −1 → retenu, dans la tolérance, `second_par` Achats ; ré-enregistrer n'efface pas ; écart total **−1** ; mouvement −1 « recompté par Achats » |
| `…::test_proposition_perte_comprise_et_un_seul_total` | C | Perte comprise ; un seul total kg | 100 m² × 1 kg × 1,02 = **102**, perte 0,02 ; 3 + 7 → total **10**, `kg_par_ml` [0, 0,01] |
| `…::test_annuler_un_ordre_annule_ses_retours` | R C | Annulation d'ordre : retours annulés, stock d'avant | 20 sortis, 5 rendus : annulation → +15 ; retour « annulee » ; traçabilité = soldes, annulation visible |
| `…::test_export_des_sorties` | E S | Export des sorties | Classeur |
| `test_parcours::test_sortie_vers_la_machine_puis_retour` | C X R | Cycle sortie/retour/annulation | Rouge 500 × 1 × 0,6 × 1,02 (±5 %) ; noir manque (quarantaine) ; 50 bobines × 998/500 = **99,8** ; lot 998 − 99,8 ; retour 150 → 409 ; retour 20 → 998 − 79,8 ; annulation → **998** |
| `…::test_la_quarantaine_se_libere_par_un_transfert` | R | Libération → bon soldé | disponible 600, quarantaine 0, bon **soldee** |
| `…::test_le_stock_ne_passe_jamais_sous_zero` | X | Stock ≥ 0 | −10 000 → 409 « ne porte que » |
| `…::test_un_ajustement_se_justifie` | X (faible) | Ajustement sans motif refusé | 409 ou 422, à la création ou à la validation |
| `…::test_deux_sorties_simultanees_sur_la_meme_palette` | **P** | Deux sorties de 70 % du lot en parallèle | Codes **[200, 409]** ; lot = q − part ≥ 0 |
| `…::test_l_inventaire_suspend_puis_ajuste` | R X | Inventaire en cours suspend le magasin ; écart justifié | Sortie → 409 « inventaire » ; −50 non justifié → 422 ; justifié → validé, lot −50 |
| `…::test_les_soldes_egalent_le_journal` | C | Contrôle soldes/journal | `controles/soldes` conforme |
| `…::test_l_etiquette_porte_un_qr` | E | Étiquette QR, scan | `<svg` ; scan `http://x:8030/lot/{id}` → le lot |
| `…::test_deux_retours_simultanes_du_meme_ordre` | **P** | Deux retours de 70 sur 100 sortis | **[200, 409]** ; `sorti_net` **30** |
| `…::test_le_cache_ne_montre_jamais_un_chiffre_perime` | R | Cache invalidé par toute écriture | Stock jute + 12,5 après une ouverture |
| `test_audit2_atelier::test_la_proposition_ne_prend_que_les_lots_presents_a_la_date` | C R | FIFO et présence à la date | Aujourd'hui [VIEUX, NEUF] ; hier [VIEUX], manque **102 − 50 = 52** |
| `…::test_un_ordre_d_hier_ne_valide_pas_un_lot_arrive_aujourd_hui` | X | Lot arrivé après la date de l'ordre | Blocage « après la date de l'ordre » ; 409 ; lot intact 400 |
| `…::test_le_disponible_a_une_date_tient_compte_de_ce_qui_est_sorti_depuis` | C | `presents_au` : disponible passé = min des cumuls futurs | 500 hier, −480 aujourd'hui → hier **20** ; J−3 → 0 |
| `…::test_un_ordre_repris_s_annule_avec_ses_retours_sans_document` | R C M | Retours repris de l'ERP Fil (sans document) annulés avec l'ordre | Revenu 12,5 + 40 = **52,5**, net 400 − 52,5 ; mention « ERP Fil » ; annulé → revenu 0, lots revenus à l'état d'avant (1 000) |
| `…::test_un_retour_ne_se_date_pas_avant_son_ordre` | X | Retour daté avant l'ordre ; deux lignes du même lot additionnées | 422 « avant l'ordre » ; 20 + 20 pour 30 → blocage « 30,00 kg partis … 40,00 kg rendus » ; 409 sans « -0 » |
| `…::test_une_qualite_arretee_ne_part_plus` | X | Qualité inactive | Proposition 422 « arrêtée » ; blocage sur brouillon ; validation 409 |
| `…::test_le_refus_du_stock_parle_en_kilos_au_gramme` | X | Message du refus au gramme | « 1 000,000 kg » et « 1 000,500 kg » |
| `…::test_le_stock_est_en_magasin_ou_en_machine` | C X | Fil monté = stock (magasin **ou** machine), valorisé | 60/40 sur 4 m dans 4,2 m OK ; 3 + 2 m côte à côte → 422 laize ; 4 × 10 × 60 % × 2 = **48 kg** machine = disponible = projeté ; valorisation : magasin 0, stock 48, valeur **480**, machine 480 ; total = Σ lignes = cockpit |
| `…::test_deux_validations_d_ordre_se_suivent_sous_verrou` | **P** | Verrou consultatif des ordres (n° suivent les dates) | `pg_advisory_lock(VERROU_ORDRES)` tenu ailleurs : validation attend (vivante 0,5 s) ; libéré → **[200]** |
| `test_valeur_et_dates::test_une_sortie_datee_avant_l_entree_du_lot_est_refusee` | X | Écriture antérieure à l'entrée du lot | Transfert, ajustement, retour fournisseur datés d'hier sur un lot entré aujourd'hui : blocage « n'est entré », 409 avec la date ; lot 100 |
| `…::test_une_ecriture_ne_creuse_pas_le_lot_apres_sa_date` | X C | Une écriture passée ne rend pas un lot négatif plus tard | 100 (J−10), −80 (J−3), +80 (hier) ; −50 à J−5 → 409 « Au J−3, il n'y avait que 20,00 kg » ; daté d'hier → OK |
| `…::test_ouverture_devise_inconnue_et_un_seul_total` | X C | Devise inconnue ; total en kg | XXX → 422 ; 130 + 13 → **143** |
| `…::test_un_comptage_ne_vaut_que_pour_le_magasin_compte` | R | Inventaire tournant par magasin | Quarantaine non comptée reste due (**50**) ; filtré sur le magasin compté : absente |

## 11. Domaine 10 — Valorisation (CMUP), dates passées, période close (27)

| Essai | Nat. | Ce qu'il prouve | Données → attendus clés |
|---|---|---|---|
| `test_valorisation::test_annuler_une_reception_retire_son_prix_du_cmup` | C (moteur) | Annulation à son coût | 125,7 à 26,89 ; 1 000 à 200 annulés → CMUP **26,89**, valeur **3 380** (et non 22 710), annulation à 200 |
| `…::test_annuler_une_sortie_la_fait_rentrer_a_son_cout` | C | Annulation de sortie au coût d'origine | 100 à 10, sortie 40, entrée 100 à 40, annulation → **10** ; stock [200, 5 000] |
| `…::test_un_retour_fournisseur_sort_au_cout_de_son_lot` | C | Retour au coût du lot | A 100 à 10, B 100 à 50, retour B → **50**, CMUP **10** |
| `…::test_le_cout_d_une_entree_importee_se_trouve_par_sa_ligne_de_reception` | C | Coût de revient par ligne de réception ; manuel par lot | L/D1 (1 000 + 100)/100 = **11** ; L/D2 **33** ; M manuel (500 + 50)/50 = **11** |
| `…::test_une_entree_en_devise_garde_le_cours_de_sa_validation` | C | Cours figé du mouvement | 2 USD au cours 10 → **20** (jour 12) ; sans cours (repris) → 24 |
| `…::test_sans_stock_le_cmup_moyenne_les_achats_chacun_dans_sa_devise` | C | Moyenne des achats, chacun converti | (100 × 2 × 11 + 100 × 20)/200 = **21** (pas 121) |
| `…::test_une_annulation_du_jour_ne_pese_pas_sur_les_sorties_du_jour` | C | Annulation du jour rejouée à sa place (audit G1) | Sortie à **10** (pas 20), stock [50, **500**] |
| `…::test_une_reentree_sur_stock_vide_reprend_ce_qu_elle_a_coute` | C | Ré-entrée sur stock vide (audit G2) | Retour 20 à **10**, stock [20, 200], conso **800** ; lot retrouvé à 10 ; lot inconnu → dernier CMUP **15** ; rien → catalogue **30** |
| `…::test_un_cout_nul_est_un_cout` | C | Coût nul ≠ inconnu (audit G3) | Annulation d'une ouverture à 0 → **0**, stock [100, 1 000] ; stock à 0 MAD → CMUP **0** (pas 20) |
| `…::test_la_classe_xyz_compte_les_sorties_nettes_des_mois_clos` | C | XYZ sur sorties nettes, 12 mois clos | Sortie annulée → CV **0**, « — » ; +300 un mois → CV > 0,5, **Z** |
| `…::test_une_sortie_annulee_n_est_pas_la_derniere_sortie` | C | Dernière sortie | = J1 |
| `…::test_le_cockpit_compare_stock_et_consommation_sur_la_meme_base` | C | DIO et dormants au CMUP | Valeur 1 000 × 20 + 500 × 8 = **24 000** ; coût de rotation 1 200 × 20 / jours × 365 ; DIO = 24 000 / rotation × 365 ; dormant **4 000**, part 4 000/24 000 |
| `…::test_une_date_passee_rejoue_le_journal_et_rouvre_les_commandes` | C | `a_la_date` : journal tronqué, commande rouverte, aujourd'hui intact | Au J2 : mouvement [1], pas de réception, commande « Confirmée », reçu 0 ; stock 100, attendu 500 ; original « Soldée » ; `a_la_date(d, J3) is d` |
| `…::test_les_lots_disponibles_ne_proposent_pas_la_quarantaine` | C | Lots proposés hors quarantaine | [(A, **70**)], par magasin {MAG: 70} |
| `…::test_api_annuler_une_reception_rend_le_cmup_d_avant` | C | Par l'API | CMUP (125,7 × 26,89 + 200 000)/1 125,7 → annulée : **26,89** ; annulation `cout_mad` 200, valeur **−200 000** |
| `…::test_api_retour_fournisseur_au_cout_du_lot` | C | Par l'API | stock 100, CMUP **10** |
| `…::test_api_le_cours_d_une_entree_est_fige_a_sa_validation` | C | GBP 15 → 20 | CMUP **30** inchangé ; mouvement cours 15 |
| `…::test_api_une_date_passee_rejoue_stock_et_valeur` | C | Date de référence | J−5 : 100 kg, **1 000 MAD** ; aujourd'hui 150 ; stock passé 100 |
| `…::test_api_l_inventaire_valorise_ses_ecarts_et_ne_se_date_pas_avant_ce_qu_il_fige` | C X D | Écarts valorisés ; date ≥ entrée des lots | Daté hier → 409 « VI-1 » ; +50 à 10, −50 à 90 : écart **0 kg**, absolu 100, valeur **−4 000**, absolue 5 000 ; alimentation : valeurs None |
| `…::test_api_c12_confronte_les_soldes_au_journal` | C | C12 voit un solde faussé | +5 → 1 anomalie, VS-1 105 vs 100 ; remis → 0 |
| `…::test_api_les_lots_comptent_comme_les_soldes` | C | Liste des lots = soldes | entrées/sorties/stock égaux ; (100, 0) ; disponibles [(VL-1, 70)] |
| `…::test_api_le_bilan_d_un_mois_passe_compte_ses_ruptures_a_la_fin_du_mois` | C | Bilan passé figé | Ruptures du mois dernier inchangées après +1 000 000 kg aujourd'hui ; statut RUPTURE au dernier jour du mois |
| `test_valeur_et_dates::test_une_matiere_recue_recemment_ne_dort_pas` | C | Dormant : dernière entrée compte | Neuve 0 j non dormante ; 200 j → dormante, C18 stock 10 |
| `…::test_a_une_date_passee_ni_le_montage_ni_les_retours_d_apres` | C (moteur) | Date passée sans montage actuel ni retours postérieurs | Machine aujourd'hui **20** ; au J2 {} et reçu **1 000** |
| `…::test_un_mois_clos_ne_se_revalorise_pas` | X R | Période close : frais, cours, nouveau dossier, clé, réouverture refusés ; clôture permise | 409 « période close … rouvre la période » ; valeur au J−5 inchangée ; période rouverte → gestes acceptés |
| `…::test_la_valorisation_s_exporte_a_une_fin_de_mois` | E | Export daté | `valorisation-AAAA-MM-JJ`, titre « au JJ/MM/AAAA » |
| `test_parcours::test_une_periode_close_ne_bouge_plus` | X (faible) | Écriture dans une période close | 409/422 « clos » |

## 12. Domaine 11 — Plan d'achat, besoins, production (28)

| Essai | Nat. | Ce qu'il prouve | Données → attendus clés |
|---|---|---|---|
| `test_audit2_achat::test_une_matiere_non_consommee_ne_se_rachete_pas_pour_son_stock_minimum` | C | Stock min sans conso → pas d'achat | FIL B stock_min 12 900, conso 0 → 0, « non consommée » |
| `…::test_une_matiere_ou_un_fournisseur_desactive_ne_se_rachete_pas` (×2) | C | Inactif → 0 | « désactivé », budget 0 |
| `…::test_le_budget_est_la_somme_des_lignes_affichees` | C | Budget = Σ lignes = Σ fournisseurs | Ligne au statut 🟢 OK à commander comptée |
| `…::test_un_brouillon_n_est_pas_repropose_mais_n_est_pas_attendu` | C | Brouillon déduit de la proposition, pas du projeté | `bc_en_preparation` 300 ; à commander − 300 ; projeté/statut inchangés ; reste 1e-10 → **0** |
| `…::test_un_plan_revise_en_cours_de_mois_compte_pour_ses_jours` | C | Prorata des jours | Sept. : 1 000 × 20/30 + 2 000 × 10/30 ; août 1 000 ; arrêtée le 21 → 1 000 × 20/30 ; vu au 10/09 → 1 000 |
| `…::test_un_coefficient_de_saisonnalite_ne_remet_pas_la_croissance_a_zero` | C | `_versions_du_plan` | Saison seule → ancre 2025-10-01 ; nouvelle base → 2026-03-10 |
| `…::test_la_fenetre_se_compte_en_mois_au_demi_superieur` | C | 75 j = 3 mois | coefficient **4 000/3 000** |
| `…::test_le_fil_qui_en_remplace_un_autre_prend_son_taux_de_realisation` | C | Héritage du taux | A 0,8 ; B 0,8, hérité [FIL A], besoin **800** |
| `…::test_un_fil_abandonne_que_l_atelier_finit_n_est_pas_une_demande_durable` | C | Fil sorti de recette → besoin 0 ; jamais en recette → 30 × 12 | 0 ; **360** |
| `…::test_c33_ne_liste_que_ce_que_le_calcul_plafonne` | C | C33 = lignes plafonnées | retenu = stock_min_plafonne arrondi |
| `…::test_le_realise_a_une_date_passee_prend_le_plan_et_les_ordres_de_cette_date` | C | Réalisé au 15/09 | plan **1 000**, réalisé **300** |
| `…::test_les_besoins_detailles_a_une_date_passee_lisent_le_stock_de_cette_date` | C | Besoins détaillés = stock à la même date | disponible et projeté égaux à `/stock?date_reference=hier` |
| `test_plan_besoins::test_un_plan_releve_n_est_pas_defait_par_le_reel_d_avant` | C | Passé jugé sur le plan de son époque | coefficient **1,0**, besoin **1 500** ; sans histoire 1 000/1 500 |
| `…::test_un_fil_remplace_dans_la_recette_n_est_pas_juge_sur_un_coefficient_qui_ne_le_concerne_pas` | C | Remplacement au 20/09 | B 1,0 hérité, besoin **1 000** ; A besoin annuel **0** |
| `…::test_le_realise_garde_le_plan_d_une_qualite_arretee` | C | Arrêt le 5/10 | sept. 1 000, oct. 0 ; sans histoire : début service 2026-06-01, [0]×7 + [1 000]×4 + [0] |
| `…::test_une_qualite_arretee_sans_histoire_garde_son_plan_jusqu_a_son_dernier_tissage` | C | `_arret_sans_histoire` | août 1 000, sept. 0 ; jamais tissée → 0 |
| `…::test_la_croissance_d_un_mois_ne_depend_pas_du_mois_d_ou_on_le_regarde` | C | Croissance ancrée | sept. 2026 = round(1 000 × 1,12^(8/12)) vu de mars ou sept. ; mode « classeur » diffère |
| `…::test_l_ecart_d_un_ordre_passe_ne_bouge_pas_quand_le_poids_au_m2_change` | C | Prévu au poids du jour, ou figé | OF-1 **100** ; OF-2 figé **90**, perte 0,03 |
| `…::test_un_ordre_annule_avec_retours_ne_compte_rien` | C | Ordre annulé | consommé/retours/net 0 ; début = fin = 01/09 |
| `…::test_une_commande_arrivant_apres_le_delai_mais_dans_la_couverture_est_retranchee` | C | Commande dans la couverture | 500 au 22/11 : `bc_dans_couverture` 500, projeté inchangé, théorique − 500 ; 15/01/2027 → 0 |
| `…::test_la_couverture_se_compare_au_seuil_d_alerte_en_jours` | C | Cible = stock min recalculé ÷ conso/30 | Stocks 1 500, 2 600, 4 000, 9 000 : cohérence couverture/cible ↔ projeté/stock min |
| `…::test_le_tier_et_l_urgence_suivent_le_statut_avant_le_montant` | C | Tier et urgence | CRITIQUE → TIER 1 ; URGENT → TIER 2 ; URGENT classe A 400 000 → TIER 1 ; ATTENTION → TIER 4 ; F « 🚨 BC URGENT », G 900 000 OK « 📋 BC groupé », H « 📝 Standard » |
| `…::test_le_prevu_d_un_ordre_est_fige_et_le_bilan_le_lit_comme_les_sorties` | C R | Prévu figé à la validation ; versions avec poids ; bilan = écran Sorties | 10 × (1 + 0,02) × 1,02 ; figé {perte 0,02, fils {PB POIL 10, PB FRANGE 0,2}} ; poids ×2 → prévu inchangé ; net **50** ; bilan = `consommations` |
| `…::test_un_ordre_annule_avec_son_retour_ne_compte_ni_sortie_ni_retour` | C | Par l'API | 0, 0, 0 |
| `…::test_tout_chemin_qui_change_le_plan_en_garde_la_version` | R C | Versions du plan par tous les chemins | [(0, 800), (800, 900), (900, 900)], dernière inactive ; base 900 gardée ; plan [0]×12 |
| `test_production_plan::test_le_plan_s_enregistre_d_un_bloc` | R C X D | Plan global atomique | Achats/alimentation 403 ; `modifiees` 2 puis 0 ; PLA total **13 000**, déc. **2 000**, kg/m² > 2 ; coefficient 99 → 422, rien écrit |
| `…::test_le_mrp_detaille_rejoint_les_besoins` | C | MRP détaillé = besoins | total égal, qualités ⊇ {PLA, PLB}, Σ par mois |
| `test_stock_atelier::test_plan_des_mois_clos_fige` | C (faible) | Mois clos figés | `plan_fige` ; assertion conditionnelle |

## 13. Domaine 12 — Pilotage, contrôles, analyse, bilan, journal, exports (27)

| Essai | Nat. | Ce qu'il prouve | Données → attendus clés |
|---|---|---|---|
| `test_direction::test_M84_le_cout_d_un_achat_est_le_cout_rendu_usine` | C | Coût rendu usine | Rouge en dossier (cours 10,5, DD 2 500, TVA hors coût) → (1 000 × 2 × 10,5 + 2 500)/1 000 = **23,5** ; bleu hors dossier **20** (cours figé, pas 12) |
| `…::test_M84_les_opportunites_comparent_des_couts_rendus` | C (moteur) | Opportunités sur coûts rendus | Facture : A ; rendu (20 vs 23) : B, économie (23 − 20) × 100 × 12 = **3 600** |
| `…::test_M82_les_opportunites_disent_leur_seuil` | R | Seuils et écartées | seuil forte = réglage ; {sans_date, hors_fenetre} ; avertissement « coût rendu » |
| `…::test_chaque_controle_dit_quoi_faire` | R | ≥ 30 contrôles, chacun avec `quoi_faire`, `vers`, colonnes libellées | C03 conforme |
| `…::test_le_cockpit_compte_toutes_ses_alertes` | R | Structure | `nb_alertes` ≥ len ; détenues ≥ 2 ; champs |
| `…::test_le_journal_des_actions_se_filtre_et_s_exporte` | R D E | Filtres, export | Achats + « cours de change » ; au 2001-01-01 vide ; achats 403 |
| `…::test_les_cours_sont_dates` | R | Historique des cours | [12, 10], par Achats |
| `…::test_M80_l_analyse_s_exporte` (×6) | E D | Exports d'analyse | Contrôles, Valorisation, Historique des achats, Opportunités, Fournisseurs, Échéances ; alimentation 403 |
| `…::test_M80_la_matrice_s_exporte_dans_la_devise_de_la_facture` | E | Matrice | USD, 2,0 |
| `…::test_recette_les_seuils_de_couverture_restent_dans_l_ordre` | X | critique < alerte | 120 ≥ 90 → 422 « ATTENTION » |
| `…::test_recette_les_opportunites_comparent_la_meme_couleur_par_defaut` | R | Défauts | même couleur ; fenêtre 30 |
| `…::test_recette_le_bilan_compte_les_annulations_a_part` | S | Bilan | texte « Annulations (contre-passations) » |
| `test_exports::test_le_pilotage_s_exporte` | E C D | Export pilotage | 5 feuilles ; stock net **420** ; C01 ; alimentation 403 |
| `…::test_une_date_hors_periode_est_refusee` | X | 1990 → **400** | |
| `…::test_le_journal_s_exporte_avec_ses_filtres` | E | Mouvements filtrés | EXP-1 : 1 ligne, 420 ; pas « Unité » ; filtre vide → classeur vide |
| `test_audit2_pilotage::test_C03_verifie_la_famille_du_motif` | C (moteur) | C03 | **3** anomalies (R2, R3, —) |
| `…::test_les_controles_impossibles_se_disent_garantis_par_la_base` | R | Contrôles garantis | {C09, C10, C11, C16, C21}, hors total ; C11 → devises ; C27 sans « Traçabilité » |
| `…::test_le_journal_ecrit_les_taux_en_pourcent_et_cherche_les_jokers` | R | Journal | « 20 % → 25 % » ; « % » et « _ » cherchés littéralement |
| `…::test_croissance_et_tolerance_de_livraison_bornees` | X | Bornes | croissance −1 → 422 ; in_full 0,5 → 422 ; −0,9 et 0,2 acceptés |
| `…::test_une_croissance_de_moins_100_ne_fait_plus_tomber_un_mois_passe` | C | Pas de division par zéro | m² > 0 |
| `…::test_le_cockpit_d_une_date_passee_repond` | S | 200 | |
| `test_audit2_achats::test_le_courriel_du_lundi_compte_les_retards_comme_l_ecran` | C | Courriel = écran | égaux, ≥ 1, avec tolérance 60 aussi |
| `…::test_c38_signale_un_prix_du_catalogue_eloigne_du_dernier_prix_paye` | C | C38 | rapport **2,5 / 0,12 ≈ 20,8** ; catalogue non touché |
| `test_valeur_et_dates::test_c12_et_c14_voient_une_ecriture_datee_apres_aujourd_hui` | C | C12/C14 sur toutes les données | Écriture future → C14 ; solde +50 → C12, aussi à J−10 |
| `…::test_le_bilan_compte_les_dirhams_sans_les_receptions_annulees` | C | Bilan | +**2 500** puis retour à l'avant ; valeur fin = valorisation ; textes |
| `test_suivi::test_bilan_echeancier_et_import_des_matieres` | S E | Bilan, échéancier, modèle d'import | modèle réimporté : 0 erreur, 0 créée, 0 modifiée |
| `test_parcours::test_les_vues_de_pilotage_repondent` | S | 27 vues en 200 | |

Contrôles couverts : C01, C03, C06, C08, C09/10/11/16/21 (garantis), C12, C14, C18, C27 (libellé),
C29, C33, C35, C36, C37, C38. **Jamais exercés** : C02, C04, C05, C07, C13, C15, C17, C19, C20, C22,
C23, C24, C25, C26, C28, C30, C31, C32, C34 (19 sur 38).

## 14. Domaine 13 — Vérification transversale (6)

| Essai | Nat. | Ce qu'il prouve | Données → attendus clés |
|---|---|---|---|
| `test_zz_verificateur::test_les_ecrans_concordent_avec_la_base` | C | Vérificateur sur tout ce que la séance a écrit | 0 écart (voir `VERIFICATION.md`) |
| `test_parite::test_memes_resultats_que_l_erp_fil` | C | Parité ERP Fil | sortie 0 et « écarts à corriger : 0 » ; sauté sans ERP Fil |
| `test_zz_restauration::test_restaurer_depuis_l_ecran_ne_se_bloque_pas` | M P | Restauration sur un vrai serveur uvicorn | Sauvegarde manuelle puis restauration < **30 s**, `installe` True ; sauté sans outils PostgreSQL |
| `test_valeur_et_dates::test_c37_et_le_verificateur_voient_un_lot_sous_zero_dans_le_passe` | C | Faute injectée en SQL | C37 manque 50, bloquant ; vérificateur : « Aucun lot sous zéro… » et « Aucune écriture à coût nul… » |
| `…::test_le_verificateur_voit_les_fautes_du_moteur_d_avant` | C | Le vérificateur attrape les 3 fautes du 2ᵉ audit (ancien moteur réinjecté) | G1 conservation de valeur ; G2 ordre de grandeur ; G3 annulation au coût |
| `test_valorisation::test_api_le_verificateur_voit_une_valeur_fausse` | C | CMUP × 1,1 injecté | écart « Valeur conservée » |

---

## 15. Essais faibles

| Essai | Faiblesse | À faire dans PRO |
|---|---|---|
| `test_parcours::test_un_ajustement_se_justifie` | Accepte 409 **ou** 422, à la création ou à la validation | Exiger 422 à la création, message précis |
| `test_parcours::test_une_periode_close_ne_bouge_plus` | Idem | Un code, une étape |
| `test_stock_atelier::test_plan_des_mois_clos_fige` | Assertion sous `if ligne and ligne2` : peut ne rien vérifier | Données dédiées, assertion inconditionnelle |
| `test_direction::test_recette_l_echeancier_liste_ce_qui_est_a_dater` | Clé présente | Fusionner avec la vérification chiffrée de l'échéancier |
| `test_direction::test_recette_le_bilan_compte_les_annulations_a_part`, `test_suivi::test_bilan_echeancier_et_import_des_matieres` | Texte présent, montant ≥ 0 | Valeurs chiffrées |
| `test_audit2_pilotage::test_le_cockpit_d_une_date_passee_repond`, `test_parcours::test_les_vues_de_pilotage_repondent`, `test_stock_atelier::test_export_des_sorties`, `test_referentiels_complets::test_les_exports_des_referentiels`, `test_direction::test_M80_l_analyse_s_exporte` | Fumée | Garder, compléter par des valeurs |
| `test_direction::test_le_cockpit_compte_toutes_ses_alertes` | Structure, `≥` | Recalcul indépendant |
| `test_referentiels_complets::test_delai_mesure` | Cas vide seulement | Délai mesuré sur bons reçus |
| `test_parcours::test_l_etiquette_porte_un_qr` | `<svg` présent | Décoder le QR |
| `test_achats::exports` (fixture) | No-op | Supprimer |
| `test_parcours::test_sortie_vers_la_machine_puis_retour` | `rel=0.05` | Valeur exacte |
| `test_zz_restauration::test_restaurer…` | Ne compare pas le contenu restauré | Empreinte avant/après |
| Concurrence (9 essais) | Courses à 2–3 fils, résultat par codes | Ajouter boucles répétées et invariants |

Fragilités : dépendance à l'ordre et état partagé (`pytest.dossier`, `test_zz_*`) ; dépendance à la date
du jour (bord de mois) ; essais sautés silencieusement ; `test_parite` dépend d'un autre virtualenv et
d'une base SQLite hors du dépôt.

## 16. Redondances

| Groupe | Essais | Remarque |
|---|---|---|
| Annuler un ordre annule ses retours | `test_parcours::test_sortie_vers_la_machine_puis_retour`, `test_stock_atelier::test_annuler_un_ordre_annule_ses_retours`, `test_plan_besoins::test_un_ordre_annule_avec_son_retour…`, `test_plan_besoins::test_un_ordre_annule_avec_retours_ne_compte_rien`, `test_audit2_atelier::test_un_ordre_repris_s_annule…` | Un essai paramétré stock + consommation + reprise |
| Frais au poids | `test_parcours::test_un_frais_au_poids_suit_les_kilos`, `test_matieres_au_metre::test_repartition_au_poids_d_un_dossier` | Doublon moteur |
| Densité / dossier clos | Deux essais au même nom | Doublon |
| Aucun prix pour l'alimentation | 3 essais | Remplacer par un balayage générique |
| Retour fournisseur au coût du lot | moteur et API | Garder (2 niveaux) |
| Annulation de réception / CMUP | moteur et API | Garder |
| Approbation | 6 essais | Complémentaires, en faire une table de transitions |

## 17. Contradiction

`test_le_bon_imprime_et_l_excel_du_fournisseur` (`/api/export/commandes/{id}/bon`) : anglais, **sans
prix**. `test_le_bon_de_commande_part_chez_le_fournisseur` (`/api/export/bon-de-commande/{id}`) :
français, **avec prix et montant**, nommé « part chez le fournisseur ». La décision de Mohamed
(PLAN.md) : bon fournisseur en anglais, sans prix. PRO : une seule route « fournisseur » sans prix ;
la version chiffrée, si gardée, s'appelle « bon interne ».

## 18. Routes jamais exercées par un essai

207 routes. Écritures jamais appelées : `POST /api/installation`, `POST /api/deconnexion`, `POST
/api/moi/code`, `POST /api/utilisateurs`, `PUT /api/utilisateurs/{uid}`, `PUT /api/dossiers/{did}`,
`DELETE /api/inventaires/{iid}`, `PUT /api/operations/{oid}`, `POST /api/articles/composer`, `POST
/api/indicateurs/photographier`. Lectures jamais lues par un rôle connecté : `GET /api/moi`,
`/api/parametres/historique`, `/api/operations/motifs`, `/api/plan-achat/fournisseur/{nom}`,
`/api/receptions/bobines`, `/api/acces`, `/api/acces/qr`, `/api/indicateurs/historique`,
`/api/courriel/apercu`. Le balayage des droits ne porte que sur les GET anonymes ; aucun essai ne
prouve que chaque route d'écriture déclare ses rôles.
