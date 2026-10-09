-- Petite usine au schéma de Gestion MP corrigé (lot R1, tests/fabriques/reprise.py).
-- Une ligne de chaque sorte : chaque traduction de la reprise (MODELE-DONNEES § 10.3).
-- @@EMPREINTE@@ : empreinte scrypt du code « direction-1 », posée par la fabrique.
INSERT INTO utilisateur VALUES
 (1, 'mohamed', 'MOHAMED MAZARI', 'direction', 'm@usine.ma', '@@EMPREINTE@@', true, '2026-09-01', NULL),
 (2, 'Atelier', 'Atelier', 'alimentation', '', 'pbkdf2$ancien', true, '2026-09-01', NULL);
INSERT INTO role_nomenclature VALUES ('Poil', false, 0), ('Chaîne', false, 1), ('Trame', false, 2),
 ('Colle', false, 3), ('Cuir', true, 4), ('Franges', true, 5), ('Ruban', true, 6),
 ('Plastique', false, 7);
INSERT INTO devise VALUES ('MAD', 'Dirham', 1, true), ('USD', 'Dollar', 9.5, true),
 ('EUR', 'Euro', 11, true);
INSERT INTO parametre VALUES ('taux_perte', '0.02', '2026-09-01', 'MOHAMED MAZARI'),
 ('seuil_critique', '60.0', '2026-09-01', 'Mohamed'),
 ('courriel_dernier_envoi', '2026-10-05', '2026-10-05', 'système');
INSERT INTO parametre_historique VALUES (1, 'cours_USD', '9.5', '2026-09-01 08:00', 'Mohamed'),
 (2, 'seuil_critique', '45.0', '2026-09-01 08:00', 'Mohamed'),
 (3, 'seuil_critique', '60.0', '2026-09-02 08:00', 'MOHAMED');
INSERT INTO poste_frais VALUES ('DD', 'Droits de douane', false, 0, 'valeur'),
 ('TPI', 'Taxe parafiscale', false, 1, 'valeur'), ('TVA', 'TVA', true, 2, 'valeur'),
 ('PORT', 'Port', false, 3, 'valeur'), ('FRET', 'Fret', false, 4, 'poids'),
 ('ASSUR', 'Assurance', false, 5, 'valeur'), ('TRANSIT', 'Transitaire', false, 6, 'valeur'),
 ('TIMBRE', 'Timbre', false, 7, 'valeur'), ('INT_OC', 'Intérêts', false, 8, 'valeur'),
 ('TMSA', 'TMSA', false, 9, 'valeur'), ('AUTRE', 'Autre', false, 10, 'valeur');
INSERT INTO composition VALUES ('PES', 'Polyester', 'Synthétique', true, '', '');
INSERT INTO type_fil VALUES ('DTY', 'Texturé', true, '');
INSERT INTO titrage VALUES ('2900', '2900', 'Dtex', true, '');
INSERT INTO couleur VALUES ('Rouge', 'Rouge', 'Rouges', true, '');
INSERT INTO fournisseur (id, nom, code, pays, devise, delai_jours, notes, actif) VALUES
 (1, 'LOMAT', 'LOM', 'Turquie', 'USD', 45.0, '', true),
 (2, 'LOCAL', '', 'maroc', 'MAD', 30.4, '', true);
INSERT INTO magasin VALUES (1, 'Principal', 'Magasin principal', 'Stock courant', true, ''),
 (2, 'Morocco', 'Morocco', 'Stock courant', true, ''),
 (3, 'Quarantaine', 'Quarantaine', 'Quarantaine', true, '');
INSERT INTO metier VALUES (1, 'M1', 'Métier 1', 4.2, 320, 2, true, '');
INSERT INTO article (id, reference, designation, role, composition, type_fil, titrage, couleur,
 unite_prix, densite, fournisseur_id, prix, devise, unite_achat, contenance_achat, version,
 modifie_par) VALUES
 (1, 'PES ROUGE', 'Poil rouge', 'Poil', 'PES', 'DTY', '2900', 'Rouge', 'kg', 0, 1, 2.5, 'USD',
  'Palette', 756, 1, 'MOHAMED MAZARI'),
 (2, 'Jute', 'Jute 12/1', 'Trame', NULL, NULL, NULL, NULL, 'kg', 0, 2, 10, 'MAD', 'Palette', 0, 1, ''),
 (3, 'Cuir', 'Cuir', 'Cuir', NULL, NULL, NULL, NULL, 'ml', 0.014, 2, 0.074, 'MAD', 'kg', 1, 1, '');
INSERT INTO fil_monte VALUES (1, 1, 1, 1, 4, 100, ''), (2, 1, 5, 2, 4, 100, '');
INSERT INTO qualite VALUES (1, 'Q1', 'Qualité 1', 1200, true);
INSERT INTO qualite_poids VALUES (1, 1, 'Poil', 1.5), (2, 1, 'Trame', 0.5);
INSERT INTO qualite_saison SELECT m, 1, m, 1.0 FROM generate_series(1, 12) m;
INSERT INTO recette VALUES (1, 1, 1, 100), (2, 1, 2, 100);
INSERT INTO recette_version VALUES
 (1, 1, '2026-09-01 09:00', 'MOHAMED MAZARI', '[{"reference": "PES ROUGE", "role": "Poil", "pourcentage": 100.0}, {"reference": "Jute", "role": "Trame", "pourcentage": 100.0}]', '{"Poil": 1.5, "Trame": 0.5}'),
 (2, 1, '2026-08-01 09:00', '', '[{"reference": "PES ROUGE", "role": "Poil", "pourcentage": 100.0}, {"reference": "Disparue", "role": "Trame", "pourcentage": 100.0}]', NULL);
INSERT INTO facture VALUES (1, 1, 'F-1', '2026-09-03', 2500, 'USD', '2026-10-03', NULL),
 (2, 2, 'F-2', '2026-09-04', 0, 'MAD', '2026-09-01', NULL);
INSERT INTO commande (id, numero, fournisseur_id, date_commande, statut, devise, cours,
 observations, cree_par, cree_le, approuvee_par, approuvee_le, montant_approuve, version_approuvee)
 VALUES
 (1, 'BC-2026-0001', 1, '2026-09-01', 'confirmee', 'USD', 0, '', 'MOHAMED MAZARI',
  '2026-09-01 10:00', 'MOHAMED MAZARI', '2026-09-01 11:00', 23750.0, '{"montant": 2500.004, "lignes": [{"article_id": 1, "quantite": 1000.0, "unite_achat": "Palette", "contenance": 756.0, "prix": 2.5, "prix_confirme": true, "confirme_par": "MOHAMED MAZARI", "confirme_le": "2026-09-02T10:00:00"}]}'),
 (2, 'BC-2026-0002', 2, '2026-09-01', 'soldee', 'MAD', 0, '', 'Mohamed', '2026-09-01 10:00',
  '', NULL, 0, ''),
 (3, 'BC-2026-0003', 2, '2026-09-05', 'brouillon', 'MAD', 0, '', 'Mohamed', '2026-09-05 10:00',
  '', NULL, 0, '');
INSERT INTO commande_ligne VALUES (1, 1, 1, 1000.0000000001, 'Palette', 756, 2.5, true, NULL, ''),
 (2, 2, 2, 500, 'kg', 1, 10, false, NULL, '');
INSERT INTO lot VALUES (1, 1, 'L 001', 1, '2026-09-03', 3.15, ''),
 (2, 1, 'LOT-2026-0001', 1, '2026-09-03', 0, ''), (3, 2, 'J-1', 2, '2026-09-01', 0, ''),
 (4, 1, 'L-004', 1, '2026-09-06', 0, ''), (5, 1, 'L-005', 1, '2026-09-06', 0, ''),
 (6, 1, 'L-006', 1, '2026-09-06', 0, '');
INSERT INTO reception (id, numero, statut, date, fournisseur_id, numero_bl, facture_id,
 observations, cree_par, cree_le, validee_par, controle_par, validee_le) VALUES
 (1, 'REC-2026-0001', 'validee', '2026-09-03', 1, 'BL1', 1, '', 'Karim', '2026-09-03 08:00',
  'Karim', '', '2026-09-03 09:00'),
 (2, 'REC-2026-0002', 'annulee', '2026-09-04', 2, '', 2, '', 'Karim', '2026-09-04 08:00',
  'Karim', '', '2026-09-04 09:00'),
 (3, 'REC-2026-0003', 'brouillon', '2026-09-05', 2, '', NULL, '', 'Karim', '2026-09-05 08:00',
  '', '', NULL),
 (4, 'REC-2026-0004', 'validee', '2026-09-06', 1, 'BL4', NULL, 'camion mixte', 'Karim',
  '2026-09-06 08:00', 'Karim', '', '2026-09-06 09:00');
INSERT INTO reception_ligne (id, reception_id, commande_ligne_id, article_id, lot_numero,
 quantite_pesee, nb_bobines, magasin_id, qualite, prix, devise, lot_id) VALUES
 (1, 1, 1, 1, 'L 001', 1000, 320, 1, 'conforme', 2.5, 'USD', 1),
 (2, 1, NULL, 1, 'LOT INTERNE', 100, 30, 1, 'conforme', 2.0, 'EUR', 2),
 (3, 2, 2, 2, 'J-9', 50, 0, NULL, 'refuse', 10, 'MAD', NULL),
 (4, 4, NULL, 1, 'L-004', 40, 0, 1, 'conforme', 2.6, 'USD', 4),
 (5, 4, NULL, 1, 'L-005', 30, 0, 1, 'conforme', 2.6, 'USD', 5),
 (6, 4, NULL, 1, 'L-006', 20, 0, 1, 'conforme', 2.1, 'EUR', 6);
INSERT INTO bon_sortie VALUES
 (1, 'OF-2026-0001', 'valide', '2026-09-10', 1, 1, '', 'Youssef', '2026-09-10 08:00', 'Youssef',
  NULL, '{"perte": 0.02, "fils": {"PES ROUGE": 300.0, "Inconnue": 5.0}}'),
 (2, 'OF-2026-0002', 'brouillon', '2026-09-11', 1, 1, '', 'Youssef', '2026-09-11 08:00', '', NULL, NULL);
INSERT INTO bon_fabrication VALUES (1, 1, 1, 150.00049);
INSERT INTO bon_ligne VALUES (1, 1, 1, 1, 300), (2, 1, 1, 1, 200);
INSERT INTO operation VALUES (1, 'TRF-2026-0001', 'transfert', 'validee', '2026-09-12', NULL, NULL,
 'Rangement', '', 'Karim', '2026-09-12 08:00', 'Karim', '2026-09-12 09:00');
INSERT INTO operation_ligne VALUES (1, 1, 2, 3, 'J-1', 1, 2, 50, 0, '');
INSERT INTO inventaire VALUES (1, 'INV-2026-0001', 'Inventaire', 'valide', '2026-09-20', 2, 0.02,
 'Karim', 'Mohamed', NULL);
INSERT INTO inventaire_ligne (id, inventaire_id, lot_id, article_id, lot_numero, magasin_id,
 theorique, compte, second_compte, second_par, justification)
 VALUES (1, 1, 3, 2, '', 2, 50, 45, 45, 'MOHAMED', 'casse');
INSERT INTO mouvement (id, date_effet, date_saisie, type, article_id, lot_id, magasin_id,
 quantite, prix, devise, cours, document, document_id, document_numero, ordre_id, paire, motif,
 auteur, contrepasse_id) VALUES
 (1, '2026-09-01', '2026-09-01 08:00', 'OUVERTURE', 2, 3, 1, 200, 10, 'MAD', 0, 'reprise', NULL, '', NULL, NULL, '', '', NULL),
 (2, '2026-09-03', '2026-09-03 09:00', 'RECEPTION', 1, 1, 1, 1000.0000000002, 2.5, 'USD', 9.5, 'reception', NULL, 'BC-2026-0001', NULL, NULL, '', 'Karim', NULL),
 (3, '2026-09-03', '2026-09-03 09:00', 'RECEPTION', 1, 2, 1, 100, 2.0, 'EUR', 0, 'reception', 1, 'REC-2026-0001', NULL, NULL, '', 'Karim', NULL),
 (4, '2026-09-10', '2026-09-10 09:00', 'SORTIE', 1, 1, 1, -300, 2.5, 'USD', 0, 'sortie', 1, 'OF-2026-0001', 1, NULL, '', 'Youssef', NULL),
 (5, '2026-09-10', '2026-09-11 09:00', 'SORTIE', 1, 1, 1, 300, 2.5, 'USD', 0, 'sortie', 1, 'OF-2026-0001', 1, NULL, '', 'Mohamed', 4),
 (6, '2026-09-10', '2026-09-11 10:00', 'SORTIE', 1, 1, 1, -200, 2.5, 'USD', 0, 'sortie', 1, 'OF-2026-0001', 1, NULL, '', 'Youssef', NULL),
 (7, '2026-09-12', '2026-09-12 09:00', 'TRANSFERT', 2, 3, 1, -50, 10, 'MAD', 0, 'operation', 1, 'TRF-2026-0001', NULL, 7, 'Rangement', 'Karim', NULL),
 (8, '2026-09-12', '2026-09-12 09:00', 'TRANSFERT', 2, 3, 2, 50, 10, 'MAD', 0, 'operation', 1, 'TRF-2026-0001', NULL, 7, 'Rangement', 'Karim', NULL),
 (9, '2026-09-13', '2026-09-13 09:00', 'RETOUR_FOURNISSEUR', 2, 3, 1, -20, 10, 'MAD', 0, 'reprise', NULL, '', NULL, NULL, 'Excédent de réception', 'Karim', NULL),
 (10, '2026-09-14', '2026-09-14 09:00', 'RETOUR_MACHINE', 1, 1, 1, 10, 2.5, 'USD', 0, 'reprise', NULL, '', NULL, NULL, 'Reliquat de fin d''ordre', 'Youssef', NULL),
 (11, '2026-09-20', '2026-09-20 18:00', 'AJUSTEMENT', 2, 3, 2, -5, 10, 'MAD', 0, 'inventaire', 1, 'INV-2026-0001', NULL, NULL, 'Écart d''inventaire', 'Mohamed', NULL),
 (12, '2026-09-06', '2026-09-06 09:00', 'RECEPTION', 1, 4, 1, 40, 2.6, 'USD', 0, 'reception', NULL, 'REC-2026-0004', NULL, NULL, '', 'Karim', NULL),
 (13, '2026-09-06', '2026-09-06 09:00', 'RECEPTION', 1, 5, 1, 30, 2.6, 'USD', 0, 'reception', NULL, 'REC-2026-0004', NULL, NULL, '', 'Karim', NULL),
 (14, '2026-09-06', '2026-09-06 09:00', 'RECEPTION', 1, 6, 1, 20, 2.1, 'EUR', 0, 'reception', NULL, 'REC-2026-0004', NULL, NULL, '', 'Karim', NULL);
INSERT INTO solde VALUES (1, 1, 810.0000000002), (2, 1, 100), (3, 1, 130), (3, 2, 45),
 (4, 1, 40), (5, 1, 30), (6, 1, 20);
INSERT INTO dossier VALUES (1, '01/26', 'LOMAT septembre', '2026-09-03', 'BMCI', 'clos',
 '2026-09-25 10:00', '', 1), (2, 'X-OLD', 'Ancien', NULL, '', 'ouvert', NULL, '', NULL);
INSERT INTO dossier_ligne VALUES
 (1, 1, 1, 1, 1, 1, 1000, 2500, 'USD', 9.5, '', NULL, true),
 (2, 1, NULL, 1, 2, 1, 100, 200.004, 'EUR', 0, '', NULL, false);
INSERT INTO dossier_charge VALUES (1, 1, 'DD', 1000.005, NULL, 'D1', '', '', NULL, NULL, NULL),
 (2, 1, 'TRANSIT', 100, 1, 'T1', '', 'Transit SA', NULL, '2026-10-01', NULL),
 (4, 1, 'FRET', 0, NULL, '', '', '', NULL, NULL, NULL);
INSERT INTO dossier_charge_part VALUES (1, 1, 909.0954545), (1, 2, 90.9095454);
INSERT INTO reclamation (id, numero, fournisseur_id, reception_id, reception_ligne_id, lot_id,
 motif, description, quantite, montant_demande, devise, reponse, issue, montant_obtenu, statut,
 ouverte_le, close_le, cree_par) VALUES (1, 'RCL-2026-0001', 1, 1, 1, 1, 'Quantité manquante',
 'manque', 20, 50, 'USD', 'avoir reçu', 'Avoir', 50, 'close', '2026-09-05', '2026-09-20', 'Mohamed'),
 (2, 'RCL-2026-0002', 1, 4, 6, 6, 'Qualité (défaut du fil)', 'fil cassant', 5, 0, 'EUR', '', '',
  0, 'ouverte', '2026-09-07', NULL, 'Mohamed');
INSERT INTO signalement (id, quand, par, par_id, article_id, texte, urgence, traite_par,
 traite_le, reponse) VALUES (1, '2026-09-15 08:00', 'Atelier', 2, 1, 'Plus de fil rouge',
 'urgente', '', NULL, '');
INSERT INTO indicateur_jour VALUES ('2026-10-08', '{"valeur_stock_mad": 1234.567, "couverture_jours": 12.345, "ruptures": 2, "critiques": 1, "urgents": 0, "a_commander_mad": 99.999, "commandes_en_cours_mad": 0.0, "otif_moyen": null}');
INSERT INTO compteur VALUES (1, 'BC', 2026, 3), (2, 'REC', 2026, 3), (3, 'OF', 2026, 2);
INSERT INTO journal (id, quand, utilisateur, role, action, objet, objet_id, detail) VALUES
 (1, '2026-09-01 08:00', 'MOHAMED MAZARI', 'direction', 'installation', 'utilisateur', 1, ''),
 (2, '2026-09-02 08:00', 'Mohamed', 'direction', 'plan de production', 'qualite', 1,
  'Q1 : base 1 200 m²
plan={"avant": {"b": 1000.0, "c": [1,1,1,1,1,1,1,1,1,1,1,1]}, "apres": {"b": 1200.0, "c": [1,1,1,1,1,1,1,1,1,1,1,1.2], "a": true}}'),
 (3, '2026-09-02 09:00', 'Mohamed', 'direction', 'renvoi aux achats', 'commande', 1,
  'BC-2026-0001 · trop cher, renégocier'),
 (4, '2026-09-02 10:00', 'MOHAMED MAZARI', 'direction', 'commande à approuver', 'commande', 1,
  'BC-2026-0001 · prix · 20 000 MAD → 23 750 MAD (seuil 10 000 MAD)'),
 (5, '2026-09-02 11:00', 'MOHAMED MAZARI', 'direction', 'approbation commande', 'commande', 1,
  'BC-2026-0001 · 23 750 MAD approuvés'),
 (6, '2026-09-20 11:00', 'Mohamed', 'direction', 'commande soldée', 'commande', 2, 'BC-2026-0002'),
 (7, '2026-09-04 12:00', 'Karim', 'achats', 'annulation réception', 'reception', 2,
  'REC-2026-0002 · camion refusé'),
 (8, '2026-09-30 12:00', 'Mohamed', 'direction', 'montage', 'metier', 1, 'M1 : PES ROUGE étage 1'),
 (9, '2026-09-01 12:00', 'Démonstration', 'ERP Fil', 'statut BC', 'BC-2026-0002', NULL, 'soldée');
INSERT INTO piece_jointe VALUES (1, 'article', 1, 'fiche.pdf', 'application/pdf', 5,
 'article/1/fiche.pdf', 'Mohamed', '2026-09-01 10:00'),
 (2, 'commande', 1, 'proforma.pdf', 'application/pdf', 5, '/chemin/disparu/proforma.pdf',
  'Mohamed', '2026-09-01 10:00'),
 (3, 'reception', 1, 'perdu.pdf', 'application/pdf', 5, 'reception/1/perdu.pdf', 'Mohamed',
  '2026-09-03 10:00');
