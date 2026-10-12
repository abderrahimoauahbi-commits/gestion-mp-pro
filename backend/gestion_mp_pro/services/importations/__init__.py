"""Dossiers d'importation : ce que la marchandise coûte rendue à l'usine (lot D7).

Le dossier s'ouvre depuis la facture d'une réception validée et en prend toute la marchandise
(I3) ; un second camion d'une de ses factures rejoint son dossier ; une réception sans facture
attend qu'on la saisisse ; seul un dossier d'avant la mise en service se saisit à la main. Un
dossier (un arrivage, une déclaration en douane) porte **une ou plusieurs factures** (décision
de Mohamed du 12/10/2026, qui amende I3) ; une facture n'est que dans un seul dossier. Les
importations dépendent des réceptions et de leur facture, jamais des commandes (sauf le cours
figé d'un bon, repris tel quel).

Modules :

- `socle` : chargement verrouillé, version, contexte de lecture, vue du moteur, marchandise
  libre, porteurs d'une facture ;
- `fiche` et `fiche_parties` : la fiche calculée (coût, TVA et droits attendus, alertes,
  échéancier, gestes permis) ; `lecture` : la liste (route 187) ; `attente` : ce qui attend son
  dossier (route 188) ;
- `ouverture` : ouvrir, rattacher le second camion (190, 192) ; `factures_dossier` : ajouter ou
  retirer une facture (253, 254) ; `marchandises` : saisie à la
  main, cours, retrait, détachement (193–198) ; `frais` (199–201) ; `etats` : en-tête, clôture,
  réouverture, annulation (191, 202–204).

Le coût de revient (routes 206–208) est dans `services/analyse_revient.py`.
"""
