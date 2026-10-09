"""Dossiers d'importation : ce que la marchandise coûte rendue à l'usine (lot D7).

**Un dossier = une facture = une livraison** (décision de Mohamed, I3) : le dossier s'ouvre
depuis la facture d'une réception validée et en prend toute la marchandise ; un second camion
de la même facture rejoint son dossier ; une réception sans facture attend qu'on la saisisse ;
seul un dossier d'avant la mise en service se saisit à la main. Les importations dépendent des
réceptions et de leur facture, jamais des commandes (sauf le cours figé d'un bon, repris tel
quel).

Modules :

- `socle` : chargement verrouillé, version, contexte de lecture, vue du moteur, marchandise
  libre, porteurs d'une facture ;
- `fiche` et `fiche_parties` : la fiche calculée (coût, TVA et droits attendus, alertes,
  échéancier, gestes permis) ; `lecture` : la liste (route 187) ; `attente` : ce qui attend son
  dossier (route 188) ;
- `ouverture` : ouvrir, rattacher le second camion (190, 192) ; `marchandises` : saisie à la
  main, cours, retrait, détachement (193–198) ; `frais` (199–201) ; `etats` : en-tête, clôture,
  réouverture, annulation (191, 202–204).

Le coût de revient (routes 206–208) est dans `services/analyse_revient.py`.
"""
