# Gestion MP PRO — notice

> Générée depuis `frontend/src/aide.json` par `scripts/generer_notice.py` : ne pas la modifier à
> la main. Le même texte s'affiche dans l'écran (Mode d'emploi, bouton « ? » de chaque écran,
> formules des indicateurs).

## Sur les métiers

Sur les métiers : le fil monté, pas encore tissé. C’est du stock : il compte dans le stock, sa valeur, le disponible et le stock projeté. Monter n’écrit aucun mouvement : le fil a déjà été sorti par un ordre.

## Mode d’emploi

Les règles, qui fait quoi, les gestes pas à pas, les calculs, et où est passé chaque écran de l’ERP Fil.

### Les règles qui tiennent le stock juste

1. **Les mouvements de stock sont la seule écriture de stock.** Le stock détenu, la couverture, la valeur, le plan d’achat : tout se recalcule à partir d’eux, à chaque affichage. Les soldes par lot et par magasin en sont la somme, et un contrôle vérifie à tout moment qu’ils retombent dessus (Analyse › Contrôles (`/analyse?onglet=controles`), C12).
2. **Brouillon, puis validation.** Tout document (commande, réception, sortie vers les machines, ouverture, transfert, ajustement, retour, inventaire) naît en **brouillon** : il se modifie, se supprime, et rien ne bouge au stock. La **validation** l’écrit. Le numéro de série (REC-…, OF-…, BC-…) n’est donné qu’à la validation ou à l’envoi : un brouillon supprimé ne laisse pas de trou. Avant, l’écran le désigne « Brouillon » ; un bon soumis à la direction, « À approuver ».
3. **Un document validé ne s’efface pas : il s’annule (contre-passation).** Annuler écrit l’écriture inverse, datée comme l’original, signée par qui annule ; les deux restent dans les mouvements de stock. (Les annulations reprises de l’ERP Fil portent, elles, la date de la reprise : le Bilan du mois les compte à part, sur la ligne « annulations ».) On ne réécrit jamais une écriture validée.
4. **Le stock se tient en kilos ; la commande se passe en conditionnements.** Un fil s’achète en palettes, une colle en fûts, un intrant au kilo. La matière porte son unité d’achat et sa contenance (déduite sinon : la palette si l’on connaît le poids d’une bobine et les bobines par palette, la bobine, sinon le kilo). La préparation de commande parle palettes et conteneur ; le bon écrit « 12 × Palette de 900 kg ». Le cuir, les franges et le ruban aussi se tiennent en kilos.
5. **Le cuir, les franges, le ruban : des kilos en stock, des mètres dans la recette.** Ils se pèsent à la réception, sortent vers les machines, se comptent à l’inventaire et se commandent **en kilos**, comme tout. Leur fiche porte une **densité** (kg par mètre linéaire), obligatoire. Le **prix** se saisit au kilo (par défaut) ou au mètre, au choix, sur la fiche ; tous les calculs le lisent au kilo (prix au mètre ÷ densité). La recette dit des **mètres par m²** de tapis ; la densité en fait des kilos par m², qui font les besoins, la sortie proposée, le prévu des ordres et le coût au m². Leurs mètres s’affichent à titre indicatif à côté des kilos (« 14,3 kg ≈ 1 020 ml ») : fiche, stock, sortie, besoins, plan d’achat, bon de commande.
6. **Le prix de la facture n’est pas le coût du fil.** Droits, fret, transit, port, banque s’ajoutent, et se paient à chaque livraison : le dossier d’importation suit donc la **facture** (un dossier par facture, ouvert depuis la réception qui l’a apportée), pas la commande. Il porte ces frais et les répartit sur les marchandises, à la valeur ou au poids selon le poste de frais. La TVA, récupérable, reste hors du coût : c’est le **Coût hors TVA** (le coût de revient) qui valorise le stock ; le **Coût TTC** dit ce qui a été décaissé.
7. **Le lot sur toutes les écritures, l’ordre sur les sorties.** Le lot dit *d’où vient* la matière (fournisseur, réception, dossier), l’ordre de fabrication (OF-…) dit *dans quoi elle est partie*. L’un sans l’autre laisse la moitié de la question sans réponse. Un fournisseur sans numéro de lot : « Lot interne » en donne un.
8. **Une référence de fil se compose de quatre parties.** Composition (PP, PES…), type de fil (frisé, shrink…), titrage (2900 Dtex…), couleur : quatre listes tenues en référentiels (Classification (`/catalogue?onglet=classification`)), qui composent la référence à la saisie et servent à chercher un fil sans connaître sa référence par cœur.
9. **Le stock est dans les magasins ou sur les métiers.** Sur les métiers : le fil monté, pas encore tissé. C’est du stock : il compte dans le stock, sa valeur, le disponible et le stock projeté. Monter n’écrit aucun mouvement : le fil a déjà été sorti par un ordre. Un fil monté à un étage pèse mètres × densité × poids d’une bobine × pourcentage. Le stock de l’usine, et sa valeur, sont ceux des magasins plus ceux des métiers ; le disponible et le stock projeté comptent aussi le fil sur les métiers : on ne rachète pas ce qui est déjà dans le cantre. Le détail magasins / métiers se lit sur la fiche matière, le Cockpit, la Valorisation et Métiers à tisser. Il revient au magasin par un retour des machines. Un fil monté sans sortie enregistrée est encore compté au magasin (contrôle C25).
10. **La devise appartient au prix, pas au fournisseur.** Un fournisseur peut facturer la colle en euros et la chaîne en dollars. Les montants ne s’additionnent jamais entre devises : un bon de commande part par devise, et les totaux se font en MAD. Le cours est figé à la confirmation des prix d’une commande ; un dossier d’importation porte le cours de la banque.
11. **Deux horloges.** L’**historique est figé** : ce qui a été saisi l’a été à sa date. La **projection est glissante** : le plan, les besoins et les alertes se recalculent sur les douze mois à venir, à partir d’aujourd’hui (l’heure de l’usine, celle du serveur), à chaque ouverture.
12. **Le stock ne passe jamais sous zéro.** À plusieurs sur la même palette, le second lit le solde à jour et est refusé s’il ne reste pas assez. La matière en **quarantaine** est détenue mais pas disponible : comptée dans le stock et sa valeur, elle n’est ni proposée aux machines, ni comptée dans le disponible, le stock projeté et la couverture ; elle se libère par un transfert motivé.
13. **Les dates tiennent.** Pas d’écriture dans le futur ; une **période close** (Réglages › Période close (`/reglages?onglet=periode`)) ne bouge plus ; pendant un **inventaire**, le périmètre compté ne bouge plus ; un ordre de fabrication ne se valide pas à une date antérieure au dernier ordre validé.
14. **Chaque geste est signé.** Chacun a son compte : tout ce qui s’enregistre porte son nom (colonne « Par »), chaque fiche a son « Historique », et le Journal des actions (`/administration?onglet=journal`) garde qui a fait quoi, sur quoi, et quand, avec l’avant et l’après. Le serveur refuse ce que le menu cache : un rôle ne peut pas faire par une autre porte ce que son écran ne propose pas.

### Qui fait quoi

#### Direction

- Voit et peut tout le métier. Le Cockpit (`/cockpit`) réunit ce qui demande une décision : commandes à approuver, ruptures, retards, prix à confirmer, brouillons, contrôles, sauvegarde.
- Approuve les commandes au-delà du seuil réglé (le bon s’ouvre en entier, puis « Approuver ») ou les renvoie aux achats.
- Règle les Réglages (`/reglages`) (paramètres de calcul, devises, magasins, postes de frais, codes douaniers, période close) et l’Administration (`/administration`) (comptes, appareils, sauvegardes, journal des actions). Règle les métiers (laize, étages, densité) et saisit le plan de production.

#### Achats

- Plan d’achat, commandes, réceptions (avec le poids des bobines et l’archive des pesées), importations et coût de revient, inventaire, ouvertures, transferts, ajustements, retours au fournisseur.
- Matières, classification, fournisseurs ; qualités et recettes en lecture ; production en lecture.
- L’Analyse (`/analyse`) : prix, opportunités d’économies, fournisseurs, valorisation, coût de revient, contrôles.
- Réglages (`/reglages?onglet=devises`) en lecture, devises en écriture ; ni comptes, ni sauvegardes, ni approbation des commandes.

#### Alimentation des machines

- Au téléphone (écran atelier (`/atelier`)) : envoyer aux machines (qualité et m², les fils et les lots sont proposés), retour des machines, trouver un lot (mots ou QR), déplacer un lot, monter un fil, signaler un besoin.
- Au bureau : sorties vers les machines, Opérations de stock (`/operations?onglet=transfert`) (transferts et retours des machines), stock et lots, matières en lecture, métiers à tisser (monter les fils), production en lecture. Les ouvertures, ajustements et retours au fournisseur restent aux achats.
- Ne voit ni les prix, ni les montants, ni les budgets, ni le pilotage des achats.

#### Administrateur technique

- Tient l’Administration (`/administration`) : comptes, appareils de l’atelier, sauvegardes et restauration, journal des actions, courriel, serveur, accès au téléphone.
- Ne voit aucune donnée métier : ni stock, ni commandes, ni prix.

### Pas à pas

#### Passer une commande depuis le plan (`/plan-achat`)

1. Plan d’achat › Par fournisseur : les fournisseurs sont classés par budget, les matières par urgence.
2. « Préparer la commande » ouvre l’arbitrage : quantité suggérée en kilos et dans l’unité de commande (palette, fût, sac…), palettes par conteneur.
3. Créer le bon : il part sans les prix, un bon par devise, en brouillon.
4. Commandes › Brouillons : relire, puis « Envoyer » (au-delà du seuil, la direction approuve d’abord).
5. Au retour du fournisseur : « Saisir les prix », puis « Confirmer ces prix » : ils vont au bon et au catalogue, le cours est figé.
6. Suivre l’expédition : proforma, acompte, embarquement, ETA, port, dédouanement, arrivée usine. L’ETA remplace la date prévue dans la projection.

#### Commander sans passer par le plan (`/commandes/nouvelle`)

1. Commandes › « Nouvelle commande », choisir le fournisseur.
2. La préparation s’ouvre avec ce que Gestion MP PRO suggère : ajuster, ou tout mettre à zéro.
3. Dans le bon en brouillon, ajouter les matières de ce fournisseur qui manquent.

#### Réceptionner une livraison (`/receptions/nouvelle`)

1. Réceptions › Nouvelle réception : le fournisseur (ou taper le n° du bon de commande), cocher les bons que le camion apporte.
2. Pour chaque lot : son numéro (ou « Lot interne »), l’Annoncé BL (kg), la pesée (c’est elle qui fait foi), palettes et bobines, le magasin.
3. Conforme → magasin ; sous réserve → quarantaine ; refusé → n’entre pas.
4. Enregistrer crée un brouillon, qui se modifie et se remet à jour seul. Valider fait entrer le stock et écrit le prix.
5. Imprimer les étiquettes QR des lots.

#### Monter un fil sur un métier (`/metiers`)

1. Métiers à tisser : choisir le métier (laize d’un étage, nombre d’étages, densité, réglés par la direction).
2. Choisir l’étage, chercher le fil, saisir les mètres montés et le pourcentage.
3. L’écran calcule bobines = mètres × densité × pourcentage, poids = bobines × kg / bobine. Sur les métiers : le fil monté, pas encore tissé. C’est du stock : il compte dans le stock, sa valeur, le disponible et le stock projeté. Monter n’écrit aucun mouvement : le fil a déjà été sorti par un ordre. Deux fils qui se partagent les mêmes mètres (60 et 40 %) n’occupent qu’une fois la laize.
4. Le fil monté doit avoir été sorti vers les machines : sinon le magasin le compte encore (contrôle C25).

#### Sortir de la matière pour un ordre (`/ordres/nouveau`)

1. Au téléphone : « Envoyer aux machines » ; au bureau : Sorties vers les machines › Nouvelle sortie.
2. Dire ce qu’on tisse : une ou plusieurs qualités en service et leurs m². Les recettes donnent les fils et les kilos ; les lots les plus anciens présents à la date de l’ordre sont proposés (un ordre daté d’hier ne prend pas un lot arrivé ce matin).
3. Corriger au réel (kg, bobines ou palettes), ajouter un fil hors recette si besoin.
4. Valider : le stock baisse, l’ordre reçoit son numéro OF. Un retour se saisit ensuite contre cet ordre, daté au plus tôt du jour de l’ordre. Annuler l’ordre annule aussi ses retours, ceux repris de l’ERP Fil compris.

#### Savoir ce qu’un fil a coûté (`/analyse?onglet=revient`)

1. Analyse › Coût de revient (ou Importations) : chercher par référence, composition, titrage, couleur, qualité, fournisseur, période.
2. Plusieurs combinaisons d’un coup : composer « PES + 1500 », « + Ajouter cette combinaison », puis « PP + 1800 ».
3. À lire : Achat (la facture), Charges hors TVA, Coût hors TVA au kilo, TVA, Coût TTC.
4. Dans le temps : Analyse › Matrice, puis « Courbe » sur la ligne du fil.

#### Retrouver d’où vient un fil (`/stock?onglet=lots`)

1. Lire le QR de la palette, ou taper quelques mots : la fiche du lot s’ouvre (où il est, combien, son histoire).
2. Fiche du lot › « Où ce lot est-il allé ? » : le chemin d’un lot, de la réception aux ordres qu’il a servis. Stock › Ordres de fabrication : les lots partis dans un ordre.
3. Un tapis qui revient ? Son ordre donne les lots ; les lots donnent les autres ordres concernés.

#### Faire l’inventaire (`/inventaires/nouveau`)

1. Inventaire › Ouvrir : choisir le périmètre ; le stock théorique est figé, les mouvements du périmètre compté sont suspendus.
2. Compter, saisir en palettes, bobines ou kilos. Au-delà de la tolérance, l’écart se justifie.
3. Valider : un ajustement par écart est écrit aux mouvements de stock, le périmètre reprend vie.

#### Le point hebdomadaire (`/cockpit`)

1. Analyse › Contrôles : aucun bloquant ? Chaque anomalie dit quoi faire.
2. Cockpit (direction) ou Ma journée (achats) : ruptures, retards, prix à confirmer, brouillons à valider.
3. Analyse › Matrice : quels prix ont bougé ? Opportunités d’économies : quelle négociation ouvrir ?
4. Plan d’achat : ce qu’il faut engager cette semaine. Analyse › Échéancier : ce qu’il faudra payer.
5. Administration › Sauvegardes : la dernière (de cette base) a moins d’un jour.
6. En début de mois : Cockpit › « Bilan du mois » (le mois écoulé, à imprimer) et Cockpit › Évolution.

### Les calculs à connaître

| Grandeur | Comment elle est obtenue |
|---|---|
| Besoin matière du mois | (1 + taux de perte) × Σ des recettes : kg / m² de chaque fil × m² planifiés ce mois-là. Pour le cuir, les franges, le ruban : kg / m² = ml / m² de la recette × densité de la matière. |
| Prix au kilo | Le prix de la fiche s’il est au kilo ; s’il est au mètre, prix ÷ densité (kg / ml). La valeur du stock, le coût moyen, le coût au m² et le budget d’achat le lisent au kilo. |
| Besoin retenu | Le besoin du plan corrigé par le réel : sorties nettes des trois derniers mois clos ÷ ce que le plan et les recettes de l’époque prévoyaient (un plan changé en cours de mois compte pour ses jours), borné entre 0,5 et 1,5 ; pas de baisse pour un fil en rupture. Un fil qui en remplace un autre dans une recette prend le coefficient de l’ancien. Un fil consommé hors de toute recette se prévoit sur ce qui sort, sauf un fil sorti des recettes dans l’année, que l’atelier finit. |
| Stock détenu | Le stock est dans les magasins (stock courant + quarantaine) ou sur les métiers. Sur les métiers : le fil monté, pas encore tissé. C’est du stock : il compte dans le stock, sa valeur, le disponible et le stock projeté. Monter n’écrit aucun mouvement : le fil a déjà été sorti par un ordre. Disponible = magasins hors quarantaine, plus le fil sur les métiers : c’est lui qui décide de ce qu’il faut commander. |
| Fil sur les métiers | Un fil monté à un étage pèse mètres × densité × poids d’une bobine × pourcentage. Sur les métiers : le fil monté, pas encore tissé. C’est du stock : il compte dans le stock, sa valeur, le disponible et le stock projeté. Monter n’écrit aucun mouvement : le fil a déjà été sorti par un ordre. Il revient au magasin par un retour des machines. |
| Stock projeté | Stock disponible + commandé attendu dans le délai − demande pendant le délai du fournisseur : ce qu’il restera quand arrivera une commande passée aujourd’hui. Un bon en brouillon ou à approuver n’y compte pas (il n’est pas parti). |
| Sorties prévues | La demande entre la livraison et la commande suivante : ce que la commande doit couvrir. |
| Seuil d’alerte | Le plus grand de : stock minimum de la fiche (plafonné à N mois de la consommation à venir ; aucun pour une matière non consommée), couverture minimum de la fiche × (1 + marge de sécurité), jours de sécurité de la classe ABC. Le délai du fournisseur n’y est plus : il est déjà retiré du stock projeté. |
| Statut (au seuil) | RUPTURE (plus rien), CRITIQUE, URGENT, ATTENTION, OK : le stock projeté face au seuil d’alerte. |
| Matières en alerte | Trois comptes nommés, servis par le serveur : « alerte rouge » = en rupture ou critiques (pastille du menu, bandeaux) ; « à commander vite » = rupture, critiques et urgentes (Ma journée) ; « en alerte » = les quatre statuts RUPTURE, CRITIQUE, URGENT, ATTENTION (onglet Matières en alerte). |
| Statut de couverture | La couverture en jours face aux réglages « couverture critique » et « couverture d’ATTENTION ». |
| Couverture | Stock projeté ÷ consommation journalière. Couverture pondérée (Cockpit) : la même, pondérée par la valeur. |
| Quantité à commander | Sorties prévues + le plus grand de (sécurité de la classe sur la période, seuil d’alerte) − stock projeté − commandé arrivant pendant la période couverte − déjà en préparation (bons en brouillon ou à approuver), portée au minimum de commande et arrondie au conditionnement. Sous le gramme : rien. Une matière désactivée, d’un fournisseur désactivé, ou non consommée ne se rachète pas. |
| Classe ABC | Sur la valeur consommée par an, en MAD : jusqu’à 80 % cumulés → A, jusqu’à 95 % → B, sinon C (réglables). |
| Classe XYZ | Sur la régularité de la demande mensuelle : coefficient de variation sous 0,25 → X, sous 0,5 → Y, sinon Z (réglables). |
| Valeur du stock (CMUP) | Coût moyen unitaire pondéré, recalculé à chaque entrée au Coût hors TVA (frais d’importation compris quand le dossier est saisi), appliqué au stock détenu (magasins et sur les métiers, quarantaine comprise) ; à défaut d’achat, au prix du catalogue. Le Cockpit et la Valorisation disent « dont X sur les métiers ». |
| Coût hors TVA d’une marchandise | Valeur au cours de la banque + sa part des charges non récupérables (droits, fret, transit…), à la valeur ou au poids selon le poste. La TVA est à part (Coût TTC). |
| Opportunité d’économies | (prix actuel − prix du comparable le moins cher) × consommation annuelle, entre fils de même composition, type et titrage, payés à la même époque, au coût rendu usine. |
| OTIF | Une réception est parfaite si elle est à l’heure, complète (à la tolérance près) et conforme. À l’heure se juge sur la date promise du bon (l’ETA ne la repousse pas). Score fournisseur = OTIF × 60 + jusqu’à 20 points pour peu de retours (0 dès 5 % renvoyés) + jusqu’à 20 pour un délai court. |
| Rotation du stock | Ce que l’atelier a consommé sur les douze derniers mois clos, au coût moyen (CMUP), ÷ valeur du stock au coût moyen, les deux sur la même base. Sans consommation encore : le plan au prix du catalogue, face au stock au catalogue. Le stock couvre 365 ÷ rotation jours de consommation. |
| Cycle de trésorerie | Jours de stock + délai client − délai de paiement fournisseur (pondéré par les montants). |

Les seuils, taux et tolérances se règlent dans Réglages › Paramètres (`/reglages?onglet=parametres`) (direction) ; chaque changement est daté et recalcule tout le pilotage. Les indicateurs des écrans disent la même formule dans leur « ? ».

### L’analyse : une question par onglet

Menu « Analyse ». Chaque liste s’exporte en Excel ; chaque onglet a son adresse, à garder en favori.

| Onglet | Ce qu'on y lit |
|---|---|
| Valorisation (`/analyse?onglet=valorisation`) | Ce que vaut le stock détenu (magasins et sur les métiers), au coût moyen pondéré, dont le fil sur les métiers ; l’écart avec le catalogue. |
| Matrice (`/analyse?onglet=matrice`) | Le prix de chaque fil mois par mois, dans la monnaie de la facture, coloré face au précédent (baisse, stable, hausse, forte hausse). Filtres liés, courbe d’un fil, comparaison de plusieurs fils sur une même courbe à la couleur du fil. |
| Prix payés (`/analyse?onglet=historique`) | Chaque prix payé, son précédent et son évolution, le plus récent d’abord. |
| Opportunités d’économies (`/analyse?onglet=opportunites`) | Les fils comparables (même composition, type, titrage et, par défaut, même couleur) qui coûtent moins cher ailleurs à la même époque, au coût rendu usine ; et ce qui a été écarté (prix non datés, trop éloignés). |
| Fournisseurs (`/analyse?onglet=fournisseurs`) | OTIF, retours, écart de pesée, score sur 100, classement et action conseillée ; les réceptions notées une à une. |
| Coût de revient (`/analyse?onglet=revient`) | Ce que chaque fil a coûté rendu usine, par référence, caractéristique, qualité ou période. |
| Échéancier (`/analyse?onglet=echeancier`) | Ce qu’il faudra payer, et quand : factures des fournisseurs et frais d’importation, en retard en rouge, par mois ; et ce qui est dû sans échéance (« À dater »). |
| Contrôles (`/analyse?onglet=controles`) | Trente-huit vérifications de cohérence, chacune avec ses lignes fautives et ce qu’il faut faire. |
| Production (`/analyse?onglet=production`) | Le sorti net de chaque ordre face au prévu par la recette. Le plan et le réalisé par qualité sont dans Production & besoins. |

### Où est passé chaque écran de l’ERP Fil

| Écran de l'ERP Fil | Dans Gestion MP PRO | Ce qui a changé |
|---|---|---|
| Cockpit | Cockpit (direction) · Ma journée (achats, alimentation) (`/cockpit`) | Les mêmes chiffres, plus ce qui attend une décision, l’Évolution jour après jour et le Bilan du mois. |
| Stock | Stock, lots & mouvements › Par matière (`/stock`) | Toutes les colonnes de couverture, filtrables, exportables. |
| Plan d’achat | Plan d’achat (`/plan-achat`) | Par fournisseur, par référence, et la préparation de commande. |
| Production & besoins | Production & besoins (`/production`) | Plan, plan glissant, plan et réalisé, besoins matière. |
| Métiers à tisser | Métiers à tisser (`/metiers`) | L’alimentation y monte les fils ; la direction règle le métier. |
| Mouvements (journal) | Stock › Mouvements de stock (`/stock?onglet=mouvements`) | Les mouvements de stock, filtrés, exportables ; chaque n° de document mène à son document. |
| Mouvements (saisie) | Ouvertures, transferts, ajustements (`/operations`) | Ouvertures, transferts, ajustements, retours : un document par geste, en brouillon puis validé. |
| Bon de sortie | Sorties vers les machines · écran atelier (`/sorties`) | Au bureau ou au téléphone ; l’ordre (OF) à la validation. |
| Commandes | Commandes (`/commandes`) | Approbation, prix confirmés, suivi d’expédition, bon imprimable et Excel, historique. |
| Réceptions | Réceptions (`/receptions`) | Avec les réclamations, le poids des bobines et l’archive des pesées. |
| Lots & traçabilité | Stock › Lots · Ordres de fabrication (`/stock?onglet=lots`) | Fiche de lot, QR, chemin de la matière dans les deux sens. |
| Importations | Importations & coût de revient (`/importations`) | Un dossier par facture, ouvert depuis la réception ; ses frais, sa répartition. |
| Coût de revient | Analyse › Coût de revient (`/analyse?onglet=revient`) | La même recherche, combinable. |
| Inventaire | Inventaire (`/inventaire`) | Comptage sur un périmètre, écarts justifiés, ajustements à la validation. |
| Catalogue | Matières, classification, fournisseurs › Matières (`/catalogue`) | La référence se compose depuis la classification. |
| Classification des fils | Matières, classification, fournisseurs › Classification (`/catalogue?onglet=classification`) | Compositions, types, titrages, couleurs. |
| Fournisseurs | Matières, classification, fournisseurs › Fournisseurs (`/catalogue?onglet=fournisseurs`) | La fiche ; le score est dans Analyse › Fournisseurs. |
| Qualités & recettes | Qualités et recettes (`/qualites`) | Poids par rôle, recette à 100 % par rôle, versions, coût au m². |
| Valorisation du stock | Analyse › Valorisation (`/analyse?onglet=valorisation`) | Le stock détenu (magasins et sur les métiers), au coût moyen pondéré, dont X sur les métiers. |
| Prix & matrice | Analyse › Matrice · Prix payés · Opportunités (`/analyse?onglet=matrice`) | Trois onglets au lieu de trois vues dans un écran. |
| Contrôles | Analyse › Contrôles (`/analyse?onglet=controles`) | Chaque contrôle dit quoi faire ; la pastille du menu y mène. |
| Paramètres | Réglages · Administration (`/reglages`) | Réglages (Paramètres, Devises, Magasins, Frais, Douane, Période) · Administration (Comptes, Appareils, Sauvegardes, Journal des actions, Courriel, Serveur, Téléphone). |
| Guide | Mode d’emploi (`/aide`) | Cette page. |
| — (nouveau) | Administration › Comptes · Journal des actions (`/administration?onglet=comptes`) | Chacun son compte et son rôle ; qui a fait quoi. |
| — (nouveau) | Écran atelier (téléphone) (`/atelier`) | Envoyer, retour, trouver un lot, déplacer, monter un fil, signaler un besoin, au pied du métier. |

Les écrans que votre rôle ne voit pas sont indiqués sans lien.

### Gestion MP PRO sur le téléphone

1. **Dans l’usine (Wi-Fi)** : ouvrir dans le navigateur du téléphone l’adresse HTTPS du serveur (Administration › Téléphone (`/administration?onglet=telephone`) donne l’adresse exacte et un QR).
2. **Enrôler le téléphone** : Administration › Appareils crée un QR à usage unique (15 minutes) ; le lire avec le téléphone. Un téléphone enrôlé montre les visages à la connexion ; ailleurs, on tape son identifiant.
3. **Partout (4G / 5G)** : installer l’application gratuite *Tailscale* sur le serveur et sur le téléphone, connectées au même compte. Le serveur n’est jamais exposé sur Internet.
4. Dans le navigateur, *Partager › Sur l’écran d’accueil* (iPhone) ou *Ajouter à l’écran d’accueil* (Android) : Gestion MP PRO s’ouvre ensuite d’un toucher, comme une application. Il faut le réseau : rien n’est gardé sur le téléphone.
5. L’appareil photo lit les étiquettes QR des palettes et ouvre directement la fiche du lot.

## L'aide de chaque écran

### Ma journée (`/accueil`)

Ce qui attend aujourd’hui : les tâches à faire, ce qui est à valider, les arrivées des sept prochains jours et les besoins signalés par l’atelier.

- Chaque tâche ouvre son document s’il est seul, la liste filtrée sinon.
- Achats : commandes en retard, prix à confirmer, brouillons à envoyer, réceptions à valider, factures sans dossier d’importation.
- Alimentation au bureau : les sorties en brouillon, les retours à saisir, les besoins signalés et leur réponse.

### Cockpit (`/cockpit`)

Ce qui demande une décision de la direction : à faire et à valider, matières en alerte, vue d’ensemble, évolution, opportunités d’économies.

- Six indicateurs ; chacun dit sa formule (« ? ») et s’ouvre sur sa liste.
- « Bilan du mois » imprime le mois écoulé sur le papier à en-tête.
- Sur les métiers : le fil monté, pas encore tissé. C’est du stock : il compte dans le stock, sa valeur, le disponible et le stock projeté. Monter n’écrit aucun mouvement : le fil a déjà été sorti par un ordre.

### Stock, lots & mouvements (`/stock`)

Le stock par matière, lot par lot, chaque mouvement de stock, les ordres de fabrication, et ce qui attend d’être validé.

- Le stock se tient en kilos ; le cuir, les franges et le ruban disent aussi leurs mètres, à titre indicatif.
- Sur les métiers : le fil monté, pas encore tissé. C’est du stock : il compte dans le stock, sa valeur, le disponible et le stock projeté. Monter n’écrit aucun mouvement : le fil a déjà été sorti par un ordre.
- La pastille du menu compte l’alerte rouge : matières en rupture ou critiques.

### Sorties vers les machines (`/sorties`)

Les ordres de fabrication : ce qui est sorti du magasin pour chaque qualité tissée, et ce qui en est revenu.

- Les lots les plus anciens présents à la date de l’ordre sont proposés.
- Un retour se saisit contre son ordre ; annuler l’ordre annule ses retours.
- Le numéro OF est donné à la validation.

### Production & besoins (`/production`)

Le plan de production, le plan glissant, le plan face au réalisé, et les besoins matière qui en découlent.

- La direction saisit le plan ; une saisie non enregistrée est gardée en changeant d’onglet.
- Le besoin d’une matière dit d’où il vient : qualités, mètres carrés, recettes.

### Écran atelier (téléphone) (`/atelier`)

Au pied du métier : envoyer aux machines, retour des machines, trouver un lot (mots ou QR), déplacer un lot, monter un fil, signaler un besoin.

- Une tâche par écran, de grands boutons ; la saisie en cours est gardée sur le téléphone jusqu’à l’enregistrement.
- Ce qui sera refusé (inventaire en cours, date, quarantaine) est dit en tête, et « Valider » est grisé avec la raison écrite dessous.
- Aucun prix ni montant n’y est jamais montré.

### Plan d’achat (`/plan-achat`)

Ce qu’il faut commander, par fournisseur et par référence, et la préparation de la commande en kilos et en conditionnements.

- Les fournisseurs sont classés par budget, les matières par urgence.
- « Préparer la commande » ouvre l’arbitrage ; les bons partent en brouillon, un par devise.

### Commandes (`/commandes`)

Les bons de commande, du brouillon au solde : approbation, envoi, prix confirmés, suivi de l’expédition, réceptions, pièces jointes.

- Un brouillon n’a pas de numéro ; il le reçoit à l’envoi. Au-delà du seuil, la direction approuve d’abord.
- Le bon fournisseur s’imprime en anglais, sans prix, sur le papier à en-tête.
- « Confirmer ces prix » fige le cours et met à jour le catalogue.

### Réceptions (`/receptions`)

La saisie d’un camion (pesées, lots, magasins), sa validation, les réclamations au fournisseur, le poids des bobines et l’archive des pesées.

- La pesée fait foi ; l’Annoncé BL (kg) est celui du bon de livraison.
- Conforme → magasin ; sous réserve → quarantaine ; refusé → n’entre pas.
- Un brouillon se modifie, se supprime et se remet à jour seul ; la validation fait entrer le stock.

### Importations & coût de revient (`/importations`)

Un dossier d’importation par facture : ses marchandises, ses frais répartis, son échéancier, ses pièces ; ce que chaque fil a coûté rendu usine.

- Le dossier s’ouvre depuis la facture apportée par une réception.
- Coût hors TVA (le coût de revient) = achat au cours de la banque + charges non récupérables ; la TVA est à part (Coût TTC).
- Les frais non répartis sont dits à part, partout.

### Inventaire (`/inventaire`)

Ouvrir un inventaire sur un périmètre, compter à l’aveugle, justifier les écarts au-delà de la tolérance, valider : un ajustement par écart.

- Pendant l’inventaire, les mouvements des matières comptées sont suspendus dans son magasin (dans tous s’il est global) ; les autres matières continuent de bouger. Un seul inventaire ouvert par magasin.
- Le stock théorique est figé à l’ouverture ; la **feuille de comptage** s’imprime sans lui (à l’aveugle), la **feuille de recomptage** avec lui, pour les lots hors tolérance enregistrés.
- Au-delà de la tolérance, un écart se justifie (3 caractères au moins) et se recompte par une autre personne : un recomptage fait par la même personne, ou par celle qui a ouvert l’inventaire, est signalé.
- Un lot trouvé sur place s’ajoute au comptage ; il n’est créé qu’à la validation (« Lot interne » : numéro LOT-AAAA-NNNN donné à ce moment).
- Abandonner garde l’inventaire et son numéro, avec un motif ; un inventaire validé ne se défait que par son annulation (contre-passation, motif exigé), et passe « Annulé ».

### Ouvertures, transferts, ajustements (`/operations`)

Un document par geste de stock : stock d’ouverture, transfert (dont quarantaine), ajustement, retour au fournisseur, retour des machines — en brouillon, puis validé.

- L’alimentation y fait ses transferts (mise en quarantaine comprise, en disant ce qui est douteux) et ses retours des machines ; libérer une quarantaine est une décision des achats ou de la direction.
- Ce qui ferait refuser la validation est dit d’avance (« sera refusée ») : inventaire en cours sur la matière, lot épuisé, date, quarantaine.
- Le numéro est donné à la validation ; un document validé ne s’efface pas : il s’annule (contre-passation).

### Matières, classification, fournisseurs (`/catalogue`)

Les matières (la référence se compose depuis la classification), les quatre listes de la classification, et les fournisseurs.

- Une référence de fil : composition, type de fil, titrage, couleur.
- Le stock se tient en kilos ; le cuir, les franges et le ruban portent une densité (kg par mètre).
- Une fiche modifiée entre-temps par quelqu’un d’autre est refusée : « Recharger » repart de sa dernière version.
- L’alimentation lit les matières, sans prix.

### Qualités et recettes (`/qualites`)

Les qualités de tapis, leur poids par rôle, leur recette à 100 % par rôle, leurs versions et leur coût au m².

- Une recette se juge sur la version de son époque.
- Le cuir, les franges et le ruban se disent en mètres par m² dans la recette.

### Métiers à tisser (`/metiers`)

Les métiers, leurs étages et les fils montés ; la direction règle le métier, l’alimentation monte les fils.

- Sur les métiers : le fil monté, pas encore tissé. C’est du stock : il compte dans le stock, sa valeur, le disponible et le stock projeté. Monter n’écrit aucun mouvement : le fil a déjà été sorti par un ordre.
- Un fil monté sans sortie enregistrée est encore compté au magasin (contrôle C25).

### Analyse (`/analyse`)

Une question par onglet : la valeur du stock, les prix et leur évolution, les opportunités d’économies, les fournisseurs, le coût de revient, l’échéancier, les contrôles et la production.

- Chaque liste s’exporte en Excel avec ses filtres ; chaque onglet a son adresse.
- Les montants ne s’additionnent jamais entre devises : un axe ou un panneau par devise.
- La pastille du menu compte les contrôles à corriger ; elle mène à l’onglet Contrôles.

### Réglages (`/reglages`)

Les paramètres de calcul, les devises et leurs cours, les magasins, les postes de frais, les codes douaniers et la période close.

- La direction règle tout ; les achats tiennent les devises et lisent le reste.
- Chaque changement de paramètre est daté, signé et recalcule tout le pilotage.

### Administration (`/administration`)

Les comptes, les appareils de l’atelier, les sauvegardes, le journal des actions, le courriel du lundi, l’état du serveur et l’accès au téléphone.

- Comptes : un compte par personne ; l’alimentation a un code d’exactement 4 chiffres, les achats et la direction 8 caractères au moins, l’administrateur technique 12.
- Appareils : un téléphone enrôlé (QR à usage unique, 15 minutes) montre les visages à la connexion ; ailleurs, on tape son identifiant.
- Sauvegardes : la dernière a moins d’un jour ; une restauration se confirme puis se relit dans une fenêtre (« J’ai compris »).
- Journal des actions : qui a fait quoi, sur quoi, et quand, avec l’avant et l’après.

### Mode d’emploi (`/aide`)

Les règles qui tiennent le stock juste, qui fait quoi, les gestes pas à pas, les calculs, l’analyse, où est passé chaque écran de l’ERP Fil, et le téléphone.

- Un onglet par question ; l’onglet ouvert est dans l’adresse, à garder en favori.
- Les écrans que votre rôle ne voit pas sont indiqués sans lien.
- Le bouton « ? » de chaque écran ouvre l’aide de cet écran.

### Connexion

Touchez votre nom, puis tapez votre code ; hors du poste de l’usine et des téléphones enrôlés, tapez votre identifiant.

- L’alimentation entre au 4e chiffre ; les autres valident par Entrée.
- Cinq essais manqués font patienter, de plus en plus longtemps (30 secondes, puis le double, 15 minutes au plus).
- Code oublié : la direction ou l’administrateur le remet à zéro dans Administration › Comptes.

### Fiche de lot (`/lots/:id`)

Où est le lot, combien il en reste, d’où il vient, quels ordres il a servis ; la libération de quarantaine et l’étiquette QR.

- « Où ce lot est-il allé ? » ouvre la traçabilité.
- Libérer une quarantaine est une décision des achats ou de la direction, après contrôle de la matière.
- L’étiquette QR mène au téléphone à la fiche de l’atelier, au bureau à cette fiche.

### Fiche fournisseur (`/fournisseurs/nouveau`)

Un fournisseur : identité et contact, approvisionnement (délai, couverture, devise, incoterm, port), paiement, ses pièces jointes et son historique ; ses indicateurs (matières, délai mesuré, OTIF, score).

- Le délai et la couverture règlent le plan d’achat ; une couverture à 0 suit le réglage général.
- Le délai passe en attention quand le délai mesuré dépasse de plus de 20 % le déclaré, sur trois livraisons au moins : corriger la fiche.
- Un fournisseur qui a servi (matières, commandes, réceptions, lots, opérations, factures, pièces) se désactive ; « Supprimer » dit ce qui l’en empêche.
- Si la fiche a été modifiée entre-temps sur un autre poste, l’enregistrement est refusé : « Recharger la fiche » repart de sa dernière version.

### Fiche matière (`/matieres/nouvelle`)

Une matière du catalogue : sa classification et sa référence, son achat (fournisseur, prix, unité d’achat, code douanier), son conditionnement et son stock minimum, ses pièces jointes et son historique.

- La référence se compose seule depuis la classification (composition, type de fil, titrage, couleur, code couleur, suffixe du fournisseur) tant qu’on ne la retouche pas ; une valeur qui manque s’ajoute sur place.
- Le prix se dit au kilo, ou au mètre : il est alors ramené au kilo par la densité. Le stock et tous les calculs sont au kilo ; les mètres d’un cuir, de franges, d’un ruban sont affichés à titre indicatif.
- Une unité d’achat vide est déduite : la palette si le poids d’une bobine et les bobines par palette sont connus, sinon la bobine, sinon le kilo.
- Désactiver ne touche qu’à l’état : une matière qui a servi se désactive, elle ne se supprime pas ; le bouton « Supprimer » dit ce qui l’en empêche.
- Si la fiche a été modifiée entre-temps sur un autre poste, l’enregistrement est refusé : « Recharger la fiche » repart de sa dernière version.
- L’alimentation lit la fiche sans rien de l’achat : ni prix, ni devise, ni minimum de commande.

### Fiche qualité (`/qualites/nouvelle`)

Une qualité de tapis : sa fiche et ses poids au m² en tête de sa recette, la recette rôle par rôle, son plan de production (en lecture), les versions de sa recette et son historique.

- Dans chaque rôle utilisé, les parts des matières font 100 % (à 0,01 point près) ; un rôle qui pèse sans matière manque aux besoins et aux sorties.
- Le cuir, les franges et le ruban se disent en mètres par m² : leurs kg/m² se calculent par la densité de la matière. Les mètres restent indicatifs, le stock est en kilos.
- Fiche, poids et recette s’enregistrent ensemble, en une fois ; une qualité arrêtée accepte une recette incomplète, avec un avertissement.
- Chaque changement de matières ou de poids crée une version signée ; une version vaut à partir de son enregistrement (pas de date d’effet). « Revenir à cette version » demande un motif.
- Le plan se saisit dans la page Production (`/production?onglet=plan`), toutes qualités ensemble.
- Les achats lisent la fiche ; l’alimentation la lit sans coût ni prix.

### Le catalogue par tableur (`/catalogue/tableur`)

Télécharger le catalogue en tableur, le corriger dans Excel, le relire : l’aperçu dit ce qui sera créé, modifié ou refusé, avant toute écriture.

- Une case vide ne change rien ; pour vider une case, nommer sa colonne dans « Vider ».
- Chaque ligne passe par les mêmes contrôles que la fiche ; un tableur en erreur n’écrit rien.
- « Appliquer » écrit exactement ce que l’aperçu a montré : si le catalogue a changé depuis, il refuse ; relire alors le tableur.
- Aucune matière n’est supprimée par le tableur.

### Mon compte (`/compte`)

Votre nom, votre identifiant, votre rôle et votre courriel ; changer votre code ; l’apparence de l’écran.

- Changer son code demande l’ancien ; vos autres sessions sont alors fermées.
- L’alimentation a un code d’exactement 4 chiffres ; les achats et la direction 8 caractères au moins ; l’administrateur technique 12.
- L’apparence (claire, sombre, ou celle du poste) ne vaut que pour ce navigateur.

### Première installation

Au tout premier lancement, aucun compte n’existe : on crée celui de la direction, qui crée ensuite les autres comptes (Administration › Comptes).

- L’identifiant retenu est annoncé sous le champ.
- Le code de la direction fait 8 caractères au moins.

### Suivi de traçabilité (`/tracabilite`)

Le chemin de la matière dans les deux sens : d’un lot aux ordres qu’il a servis, d’un ordre aux lots qu’il a pris.

- « Entré » est ce qui a été reçu ; les retours se déduisent du sorti ; les annulations sont marquées.
