# Tournée d'écran — stress test « 10 ans » de Gestion MP PRO

Généré par `backend/essais/stress/tournee.py` (pilote `tournee_ecran.mjs`). Bureau 1 440 × 900 (direction, achats, alimentation), téléphone 375 × 812 (atelier : direction et alimentation ; bureau de l'alimentation). Tous les écrans et tous les onglets du registre, les exports Excel, les documents A4, la recherche à la frappe. Seuils : > 1 s lent, > 3 s bloquant.

## 1. Bases parcourues

| Base | Jour de l'horloge | Volume | Écrans | > 1 s | > 3 s ou bloqués | Anomalies | Médiane | Pire |
|---|---|---|---|---|---|---|---|---|
| referentiels | 2026-10-15 | 0 mvts, 0 lots, 0 bons, 0 réc., 0 OF | 307 | 0 | 0 | 69 | 375 ms | 804 ms |
| x30 | 2026-10-15 | 313 140 mvts, 50 520 lots, 9 900 bons, 9 630 réc., 9 600 OF | 368 | 71 | 121 | 447 | 1 124 ms | 20 618 ms |
| annee-1 | 2027-10-14 | 15 746 mvts, 340 lots, 80 bons, 89 réc., 986 OF | 378 | 15 | 0 | 137 | 417 ms | 1 532 ms |
| annee-2 | 2028-10-14 | 29 950 mvts, 691 lots, 270 bons, 258 réc., 1 949 OF | 378 | 36 | 0 | 181 | 424 ms | 2 153 ms |

## 2. Écran × base — temps jusqu'à l'affichage et état

Temps = navigation → roue disparue, texte présent, plus aucun appel `/api/` en vol (écran construit, Chrome sans tête, uvicorn 2 processus). État : ok ; lent (> 1 s) ; BLOQUANT (> 3 s) ; anomalie (voir § 3) ; BLOQUÉ (rien après 30 s).

| Zone | Rôle | Écran | referentiels (ms, état) | x30 (ms, état) | annee-1 (ms, état) | annee-2 (ms, état) |
|---|---|---|---|---|---|---|
| bureau | direction | `/cockpit?onglet=faire` | 516 ok | 17 035 BLOQUANT +anom. | 1 212 lent | 1 840 lent |
| bureau | direction | `/cockpit?onglet=alertes` | 392 ok | 5 350 BLOQUANT | 540 ok | 714 ok |
| bureau | direction | `/cockpit?onglet=ensemble` | 377 ok | 2 031 lent | 417 ok | 424 ok |
| bureau | direction | `/cockpit?onglet=evolution` | 376 ok | 2 082 lent | 417 ok | 418 ok |
| bureau | direction | `/cockpit?onglet=economies` | 374 ok | 2 573 lent | 417 ok | 417 ok |
| bureau | direction | `/stock?onglet=matieres` | 377 anomalie | 802 anomalie | 417 anomalie | 560 anomalie |
| bureau | direction | `/stock?onglet=lots` | 375 ok | 5 916 BLOQUANT +anom. | 578 anomalie | 678 anomalie |
| bureau | direction | `/stock?onglet=mouvements` | 374 ok | 1 274 anomalie | 532 anomalie | 523 anomalie |
| bureau | direction | `/stock?onglet=ordres` | 377 ok | 4 948 BLOQUANT +anom. | 764 ok | 1 059 anomalie |
| bureau | direction | `/stock?onglet=a-valider` | 374 ok | 796 ok | 418 ok | 376 ok |
| bureau | direction | `/stock/matieres/1` | 419 anomalie | — | — | — |
| bureau | direction | `/tracabilite?matiere=1` | 374 ok | — | — | — |
| bureau | direction | `/sorties?onglet=valide` | 375 ok | 7 389 BLOQUANT +anom. | 929 ok | 1 236 anomalie |
| bureau | direction | `/sorties?onglet=brouillon` | 375 ok | 791 ok | 458 ok | 337 ok |
| bureau | direction | `/sorties?onglet=annule` | 373 ok | 622 ok | 500 ok | 624 ok |
| bureau | direction | `/ordres/nouveau` | 415 ok | 13 441 BLOQUANT +anom. | 1 455 lent | 1 535 lent |
| bureau | direction | `/production?onglet=plan` | 373 anomalie | 596 anomalie | 377 anomalie | 376 anomalie |
| bureau | direction | `/production?onglet=glissant` | 373 anomalie | 419 anomalie | 375 anomalie | 379 anomalie |
| bureau | direction | `/production?onglet=realise` | 375 anomalie | 418 anomalie | 375 anomalie | 374 anomalie |
| bureau | direction | `/production?onglet=besoins` | 375 anomalie | 708 anomalie | 378 anomalie | 387 anomalie |
| bureau | direction | `/production/besoins/1` | 375 anomalie | — | — | — |
| bureau | direction | `/plan-achat?onglet=fournisseurs` | 373 ok | 624 ok | 374 ok | 376 ok |
| bureau | direction | `/plan-achat?onglet=references` | 374 ok | 624 ok | 376 ok | 375 ok |
| bureau | direction | `/plan-achat/preparer/1` | 374 ok | 792 ok | 417 ok | 456 ok |
| bureau | direction | `/commandes?onglet=brouillon` | 374 ok | 1 581 lent | 377 ok | 338 ok |
| bureau | direction | `/commandes?onglet=a_approuver` | 374 ok | 1 416 lent | 334 ok | 375 ok |
| bureau | direction | `/commandes?onglet=envoyee` | 373 ok | 1 412 lent | 336 ok | 335 ok |
| bureau | direction | `/commandes?onglet=confirmee` | 373 ok | 2 602 anomalie | 333 ok | 334 ok |
| bureau | direction | `/commandes?onglet=clos` | 373 ok | 3 549 BLOQUANT +anom. | 374 ok | 517 ok |
| bureau | direction | `/commandes/nouvelle` | 374 ok | 2 978 anomalie | 375 ok | 460 ok |
| bureau | direction | `/receptions?onglet=brouillon` | 374 ok | 4 546 BLOQUANT | 376 ok | 420 ok |
| bureau | direction | `/receptions?onglet=validee` | 375 ok | 4 446 BLOQUANT +anom. | 418 ok | 549 ok |
| bureau | direction | `/receptions?onglet=annulee` | 374 ok | 4 190 BLOQUANT | 416 ok | 416 ok |
| bureau | direction | `/receptions?onglet=reclamations` | 372 ok | 4 353 BLOQUANT | 375 ok | 418 ok |
| bureau | direction | `/receptions?onglet=bobines` | 376 ok | 4 610 BLOQUANT +anom. | 418 ok | 543 ok |
| bureau | direction | `/receptions?onglet=pesees` | 374 ok | 7 895 BLOQUANT +anom. | 334 ok | 567 ok |
| bureau | direction | `/receptions/nouvelle` | 372 ok | 4 910 BLOQUANT +anom. | 417 ok | 594 ok |
| bureau | direction | `/reclamations/nouvelle` | 375 ok | 4 906 BLOQUANT +anom. | 425 ok | 522 ok |
| bureau | direction | `/importations?onglet=ouverts` | 375 ok | 3 387 BLOQUANT +anom. | 417 ok | 542 anomalie |
| bureau | direction | `/importations?onglet=clos` | 333 ok | 3 912 BLOQUANT +anom. | 504 anomalie | 522 anomalie |
| bureau | direction | `/importations?onglet=rattacher` | 374 ok | 3 184 BLOQUANT | 416 ok | 456 ok |
| bureau | direction | `/dossiers/nouveau?onglet=facture` | 376 ok | 4 663 BLOQUANT +anom. | 419 ok | 545 anomalie |
| bureau | direction | `/dossiers/nouveau?onglet=main` | 341 ok | 3 801 BLOQUANT +anom. | 418 ok | 458 anomalie |
| bureau | direction | `/inventaire?onglet=cours` | 373 ok | 1 243 lent | 417 ok | 624 ok |
| bureau | direction | `/inventaire?onglet=passes` | 375 ok | 1 651 anomalie | 418 anomalie | 626 anomalie |
| bureau | direction | `/inventaires/nouveau` | 374 ok | 2 221 lent | 457 ok | 666 ok |
| bureau | direction | `/operations?onglet=transfert` | 377 ok | 872 ok | 417 ok | 335 ok |
| bureau | direction | `/operations?onglet=retour_machine` | 374 ok | 1 162 lent | 424 ok | 336 ok |
| bureau | direction | `/operations?onglet=ouverture` | 375 ok | 788 ok | 416 ok | 336 ok |
| bureau | direction | `/operations?onglet=ajustement` | 375 ok | 1 123 lent | 418 ok | 376 ok |
| bureau | direction | `/operations?onglet=retour_fournisseur` | 373 ok | 786 ok | 337 ok | 374 ok |
| bureau | direction | `/operations/nouvelle?type=transfert` | 373 ok | 1 123 lent | 424 ok | 430 ok |
| bureau | direction | `/operations/nouvelle?type=ajustement` | 374 ok | 829 ok | 421 ok | 419 ok |
| bureau | direction | `/catalogue?onglet=matieres` | 421 ok | 492 ok | 417 ok | 417 ok |
| bureau | direction | `/catalogue?onglet=classification` | 375 ok | 456 ok | 375 ok | 375 ok |
| bureau | direction | `/catalogue?onglet=fournisseurs` | 376 ok | 832 ok | 377 ok | 377 ok |
| bureau | direction | `/catalogue/tableur` | 377 ok | 476 ok | 386 ok | 418 ok |
| bureau | direction | `/matieres/nouvelle` | 386 ok | 487 ok | 460 ok | 461 ok |
| bureau | direction | `/matieres/1?onglet=classification` | 380 ok | — | — | — |
| bureau | direction | `/matieres/1?onglet=conditionnement` | 417 ok | — | — | — |
| bureau | direction | `/matieres/1?onglet=historique` | 416 ok | — | — | — |
| bureau | direction | `/matieres/1?onglet=achat` | 423 ok | — | — | — |
| bureau | direction | `/matieres/1?onglet=pieces` | 430 ok | — | — | — |
| bureau | direction | `/fournisseurs/nouveau` | 375 ok | 1 122 lent | 380 ok | 421 ok |
| bureau | direction | `/fournisseurs/1?onglet=fiche` | 374 ok | 791 ok | 418 ok | 379 ok |
| bureau | direction | `/fournisseurs/1?onglet=pieces` | 374 ok | 791 ok | 375 ok | 417 ok |
| bureau | direction | `/fournisseurs/1?onglet=historique` | 375 ok | 787 ok | 378 ok | 418 ok |
| bureau | direction | `/qualites?onglet=qualites` | 376 ok | 416 ok | 375 ok | 376 ok |
| bureau | direction | `/qualites?onglet=nomenclature` | 375 ok | 498 ok | 376 ok | 379 ok |
| bureau | direction | `/qualites/nouvelle` | 375 ok | 415 ok | 377 ok | 376 ok |
| bureau | direction | `/qualites/1?onglet=recette` | 374 ok | 458 ok | 380 ok | 427 ok |
| bureau | direction | `/qualites/1?onglet=plan` | 377 ok | 461 ok | 498 ok | 415 ok |
| bureau | direction | `/qualites/1?onglet=versions` | 373 ok | 457 ok | 375 ok | 419 ok |
| bureau | direction | `/qualites/1?onglet=historique` | 374 ok | 498 ok | 377 ok | 419 ok |
| bureau | direction | `/metiers` | 376 ok | 957 ok | 417 ok | 462 ok |
| bureau | direction | `/metiers/nouveau` | 373 ok | 627 ok | 417 ok | 458 ok |
| bureau | direction | `/metiers/2?onglet=fils` | 374 ok | — | 459 ok | 540 ok |
| bureau | direction | `/metiers/2?onglet=reglages` | 373 ok | — | 457 ok | 500 ok |
| bureau | direction | `/metiers/2?onglet=historique` | 376 ok | — | 458 ok | 557 ok |
| bureau | direction | `/analyse?onglet=valorisation` | 374 ok | 1 532 anomalie | 417 anomalie | 545 anomalie |
| bureau | direction | `/analyse?onglet=matrice` | 374 ok | 1 511 anomalie | 376 anomalie | 396 anomalie |
| bureau | direction | `/analyse?onglet=historique` | 374 ok | 6 844 BLOQUANT +anom. | 426 ok | 466 ok |
| bureau | direction | `/analyse?onglet=opportunites` | 374 anomalie | 1 412 anomalie | 375 anomalie | 378 anomalie |
| bureau | direction | `/analyse?onglet=fournisseurs` | 375 anomalie | 1 345 anomalie | 377 anomalie | 377 anomalie |
| bureau | direction | `/analyse?onglet=revient` | 376 ok | 2 266 anomalie | 376 anomalie | 419 ok |
| bureau | direction | `/analyse?onglet=echeancier` | 376 ok | 3 455 BLOQUANT +anom. | 376 ok | 429 ok |
| bureau | direction | `/analyse?onglet=controles` | 804 ok | 1 797 lent | 376 ok | 378 ok |
| bureau | direction | `/analyse?onglet=production` | 373 ok | 5 644 BLOQUANT +anom. | 642 ok | 940 anomalie |
| bureau | direction | `/reglages?onglet=parametres` | 374 ok | 583 ok | 375 ok | 376 ok |
| bureau | direction | `/reglages?onglet=devises` | 375 ok | 418 ok | 373 ok | 378 ok |
| bureau | direction | `/reglages?onglet=magasins` | 374 ok | 377 ok | 375 ok | 373 ok |
| bureau | direction | `/reglages?onglet=postes` | 376 ok | 751 ok | 335 ok | 837 ok |
| bureau | direction | `/reglages?onglet=codes` | 375 ok | 416 ok | 375 ok | 376 ok |
| bureau | direction | `/reglages?onglet=periode` | 376 ok | 375 ok | 377 ok | 376 ok |
| bureau | direction | `/administration?onglet=comptes` | 334 ok | 416 ok | 375 ok | 376 ok |
| bureau | direction | `/administration?onglet=appareils` | 374 ok | 375 ok | 376 ok | 376 ok |
| bureau | direction | `/administration?onglet=sauvegardes` | 332 ok | 375 ok | 334 ok | 381 ok |
| bureau | direction | `/administration?onglet=journal` | 377 anomalie | 505 anomalie | 392 anomalie | 458 anomalie |
| bureau | direction | `/administration?onglet=courriel` | 373 ok | 3 159 BLOQUANT | 459 ok | 501 ok |
| bureau | direction | `/administration?onglet=serveur` | 374 ok | 418 ok | 375 ok | 378 ok |
| bureau | direction | `/administration?onglet=telephone` | 373 ok | 374 ok | 375 ok | 377 ok |
| bureau | direction | `/administration?onglet=technique` | 332 ok | 375 ok | 376 ok | 380 ok |
| bureau | direction | `/administration?onglet=reprise` | 416 ok | 6 355 BLOQUANT | 707 ok | 957 ok |
| bureau | direction | `/administration?onglet=donnees` | 374 anomalie | 416 anomalie | 375 anomalie | 379 anomalie |
| bureau | direction | `/aide?onglet=regles` | 334 ok | 376 ok | 334 ok | 334 ok |
| bureau | direction | `/aide?onglet=roles` | 333 ok | 375 ok | 335 ok | 336 ok |
| bureau | direction | `/aide?onglet=pas` | 331 ok | 374 ok | 333 ok | 335 ok |
| bureau | direction | `/aide?onglet=calculs` | 334 ok | 376 ok | 334 ok | 377 ok |
| bureau | direction | `/aide?onglet=analyse` | 332 ok | 374 ok | 335 ok | 335 ok |
| bureau | direction | `/aide?onglet=ecrans` | 331 ok | 376 ok | 335 ok | 334 ok |
| bureau | direction | `/aide?onglet=telephone` | 334 ok | 375 ok | 333 ok | 334 ok |
| bureau | direction | `/compte` | 333 ok | 375 ok | 381 ok | 374 ok |
| bureau | achats | `/accueil` | 415 ok | 13 926 BLOQUANT | 1 082 lent | 1 910 lent |
| bureau | achats | `/stock?onglet=matieres` | 376 anomalie | 8 999 BLOQUANT +anom. | 420 anomalie | 435 anomalie |
| bureau | achats | `/stock?onglet=lots` | 416 ok | 6 969 BLOQUANT +anom. | 625 anomalie | 709 anomalie |
| bureau | achats | `/stock?onglet=mouvements` | 373 ok | 1 868 anomalie | 454 anomalie | 519 anomalie |
| bureau | achats | `/stock?onglet=ordres` | 374 ok | 5 087 BLOQUANT +anom. | 723 ok | 1 088 anomalie |
| bureau | achats | `/stock?onglet=a-valider` | 375 ok | 830 ok | 375 ok | 380 ok |
| bureau | achats | `/stock/matieres/1` | 377 anomalie | — | — | — |
| bureau | achats | `/tracabilite?matiere=1` | 376 ok | — | — | — |
| bureau | achats | `/sorties?onglet=valide` | 373 ok | 10 237 BLOQUANT +anom. | 693 ok | 1 383 lent |
| bureau | achats | `/sorties?onglet=brouillon` | 373 ok | 753 ok | 414 ok | 381 ok |
| bureau | achats | `/sorties?onglet=annule` | 374 ok | 625 ok | 541 ok | 675 ok |
| bureau | achats | `/production?onglet=plan` | 339 anomalie | 423 anomalie | 376 anomalie | 382 anomalie |
| bureau | achats | `/production?onglet=glissant` | 374 anomalie | 458 anomalie | 374 anomalie | 383 anomalie |
| bureau | achats | `/production?onglet=realise` | 372 anomalie | 508 anomalie | 376 anomalie | 382 anomalie |
| bureau | achats | `/production?onglet=besoins` | 375 anomalie | 653 anomalie | 377 anomalie | 420 anomalie |
| bureau | achats | `/production/besoins/1` | 375 anomalie | — | — | — |
| bureau | achats | `/plan-achat?onglet=fournisseurs` | 376 ok | 624 ok | 375 ok | 382 ok |
| bureau | achats | `/plan-achat?onglet=references` | 375 ok | 625 ok | 377 ok | 381 ok |
| bureau | achats | `/plan-achat/preparer/1` | 458 ok | 706 ok | 418 ok | 466 ok |
| bureau | achats | `/commandes?onglet=brouillon` | 373 ok | 1 203 lent | 376 ok | 338 ok |
| bureau | achats | `/commandes?onglet=a_approuver` | 373 ok | 834 ok | 374 ok | 381 ok |
| bureau | achats | `/commandes?onglet=envoyee` | 375 ok | 1 537 lent | 375 ok | 335 ok |
| bureau | achats | `/commandes?onglet=confirmee` | 374 ok | 1 833 anomalie | 377 ok | 429 ok |
| bureau | achats | `/commandes?onglet=clos` | 375 ok | 3 053 BLOQUANT +anom. | 383 ok | 549 ok |
| bureau | achats | `/commandes/nouvelle` | 373 ok | 3 201 BLOQUANT +anom. | 417 ok | 427 ok |
| bureau | achats | `/receptions?onglet=brouillon` | 374 ok | 4 286 BLOQUANT | 374 ok | 423 ok |
| bureau | achats | `/receptions?onglet=validee` | 373 ok | 5 453 BLOQUANT +anom. | 416 ok | 472 ok |
| bureau | achats | `/receptions?onglet=annulee` | 375 ok | 4 438 BLOQUANT | 336 ok | 507 ok |
| bureau | achats | `/receptions?onglet=reclamations` | 373 ok | 4 319 BLOQUANT | 375 ok | 425 ok |
| bureau | achats | `/receptions?onglet=bobines` | 375 ok | 4 627 BLOQUANT +anom. | 417 ok | 507 ok |
| bureau | achats | `/receptions?onglet=pesees` | 375 ok | 8 133 BLOQUANT +anom. | 426 ok | 515 ok |
| bureau | achats | `/receptions/nouvelle` | 375 ok | 5 670 BLOQUANT +anom. | 504 ok | 471 ok |
| bureau | achats | `/reclamations/nouvelle` | 375 ok | 5 607 BLOQUANT +anom. | 416 ok | 525 ok |
| bureau | achats | `/importations?onglet=ouverts` | 379 ok | 4 273 BLOQUANT +anom. | 375 ok | 550 anomalie |
| bureau | achats | `/importations?onglet=clos` | 375 ok | 4 007 BLOQUANT +anom. | 545 anomalie | 516 anomalie |
| bureau | achats | `/importations?onglet=rattacher` | 334 ok | 5 189 BLOQUANT | 417 ok | 464 ok |
| bureau | achats | `/dossiers/nouveau?onglet=facture` | 377 ok | 4 275 BLOQUANT +anom. | 420 ok | 465 anomalie |
| bureau | achats | `/dossiers/nouveau?onglet=main` | 373 ok | 4 193 BLOQUANT +anom. | 422 ok | 596 anomalie |
| bureau | achats | `/inventaire?onglet=cours` | 373 ok | 1 623 lent | 418 ok | 547 ok |
| bureau | achats | `/inventaire?onglet=passes` | 373 ok | 1 640 anomalie | 418 anomalie | 632 anomalie |
| bureau | achats | `/inventaires/nouveau` | 378 ok | 3 408 BLOQUANT | 625 ok | 895 ok |
| bureau | achats | `/operations?onglet=transfert` | 374 ok | 828 ok | 376 ok | 382 ok |
| bureau | achats | `/operations?onglet=retour_machine` | 373 ok | 1 175 lent | 376 ok | 341 ok |
| bureau | achats | `/operations?onglet=ouverture` | 375 ok | 790 ok | 374 ok | 337 ok |
| bureau | achats | `/operations?onglet=ajustement` | 374 ok | 791 ok | 419 ok | 382 ok |
| bureau | achats | `/operations?onglet=retour_fournisseur` | 371 ok | 1 124 lent | 498 ok | 339 ok |
| bureau | achats | `/operations/nouvelle?type=transfert` | 375 ok | 797 ok | 421 ok | 447 ok |
| bureau | achats | `/operations/nouvelle?type=ajustement` | 375 ok | 1 165 lent | 375 ok | 383 ok |
| bureau | achats | `/catalogue?onglet=matieres` | 375 ok | 475 ok | 377 ok | 390 ok |
| bureau | achats | `/catalogue?onglet=classification` | 373 ok | 456 ok | 376 ok | 383 ok |
| bureau | achats | `/catalogue?onglet=fournisseurs` | 375 ok | 1 125 lent | 377 ok | 425 ok |
| bureau | achats | `/catalogue/tableur` | 375 ok | 469 ok | 376 ok | 424 ok |
| bureau | achats | `/matieres/nouvelle` | 377 ok | 480 ok | 387 ok | 423 ok |
| bureau | achats | `/matieres/1?onglet=classification` | 415 ok | — | — | — |
| bureau | achats | `/matieres/1?onglet=conditionnement` | 416 ok | — | — | — |
| bureau | achats | `/matieres/1?onglet=historique` | 417 ok | — | — | — |
| bureau | achats | `/matieres/1?onglet=achat` | 423 ok | — | — | — |
| bureau | achats | `/matieres/1?onglet=pieces` | 416 ok | — | — | — |
| bureau | achats | `/fournisseurs/nouveau` | 376 ok | 791 ok | 375 ok | 427 ok |
| bureau | achats | `/fournisseurs/1?onglet=fiche` | 375 ok | 794 ok | 375 ok | 378 ok |
| bureau | achats | `/fournisseurs/1?onglet=pieces` | 373 ok | 1 122 lent | 375 ok | 421 ok |
| bureau | achats | `/fournisseurs/1?onglet=historique` | 375 ok | 786 ok | 377 ok | 424 ok |
| bureau | achats | `/qualites?onglet=qualites` | 375 ok | 417 ok | 376 ok | 383 ok |
| bureau | achats | `/qualites?onglet=nomenclature` | 377 ok | 478 ok | 461 ok | 590 ok |
| bureau | achats | `/qualites/1?onglet=recette` | 375 ok | 502 ok | 378 ok | 380 ok |
| bureau | achats | `/qualites/1?onglet=plan` | 374 ok | 499 ok | 376 ok | 423 ok |
| bureau | achats | `/qualites/1?onglet=versions` | 374 ok | 498 ok | 376 ok | 424 ok |
| bureau | achats | `/qualites/1?onglet=historique` | 374 ok | 459 ok | 375 ok | 424 ok |
| bureau | achats | `/metiers` | 376 ok | 1 041 lent | 419 ok | 508 ok |
| bureau | achats | `/metiers/2?onglet=fils` | 373 ok | — | 457 ok | 550 ok |
| bureau | achats | `/metiers/2?onglet=reglages` | 374 ok | — | 419 ok | 548 ok |
| bureau | achats | `/metiers/2?onglet=historique` | 374 ok | — | 462 ok | 506 ok |
| bureau | achats | `/analyse?onglet=valorisation` | 376 ok | 1 716 anomalie | 377 anomalie | 387 anomalie |
| bureau | achats | `/analyse?onglet=matrice` | 375 ok | 1 473 anomalie | 379 anomalie | 429 anomalie |
| bureau | achats | `/analyse?onglet=historique` | 376 ok | 7 158 BLOQUANT +anom. | 419 ok | 415 ok |
| bureau | achats | `/analyse?onglet=opportunites` | 378 anomalie | 1 484 anomalie | 376 anomalie | 384 anomalie |
| bureau | achats | `/analyse?onglet=fournisseurs` | 375 anomalie | 2 051 anomalie | 378 anomalie | 380 anomalie |
| bureau | achats | `/analyse?onglet=revient` | 373 ok | 3 303 BLOQUANT +anom. | 378 anomalie | 419 ok |
| bureau | achats | `/analyse?onglet=echeancier` | 376 ok | 3 010 BLOQUANT +anom. | 377 ok | 430 ok |
| bureau | achats | `/analyse?onglet=controles` | 375 ok | 2 039 lent | 378 ok | 380 ok |
| bureau | achats | `/analyse?onglet=production` | 380 ok | 6 174 BLOQUANT +anom. | 654 ok | 876 anomalie |
| bureau | achats | `/reglages?onglet=parametres` | 334 ok | 575 ok | 375 ok | 381 ok |
| bureau | achats | `/reglages?onglet=devises` | 375 ok | 375 ok | 377 ok | 380 ok |
| bureau | achats | `/reglages?onglet=magasins` | 374 ok | 413 ok | 378 ok | 380 ok |
| bureau | achats | `/reglages?onglet=postes` | 376 ok | 375 ok | 376 ok | 381 ok |
| bureau | achats | `/reglages?onglet=codes` | 378 ok | 376 ok | 377 ok | 384 ok |
| bureau | achats | `/reglages?onglet=periode` | 378 ok | 376 ok | 376 ok | 382 ok |
| bureau | achats | `/aide?onglet=regles` | 334 ok | 377 ok | 336 ok | 336 ok |
| bureau | achats | `/aide?onglet=roles` | 334 ok | 376 ok | 335 ok | 338 ok |
| bureau | achats | `/aide?onglet=pas` | 334 ok | 359 ok | 335 ok | 340 ok |
| bureau | achats | `/aide?onglet=calculs` | 336 ok | 376 ok | 335 ok | 339 ok |
| bureau | achats | `/aide?onglet=analyse` | 335 ok | 375 ok | 333 ok | 339 ok |
| bureau | achats | `/aide?onglet=ecrans` | 336 ok | 375 ok | 335 ok | 338 ok |
| bureau | achats | `/aide?onglet=telephone` | 335 ok | 417 ok | 335 ok | 339 ok |
| bureau | achats | `/compte` | 335 ok | 376 ok | 337 ok | 341 ok |
| bureau | alimentation | `/accueil` | 373 ok | 10 451 BLOQUANT | 791 ok | 1 057 lent |
| bureau | alimentation | `/stock?onglet=matieres` | 376 anomalie | 763 anomalie | 417 anomalie | 479 anomalie |
| bureau | alimentation | `/stock?onglet=lots` | 374 ok | 15 757 BLOQUANT +anom. | 559 anomalie | 727 anomalie |
| bureau | alimentation | `/stock?onglet=mouvements` | 375 ok | 695 anomalie | 433 anomalie | 421 anomalie |
| bureau | alimentation | `/stock?onglet=ordres` | 375 ok | 6 145 BLOQUANT +anom. | 751 ok | 1 203 anomalie |
| bureau | alimentation | `/stock?onglet=a-valider` | 335 ok | 625 ok | 375 ok | 340 ok |
| bureau | alimentation | `/stock/matieres/1` | 421 anomalie | — | — | — |
| bureau | alimentation | `/tracabilite?matiere=1` | 378 ok | — | — | — |
| bureau | alimentation | `/sorties?onglet=valide` | 373 ok | 8 413 BLOQUANT +anom. | 1 041 lent | 980 ok |
| bureau | alimentation | `/sorties?onglet=brouillon` | 374 ok | 926 ok | 375 ok | 380 ok |
| bureau | alimentation | `/sorties?onglet=annule` | 376 ok | 626 ok | 457 ok | 590 ok |
| bureau | alimentation | `/ordres/nouveau` | 423 ok | 12 119 BLOQUANT +anom. | 1 532 lent | 2 153 lent |
| bureau | alimentation | `/production?onglet=plan` | 375 anomalie | 468 anomalie | 377 anomalie | 381 anomalie |
| bureau | alimentation | `/production?onglet=glissant` | 375 anomalie | 419 anomalie | 375 anomalie | 378 anomalie |
| bureau | alimentation | `/production?onglet=realise` | 379 anomalie | 421 anomalie | 377 anomalie | 378 anomalie |
| bureau | alimentation | `/production?onglet=besoins` | 372 anomalie | 676 anomalie | 393 anomalie | 476 anomalie |
| bureau | alimentation | `/production/besoins/1` | 376 anomalie | — | — | — |
| bureau | alimentation | `/operations?onglet=transfert` | 376 ok | 665 ok | 420 ok | 384 ok |
| bureau | alimentation | `/operations?onglet=retour_machine` | 375 ok | 665 ok | 427 ok | 409 ok |
| bureau | alimentation | `/operations/nouvelle?type=transfert` | 374 ok | 708 ok | 417 ok | 431 ok |
| bureau | alimentation | `/catalogue?onglet=matieres` | 374 ok | 490 ok | 378 ok | 422 ok |
| bureau | alimentation | `/matieres/1?onglet=classification` | 418 ok | — | — | — |
| bureau | alimentation | `/matieres/1?onglet=conditionnement` | 421 ok | — | — | — |
| bureau | alimentation | `/matieres/1?onglet=historique` | 417 ok | — | — | — |
| bureau | alimentation | `/qualites?onglet=qualites` | 376 ok | 4 853 BLOQUANT | 378 ok | 381 ok |
| bureau | alimentation | `/qualites?onglet=nomenclature` | 375 ok | 452 ok | 379 ok | 386 ok |
| bureau | alimentation | `/qualites/1?onglet=recette` | 375 ok | 462 ok | 376 ok | 377 ok |
| bureau | alimentation | `/qualites/1?onglet=plan` | 374 ok | 458 ok | 461 ok | 508 ok |
| bureau | alimentation | `/qualites/1?onglet=versions` | 375 ok | 457 ok | 419 ok | 424 ok |
| bureau | alimentation | `/qualites/1?onglet=historique` | 375 ok | 459 ok | 378 ok | 421 ok |
| bureau | alimentation | `/metiers` | 374 ok | 669 ok | 376 ok | 419 ok |
| bureau | alimentation | `/metiers/2?onglet=fils` | 373 ok | — | 418 ok | 426 ok |
| bureau | alimentation | `/metiers/2?onglet=reglages` | 373 ok | — | 377 ok | 426 ok |
| bureau | alimentation | `/metiers/2?onglet=historique` | 376 ok | — | 418 ok | 465 ok |
| bureau | alimentation | `/aide?onglet=regles` | 334 ok | 377 ok | 335 ok | 338 ok |
| bureau | alimentation | `/aide?onglet=roles` | 333 ok | 375 ok | 333 ok | 335 ok |
| bureau | alimentation | `/aide?onglet=pas` | 333 ok | 377 ok | 336 ok | 337 ok |
| bureau | alimentation | `/aide?onglet=calculs` | 336 ok | 377 ok | 334 ok | 339 ok |
| bureau | alimentation | `/aide?onglet=analyse` | 335 ok | 376 ok | 335 ok | 340 ok |
| bureau | alimentation | `/aide?onglet=ecrans` | 334 ok | 344 ok | 336 ok | 341 ok |
| bureau | alimentation | `/aide?onglet=telephone` | 333 ok | 376 ok | 337 ok | 339 ok |
| bureau | alimentation | `/compte` | 334 ok | 337 ok | 336 ok | 338 ok |
| atelier | alimentation | `/atelier` | 373 ok | 11 063 BLOQUANT | 830 ok | 926 ok |
| atelier | alimentation | `/atelier/envoyer` | 567 ok | 6 863 BLOQUANT | 1 299 lent | 1 897 lent |
| atelier | alimentation | `/atelier/ordres` | 333 ok | 6 343 BLOQUANT | 876 ok | 1 311 lent |
| atelier | alimentation | `/atelier/retour` | 333 ok | 6 066 BLOQUANT +anom. | 751 ok | 1 273 anomalie |
| atelier | alimentation | `/atelier/chercher` | 376 ok | 3 221 BLOQUANT +anom. | 556 ok | 686 ok |
| atelier | alimentation | `/atelier/deplacer` | 380 ok | 2 624 lent | 459 ok | 635 ok |
| atelier | alimentation | `/atelier/montage` | 374 ok | 1 078 lent | 382 ok | 420 ok |
| atelier | alimentation | `/atelier/signaler` | 373 ok | 501 ok | 376 ok | 383 ok |
| atelier | direction | `/atelier` | 376 ok | 11 678 BLOQUANT | 830 ok | 1 054 lent |
| atelier | direction | `/atelier/envoyer` | 415 ok | 20 618 BLOQUANT | 1 167 lent | 1 774 lent |
| atelier | direction | `/atelier/ordres` | 374 ok | 5 413 BLOQUANT | 833 ok | 1 434 lent |
| atelier | direction | `/atelier/retour` | 333 ok | 5 025 BLOQUANT +anom. | 747 ok | 1 267 lent |
| atelier | direction | `/atelier/chercher` | 374 ok | 2 489 anomalie | 587 ok | 685 ok |
| atelier | direction | `/atelier/deplacer` | 375 ok | 2 878 lent | 543 ok | 634 ok |
| atelier | direction | `/atelier/montage` | 377 ok | 665 ok | 417 ok | 422 ok |
| atelier | direction | `/atelier/signaler` | 376 ok | 457 ok | 375 ok | 376 ok |
| bureau au téléphone | alimentation | `/accueil` | 379 ok | 10 309 BLOQUANT | 707 ok | 1 098 lent |
| bureau au téléphone | alimentation | `/stock?onglet=matieres` | 430 anomalie | 10 393 BLOQUANT +anom. | 460 anomalie | 483 anomalie |
| bureau au téléphone | alimentation | `/stock?onglet=lots` | 373 anomalie | 6 861 BLOQUANT +anom. | 606 anomalie | 707 anomalie |
| bureau au téléphone | alimentation | `/stock?onglet=mouvements` | 341 anomalie | 725 anomalie | 454 anomalie | 343 anomalie |
| bureau au téléphone | alimentation | `/stock?onglet=ordres` | 373 anomalie | 7 115 BLOQUANT +anom. | 809 anomalie | 1 081 anomalie |
| bureau au téléphone | alimentation | `/stock?onglet=a-valider` | 333 anomalie | 803 anomalie | 378 anomalie | 341 anomalie |
| bureau au téléphone | alimentation | `/stock/matieres/1` | 418 anomalie | — | — | — |
| bureau au téléphone | alimentation | `/tracabilite?matiere=1` | 374 anomalie | — | — | — |
| bureau au téléphone | alimentation | `/sorties?onglet=valide` | 338 anomalie | 20 177 BLOQUANT +anom. | 1 039 anomalie | 1 275 anomalie |
| bureau au téléphone | alimentation | `/sorties?onglet=brouillon` | 333 anomalie | 860 anomalie | 376 anomalie | 336 anomalie |
| bureau au téléphone | alimentation | `/sorties?onglet=annule` | 375 anomalie | 627 anomalie | 584 anomalie | 761 anomalie |
| bureau au téléphone | alimentation | `/ordres/nouveau` | 416 anomalie | 15 111 BLOQUANT +anom. | 1 106 anomalie | 2 140 anomalie |
| bureau au téléphone | alimentation | `/production?onglet=plan` | 377 anomalie | 682 anomalie | 375 anomalie | 382 anomalie |
| bureau au téléphone | alimentation | `/production?onglet=glissant` | 375 anomalie | 458 anomalie | 375 anomalie | 381 anomalie |
| bureau au téléphone | alimentation | `/production?onglet=realise` | 376 anomalie | 417 anomalie | 374 anomalie | 382 anomalie |
| bureau au téléphone | alimentation | `/production?onglet=besoins` | 375 anomalie | 719 anomalie | 382 anomalie | 392 anomalie |
| bureau au téléphone | alimentation | `/production/besoins/1` | 377 anomalie | — | — | — |
| bureau au téléphone | alimentation | `/operations?onglet=transfert` | 347 anomalie | 667 anomalie | 375 anomalie | 383 anomalie |
| bureau au téléphone | alimentation | `/operations?onglet=retour_machine` | 355 anomalie | 622 anomalie | 424 anomalie | 408 anomalie |
| bureau au téléphone | alimentation | `/operations/nouvelle?type=transfert` | 385 anomalie | 698 anomalie | 417 anomalie | 420 anomalie |
| bureau au téléphone | alimentation | `/catalogue?onglet=matieres` | 426 anomalie | 477 anomalie | 381 anomalie | 415 anomalie |
| bureau au téléphone | alimentation | `/matieres/1?onglet=classification` | 418 anomalie | — | — | — |
| bureau au téléphone | alimentation | `/matieres/1?onglet=conditionnement` | 400 anomalie | — | — | — |
| bureau au téléphone | alimentation | `/matieres/1?onglet=historique` | 445 anomalie | — | — | — |
| bureau au téléphone | alimentation | `/qualites?onglet=qualites` | 432 anomalie | 508 anomalie | 460 anomalie | 541 anomalie |
| bureau au téléphone | alimentation | `/qualites?onglet=nomenclature` | 447 anomalie | 4 616 BLOQUANT +anom. | 377 anomalie | 379 anomalie |
| bureau au téléphone | alimentation | `/qualites/1?onglet=recette` | 440 anomalie | 551 anomalie | 377 anomalie | 416 anomalie |
| bureau au téléphone | alimentation | `/qualites/1?onglet=plan` | 434 anomalie | 501 anomalie | 417 anomalie | 375 anomalie |
| bureau au téléphone | alimentation | `/qualites/1?onglet=versions` | 424 anomalie | 496 anomalie | 374 anomalie | 374 anomalie |
| bureau au téléphone | alimentation | `/qualites/1?onglet=historique` | 426 anomalie | 499 anomalie | 373 anomalie | 417 anomalie |
| bureau au téléphone | alimentation | `/metiers` | 387 anomalie | 668 anomalie | 375 anomalie | 375 anomalie |
| bureau au téléphone | alimentation | `/metiers/2?onglet=fils` | 388 anomalie | — | 418 anomalie | 376 anomalie |
| bureau au téléphone | alimentation | `/metiers/2?onglet=reglages` | 385 anomalie | — | 416 anomalie | 459 anomalie |
| bureau au téléphone | alimentation | `/metiers/2?onglet=historique` | 428 anomalie | — | 421 anomalie | 459 anomalie |
| bureau au téléphone | alimentation | `/aide?onglet=regles` | 347 ok | 334 ok | 333 ok | 334 ok |
| bureau au téléphone | alimentation | `/aide?onglet=roles` | 348 ok | 376 ok | 334 ok | 334 ok |
| bureau au téléphone | alimentation | `/aide?onglet=pas` | 356 ok | 375 ok | 333 ok | 334 ok |
| bureau au téléphone | alimentation | `/aide?onglet=calculs` | 353 anomalie | 376 anomalie | 334 anomalie | 335 anomalie |
| bureau au téléphone | alimentation | `/aide?onglet=analyse` | 348 anomalie | 375 anomalie | 336 anomalie | 333 anomalie |
| bureau au téléphone | alimentation | `/aide?onglet=ecrans` | 347 anomalie | 375 anomalie | 335 anomalie | 333 anomalie |
| bureau au téléphone | alimentation | `/aide?onglet=telephone` | 348 ok | 334 ok | 336 ok | 332 ok |
| bureau au téléphone | alimentation | `/compte` | 356 ok | 376 ok | 336 ok | 336 ok |
| bureau | direction | `/stock/matieres/111` | — | 1 084 anomalie | — | — |
| bureau | direction | `/lots/291565` | — | 6 315 BLOQUANT +anom. | — | — |
| bureau | direction | `/tracabilite?lot=291565` | — | 5 831 BLOQUANT +anom. | — | — |
| bureau | direction | `/tracabilite?matiere=111` | — | 6 805 BLOQUANT +anom. | — | — |
| bureau | direction | `/ordres/29319` | — | 8 578 BLOQUANT +anom. | — | — |
| bureau | direction | `/ordres/29319/retour` | — | 7 720 BLOQUANT +anom. | — | — |
| bureau | direction | `/production/besoins/111` | — | 691 anomalie | — | — |
| bureau | direction | `/commandes/29330?onglet=lignes` | — | 2 518 anomalie | — | — |
| bureau | direction | `/commandes/29330?onglet=prix` | — | 3 093 BLOQUANT +anom. | — | — |
| bureau | direction | `/commandes/29330?onglet=expedition` | — | 3 011 BLOQUANT +anom. | — | — |
| bureau | direction | `/commandes/29330?onglet=receptions` | — | 2 821 anomalie | — | — |
| bureau | direction | `/commandes/29330?onglet=approbation` | — | 3 078 BLOQUANT +anom. | — | — |
| bureau | direction | `/commandes/29330?onglet=pieces` | — | 2 641 anomalie | — | — |
| bureau | direction | `/commandes/29330?onglet=historique` | — | 2 830 anomalie | — | — |
| bureau | direction | `/receptions/29321?onglet=lignes` | — | 4 950 BLOQUANT +anom. | — | — |
| bureau | direction | `/receptions/29321?onglet=reclamations` | — | 4 858 BLOQUANT +anom. | — | — |
| bureau | direction | `/receptions/29321?onglet=pieces` | — | 4 324 BLOQUANT +anom. | — | — |
| bureau | direction | `/receptions/29321?onglet=historique` | — | 4 820 BLOQUANT +anom. | — | — |
| bureau | direction | `/dossiers/2990?onglet=familles` | — | 3 271 BLOQUANT +anom. | — | — |
| bureau | direction | `/dossiers/2990?onglet=marchandises` | — | 4 185 BLOQUANT +anom. | — | — |
| bureau | direction | `/dossiers/2990?onglet=frais` | — | 3 290 BLOQUANT +anom. | — | — |
| bureau | direction | `/dossiers/2990?onglet=echeancier` | — | 4 077 BLOQUANT +anom. | — | — |
| bureau | direction | `/dossiers/2990?onglet=pieces` | — | 4 093 BLOQUANT +anom. | — | — |
| bureau | direction | `/dossiers/2990?onglet=facture` | — | 3 497 BLOQUANT +anom. | — | — |
| bureau | direction | `/dossiers/2990?onglet=historique` | — | 3 832 BLOQUANT +anom. | — | — |
| bureau | direction | `/inventaires/2912?onglet=lots` | — | 1 578 anomalie | — | — |
| bureau | direction | `/inventaires/2912?onglet=pieces` | — | 2 482 anomalie | — | — |
| bureau | direction | `/inventaires/2912?onglet=historique` | — | 2 132 anomalie | — | — |
| bureau | direction | `/matieres/111?onglet=classification` | — | 512 ok | — | — |
| bureau | direction | `/matieres/111?onglet=conditionnement` | — | 478 ok | — | — |
| bureau | direction | `/matieres/111?onglet=historique` | — | 518 ok | — | — |
| bureau | direction | `/matieres/111?onglet=achat` | — | 479 ok | — | — |
| bureau | direction | `/matieres/111?onglet=pieces` | — | 522 ok | — | — |
| bureau | direction | `/metiers/1?onglet=fils` | — | 1 206 lent | — | — |
| bureau | direction | `/metiers/1?onglet=reglages` | — | 914 ok | — | — |
| bureau | direction | `/metiers/1?onglet=historique` | — | 1 285 lent | — | — |
| bureau | achats | `/stock/matieres/111` | — | 1 494 anomalie | — | — |
| bureau | achats | `/lots/291565` | — | 5 541 BLOQUANT +anom. | — | — |
| bureau | achats | `/tracabilite?lot=291565` | — | 5 958 BLOQUANT +anom. | — | — |
| bureau | achats | `/tracabilite?matiere=111` | — | 5 721 BLOQUANT +anom. | — | — |
| bureau | achats | `/ordres/29319` | — | 8 762 BLOQUANT +anom. | — | — |
| bureau | achats | `/production/besoins/111` | — | 657 anomalie | — | — |
| bureau | achats | `/commandes/29330?onglet=lignes` | — | 2 463 anomalie | — | — |
| bureau | achats | `/commandes/29330?onglet=prix` | — | 3 060 BLOQUANT +anom. | — | — |
| bureau | achats | `/commandes/29330?onglet=expedition` | — | 3 053 BLOQUANT +anom. | — | — |
| bureau | achats | `/commandes/29330?onglet=receptions` | — | 3 074 BLOQUANT +anom. | — | — |
| bureau | achats | `/commandes/29330?onglet=approbation` | — | 3 058 BLOQUANT +anom. | — | — |
| bureau | achats | `/commandes/29330?onglet=pieces` | — | 2 888 anomalie | — | — |
| bureau | achats | `/commandes/29330?onglet=historique` | — | 2 951 anomalie | — | — |
| bureau | achats | `/receptions/29321?onglet=lignes` | — | 4 910 BLOQUANT +anom. | — | — |
| bureau | achats | `/receptions/29321?onglet=reclamations` | — | 5 732 BLOQUANT +anom. | — | — |
| bureau | achats | `/receptions/29321?onglet=pieces` | — | 5 853 BLOQUANT +anom. | — | — |
| bureau | achats | `/receptions/29321?onglet=historique` | — | 5 597 BLOQUANT +anom. | — | — |
| bureau | achats | `/dossiers/2990?onglet=familles` | — | 3 965 BLOQUANT +anom. | — | — |
| bureau | achats | `/dossiers/2990?onglet=marchandises` | — | 3 515 BLOQUANT +anom. | — | — |
| bureau | achats | `/dossiers/2990?onglet=frais` | — | 4 203 BLOQUANT +anom. | — | — |
| bureau | achats | `/dossiers/2990?onglet=echeancier` | — | 3 463 BLOQUANT +anom. | — | — |
| bureau | achats | `/dossiers/2990?onglet=pieces` | — | 3 942 BLOQUANT +anom. | — | — |
| bureau | achats | `/dossiers/2990?onglet=facture` | — | 3 307 BLOQUANT +anom. | — | — |
| bureau | achats | `/dossiers/2990?onglet=historique` | — | 3 567 BLOQUANT +anom. | — | — |
| bureau | achats | `/inventaires/2912?onglet=lots` | — | 2 183 anomalie | — | — |
| bureau | achats | `/inventaires/2912?onglet=pieces` | — | 2 170 anomalie | — | — |
| bureau | achats | `/inventaires/2912?onglet=historique` | — | 2 502 anomalie | — | — |
| bureau | achats | `/matieres/111?onglet=classification` | — | 470 ok | — | — |
| bureau | achats | `/matieres/111?onglet=conditionnement` | — | 491 ok | — | — |
| bureau | achats | `/matieres/111?onglet=historique` | — | 523 ok | — | — |
| bureau | achats | `/matieres/111?onglet=achat` | — | 482 ok | — | — |
| bureau | achats | `/matieres/111?onglet=pieces` | — | 529 ok | — | — |
| bureau | achats | `/metiers/1?onglet=fils` | — | 1 451 lent | — | — |
| bureau | achats | `/metiers/1?onglet=reglages` | — | 998 ok | — | — |
| bureau | achats | `/metiers/1?onglet=historique` | — | 1 413 lent | — | — |
| bureau | alimentation | `/stock/matieres/111` | — | 1 041 anomalie | — | — |
| bureau | alimentation | `/lots/291565` | — | 6 447 BLOQUANT +anom. | — | — |
| bureau | alimentation | `/tracabilite?lot=291565` | — | 6 252 BLOQUANT +anom. | — | — |
| bureau | alimentation | `/tracabilite?matiere=111` | — | 7 083 BLOQUANT +anom. | — | — |
| bureau | alimentation | `/ordres/29319` | — | 9 162 BLOQUANT +anom. | — | — |
| bureau | alimentation | `/ordres/29319/retour` | — | 8 745 BLOQUANT +anom. | — | — |
| bureau | alimentation | `/production/besoins/111` | — | 692 anomalie | — | — |
| bureau | alimentation | `/matieres/111?onglet=classification` | — | 472 ok | — | — |
| bureau | alimentation | `/matieres/111?onglet=conditionnement` | — | 476 ok | — | — |
| bureau | alimentation | `/matieres/111?onglet=historique` | — | 526 ok | — | — |
| bureau | alimentation | `/metiers/1?onglet=fils` | — | 1 452 lent | — | — |
| bureau | alimentation | `/metiers/1?onglet=reglages` | — | 954 ok | — | — |
| bureau | alimentation | `/metiers/1?onglet=historique` | — | 1 333 lent | — | — |
| atelier | alimentation | `/atelier/ordres/29319` | — | 1 537 lent | — | — |
| atelier | alimentation | `/atelier/lots/291565` | — | 10 654 BLOQUANT | — | — |
| atelier | direction | `/atelier/ordres/29319` | — | 1 411 lent | — | — |
| atelier | direction | `/atelier/lots/291565` | — | 376 ok | — | — |
| bureau au téléphone | alimentation | `/stock/matieres/111` | — | 1 338 anomalie | — | — |
| bureau au téléphone | alimentation | `/lots/291565` | — | 7 984 BLOQUANT +anom. | — | — |
| bureau au téléphone | alimentation | `/tracabilite?lot=291565` | — | 8 263 BLOQUANT +anom. | — | — |
| bureau au téléphone | alimentation | `/tracabilite?matiere=111` | — | 14 159 BLOQUANT +anom. | — | — |
| bureau au téléphone | alimentation | `/ordres/29319` | — | 9 217 BLOQUANT +anom. | — | — |
| bureau au téléphone | alimentation | `/ordres/29319/retour` | — | 9 390 BLOQUANT +anom. | — | — |
| bureau au téléphone | alimentation | `/production/besoins/111` | — | 707 anomalie | — | — |
| bureau au téléphone | alimentation | `/matieres/111?onglet=classification` | — | 470 anomalie | — | — |
| bureau au téléphone | alimentation | `/matieres/111?onglet=conditionnement` | — | 486 anomalie | — | — |
| bureau au téléphone | alimentation | `/matieres/111?onglet=historique` | — | 516 anomalie | — | — |
| bureau au téléphone | alimentation | `/metiers/1?onglet=fils` | — | 1 453 anomalie | — | — |
| bureau au téléphone | alimentation | `/metiers/1?onglet=reglages` | — | 1 371 anomalie | — | — |
| bureau au téléphone | alimentation | `/metiers/1?onglet=historique` | — | 1 333 anomalie | — | — |
| bureau | direction | `/stock/matieres/124` | — | — | 469 anomalie | 545 anomalie |
| bureau | direction | `/lots/353` | — | — | 492 anomalie | — |
| bureau | direction | `/tracabilite?lot=353` | — | — | 832 ok | — |
| bureau | direction | `/tracabilite?matiere=124` | — | — | 781 ok | 1 125 anomalie |
| bureau | direction | `/ordres/1087` | — | — | 1 079 lent | — |
| bureau | direction | `/ordres/1087/retour` | — | — | 1 042 lent | — |
| bureau | direction | `/production/besoins/124` | — | — | 387 anomalie | 415 anomalie |
| bureau | direction | `/commandes/85?onglet=lignes` | — | — | 420 ok | — |
| bureau | direction | `/commandes/85?onglet=prix` | — | — | 415 ok | — |
| bureau | direction | `/commandes/85?onglet=expedition` | — | — | 417 ok | — |
| bureau | direction | `/commandes/85?onglet=receptions` | — | — | 421 ok | — |
| bureau | direction | `/commandes/85?onglet=approbation` | — | — | 418 ok | — |
| bureau | direction | `/commandes/85?onglet=pieces` | — | — | 417 ok | — |
| bureau | direction | `/commandes/85?onglet=historique` | — | — | 416 ok | — |
| bureau | direction | `/receptions/95?onglet=lignes` | — | — | 419 ok | — |
| bureau | direction | `/receptions/95?onglet=reclamations` | — | — | 415 ok | — |
| bureau | direction | `/receptions/95?onglet=pieces` | — | — | 417 ok | — |
| bureau | direction | `/receptions/95?onglet=historique` | — | — | 418 ok | — |
| bureau | direction | `/reclamations/10?onglet=reponse` | — | — | 416 ok | — |
| bureau | direction | `/reclamations/10?onglet=pieces` | — | — | 375 ok | — |
| bureau | direction | `/reclamations/10?onglet=historique` | — | — | 499 ok | — |
| bureau | direction | `/dossiers/58?onglet=familles` | — | — | 462 anomalie | — |
| bureau | direction | `/dossiers/58?onglet=marchandises` | — | — | 419 anomalie | — |
| bureau | direction | `/dossiers/58?onglet=frais` | — | — | 420 anomalie | — |
| bureau | direction | `/dossiers/58?onglet=echeancier` | — | — | 421 anomalie | — |
| bureau | direction | `/dossiers/58?onglet=pieces` | — | — | 508 anomalie | — |
| bureau | direction | `/dossiers/58?onglet=facture` | — | — | 466 anomalie | — |
| bureau | direction | `/dossiers/58?onglet=historique` | — | — | 423 anomalie | — |
| bureau | direction | `/inventaires/26?onglet=lots` | — | — | 541 anomalie | — |
| bureau | direction | `/inventaires/26?onglet=pieces` | — | — | 456 anomalie | — |
| bureau | direction | `/inventaires/26?onglet=historique` | — | — | 458 anomalie | — |
| bureau | direction | `/operations/337` | — | — | 425 ok | — |
| bureau | direction | `/matieres/124?onglet=classification` | — | — | 418 ok | 396 ok |
| bureau | direction | `/matieres/124?onglet=conditionnement` | — | — | 384 ok | 418 ok |
| bureau | direction | `/matieres/124?onglet=historique` | — | — | 429 ok | 426 ok |
| bureau | direction | `/matieres/124?onglet=achat` | — | — | 421 ok | 388 ok |
| bureau | direction | `/matieres/124?onglet=pieces` | — | — | 421 ok | 436 ok |
| bureau | achats | `/stock/matieres/124` | — | — | 501 anomalie | 489 anomalie |
| bureau | achats | `/lots/353` | — | — | 519 anomalie | — |
| bureau | achats | `/tracabilite?lot=353` | — | — | 699 ok | — |
| bureau | achats | `/tracabilite?matiere=124` | — | — | 737 ok | 1 075 anomalie |
| bureau | achats | `/ordres/1087` | — | — | 1 045 lent | — |
| bureau | achats | `/production/besoins/124` | — | — | 383 anomalie | 419 anomalie |
| bureau | achats | `/commandes/85?onglet=lignes` | — | — | 419 ok | — |
| bureau | achats | `/commandes/85?onglet=prix` | — | — | 386 ok | — |
| bureau | achats | `/commandes/85?onglet=expedition` | — | — | 415 ok | — |
| bureau | achats | `/commandes/85?onglet=receptions` | — | — | 416 ok | — |
| bureau | achats | `/commandes/85?onglet=approbation` | — | — | 376 ok | — |
| bureau | achats | `/commandes/85?onglet=pieces` | — | — | 417 ok | — |
| bureau | achats | `/commandes/85?onglet=historique` | — | — | 419 ok | — |
| bureau | achats | `/receptions/95?onglet=lignes` | — | — | 419 ok | — |
| bureau | achats | `/receptions/95?onglet=reclamations` | — | — | 379 ok | — |
| bureau | achats | `/receptions/95?onglet=pieces` | — | — | 425 ok | — |
| bureau | achats | `/receptions/95?onglet=historique` | — | — | 422 ok | — |
| bureau | achats | `/reclamations/10?onglet=reponse` | — | — | 417 ok | — |
| bureau | achats | `/reclamations/10?onglet=pieces` | — | — | 416 ok | — |
| bureau | achats | `/reclamations/10?onglet=historique` | — | — | 417 ok | — |
| bureau | achats | `/dossiers/58?onglet=familles` | — | — | 419 anomalie | — |
| bureau | achats | `/dossiers/58?onglet=marchandises` | — | — | 422 anomalie | — |
| bureau | achats | `/dossiers/58?onglet=frais` | — | — | 543 anomalie | — |
| bureau | achats | `/dossiers/58?onglet=echeancier` | — | — | 459 anomalie | — |
| bureau | achats | `/dossiers/58?onglet=pieces` | — | — | 418 anomalie | — |
| bureau | achats | `/dossiers/58?onglet=facture` | — | — | 460 anomalie | — |
| bureau | achats | `/dossiers/58?onglet=historique` | — | — | 504 anomalie | — |
| bureau | achats | `/inventaires/26?onglet=lots` | — | — | 460 anomalie | — |
| bureau | achats | `/inventaires/26?onglet=pieces` | — | — | 458 anomalie | — |
| bureau | achats | `/inventaires/26?onglet=historique` | — | — | 540 anomalie | — |
| bureau | achats | `/operations/337` | — | — | 421 ok | — |
| bureau | achats | `/matieres/124?onglet=classification` | — | — | 392 ok | 398 ok |
| bureau | achats | `/matieres/124?onglet=conditionnement` | — | — | 419 ok | 421 ok |
| bureau | achats | `/matieres/124?onglet=historique` | — | — | 427 ok | 422 ok |
| bureau | achats | `/matieres/124?onglet=achat` | — | — | 392 ok | 391 ok |
| bureau | achats | `/matieres/124?onglet=pieces` | — | — | 427 ok | 425 ok |
| bureau | alimentation | `/stock/matieres/124` | — | — | 798 anomalie | 1 024 anomalie |
| bureau | alimentation | `/lots/353` | — | — | 530 anomalie | — |
| bureau | alimentation | `/tracabilite?lot=353` | — | — | 828 ok | — |
| bureau | alimentation | `/tracabilite?matiere=124` | — | — | 874 ok | 1 221 anomalie |
| bureau | alimentation | `/ordres/1087` | — | — | 1 121 lent | — |
| bureau | alimentation | `/ordres/1087/retour` | — | — | 1 061 lent | — |
| bureau | alimentation | `/production/besoins/124` | — | — | 385 anomalie | 393 anomalie |
| bureau | alimentation | `/operations/337` | — | — | 416 ok | — |
| bureau | alimentation | `/matieres/124?onglet=classification` | — | — | 377 ok | 394 ok |
| bureau | alimentation | `/matieres/124?onglet=conditionnement` | — | — | 389 ok | 424 ok |
| bureau | alimentation | `/matieres/124?onglet=historique` | — | — | 434 ok | 431 ok |
| atelier | alimentation | `/atelier/ordres/1087` | — | — | 500 ok | — |
| atelier | alimentation | `/atelier/lots/353` | — | — | 385 ok | — |
| atelier | direction | `/atelier/ordres/1087` | — | — | 502 ok | — |
| atelier | direction | `/atelier/lots/353` | — | — | 376 ok | — |
| bureau au téléphone | alimentation | `/stock/matieres/124` | — | — | 764 anomalie | 994 anomalie |
| bureau au téléphone | alimentation | `/lots/353` | — | — | 526 anomalie | — |
| bureau au téléphone | alimentation | `/tracabilite?lot=353` | — | — | 833 anomalie | — |
| bureau au téléphone | alimentation | `/tracabilite?matiere=124` | — | — | 799 anomalie | 1 304 anomalie |
| bureau au téléphone | alimentation | `/ordres/1087` | — | — | 828 anomalie | — |
| bureau au téléphone | alimentation | `/ordres/1087/retour` | — | — | 1 028 anomalie | — |
| bureau au téléphone | alimentation | `/production/besoins/124` | — | — | 391 anomalie | 392 anomalie |
| bureau au téléphone | alimentation | `/operations/337` | — | — | 420 anomalie | — |
| bureau au téléphone | alimentation | `/matieres/124?onglet=classification` | — | — | 387 anomalie | 387 anomalie |
| bureau au téléphone | alimentation | `/matieres/124?onglet=conditionnement` | — | — | 383 anomalie | 378 anomalie |
| bureau au téléphone | alimentation | `/matieres/124?onglet=historique` | — | — | 420 anomalie | 416 anomalie |
| bureau | direction | `/lots/704` | — | — | — | 693 anomalie |
| bureau | direction | `/tracabilite?lot=704` | — | — | — | 1 060 anomalie |
| bureau | direction | `/ordres/2181` | — | — | — | 1 127 lent |
| bureau | direction | `/ordres/2181/retour` | — | — | — | 1 311 lent |
| bureau | direction | `/commandes/275?onglet=lignes` | — | — | — | 417 ok |
| bureau | direction | `/commandes/275?onglet=prix` | — | — | — | 418 ok |
| bureau | direction | `/commandes/275?onglet=expedition` | — | — | — | 418 ok |
| bureau | direction | `/commandes/275?onglet=receptions` | — | — | — | 417 ok |
| bureau | direction | `/commandes/275?onglet=approbation` | — | — | — | 419 ok |
| bureau | direction | `/commandes/275?onglet=pieces` | — | — | — | 416 ok |
| bureau | direction | `/commandes/275?onglet=historique` | — | — | — | 416 ok |
| bureau | direction | `/receptions/274?onglet=lignes` | — | — | — | 474 ok |
| bureau | direction | `/receptions/274?onglet=reclamations` | — | — | — | 467 ok |
| bureau | direction | `/receptions/274?onglet=pieces` | — | — | — | 460 ok |
| bureau | direction | `/receptions/274?onglet=historique` | — | — | — | 469 ok |
| bureau | direction | `/reclamations/22?onglet=reponse` | — | — | — | 544 ok |
| bureau | direction | `/reclamations/22?onglet=pieces` | — | — | — | 476 ok |
| bureau | direction | `/reclamations/22?onglet=historique` | — | — | — | 464 ok |
| bureau | direction | `/dossiers/160?onglet=familles` | — | — | — | 548 anomalie |
| bureau | direction | `/dossiers/160?onglet=marchandises` | — | — | — | 630 anomalie |
| bureau | direction | `/dossiers/160?onglet=frais` | — | — | — | 629 anomalie |
| bureau | direction | `/dossiers/160?onglet=echeancier` | — | — | — | 550 anomalie |
| bureau | direction | `/dossiers/160?onglet=pieces` | — | — | — | 633 anomalie |
| bureau | direction | `/dossiers/160?onglet=facture` | — | — | — | 626 anomalie |
| bureau | direction | `/dossiers/160?onglet=historique` | — | — | — | 564 anomalie |
| bureau | direction | `/inventaires/57?onglet=lots` | — | — | — | 628 anomalie |
| bureau | direction | `/inventaires/57?onglet=pieces` | — | — | — | 625 anomalie |
| bureau | direction | `/inventaires/57?onglet=historique` | — | — | — | 627 anomalie |
| bureau | direction | `/operations/641` | — | — | — | 434 ok |
| bureau | achats | `/lots/704` | — | — | — | 714 anomalie |
| bureau | achats | `/tracabilite?lot=704` | — | — | — | 1 112 anomalie |
| bureau | achats | `/ordres/2181` | — | — | — | 1 616 lent |
| bureau | achats | `/commandes/275?onglet=lignes` | — | — | — | 420 ok |
| bureau | achats | `/commandes/275?onglet=prix` | — | — | — | 420 ok |
| bureau | achats | `/commandes/275?onglet=expedition` | — | — | — | 423 ok |
| bureau | achats | `/commandes/275?onglet=receptions` | — | — | — | 423 ok |
| bureau | achats | `/commandes/275?onglet=approbation` | — | — | — | 424 ok |
| bureau | achats | `/commandes/275?onglet=pieces` | — | — | — | 421 ok |
| bureau | achats | `/commandes/275?onglet=historique` | — | — | — | 424 ok |
| bureau | achats | `/receptions/274?onglet=lignes` | — | — | — | 470 ok |
| bureau | achats | `/receptions/274?onglet=reclamations` | — | — | — | 552 ok |
| bureau | achats | `/receptions/274?onglet=pieces` | — | — | — | 478 ok |
| bureau | achats | `/receptions/274?onglet=historique` | — | — | — | 463 ok |
| bureau | achats | `/reclamations/22?onglet=reponse` | — | — | — | 470 ok |
| bureau | achats | `/reclamations/22?onglet=pieces` | — | — | — | 465 ok |
| bureau | achats | `/reclamations/22?onglet=historique` | — | — | — | 482 ok |
| bureau | achats | `/dossiers/160?onglet=familles` | — | — | — | 507 anomalie |
| bureau | achats | `/dossiers/160?onglet=marchandises` | — | — | — | 604 anomalie |
| bureau | achats | `/dossiers/160?onglet=frais` | — | — | — | 508 anomalie |
| bureau | achats | `/dossiers/160?onglet=echeancier` | — | — | — | 605 anomalie |
| bureau | achats | `/dossiers/160?onglet=pieces` | — | — | — | 596 anomalie |
| bureau | achats | `/dossiers/160?onglet=facture` | — | — | — | 511 anomalie |
| bureau | achats | `/dossiers/160?onglet=historique` | — | — | — | 597 anomalie |
| bureau | achats | `/inventaires/57?onglet=lots` | — | — | — | 683 anomalie |
| bureau | achats | `/inventaires/57?onglet=pieces` | — | — | — | 674 anomalie |
| bureau | achats | `/inventaires/57?onglet=historique` | — | — | — | 692 anomalie |
| bureau | achats | `/operations/641` | — | — | — | 477 ok |
| bureau | alimentation | `/lots/704` | — | — | — | 727 anomalie |
| bureau | alimentation | `/tracabilite?lot=704` | — | — | — | 1 202 anomalie |
| bureau | alimentation | `/ordres/2181` | — | — | — | 1 445 lent |
| bureau | alimentation | `/ordres/2181/retour` | — | — | — | 995 ok |
| bureau | alimentation | `/operations/641` | — | — | — | 480 ok |
| atelier | alimentation | `/atelier/ordres/2181` | — | — | — | 550 ok |
| atelier | alimentation | `/atelier/lots/704` | — | — | — | 380 ok |
| atelier | direction | `/atelier/ordres/2181` | — | — | — | 461 ok |
| atelier | direction | `/atelier/lots/704` | — | — | — | 381 ok |
| bureau au téléphone | alimentation | `/lots/704` | — | — | — | 741 anomalie |
| bureau au téléphone | alimentation | `/tracabilite?lot=704` | — | — | — | 1 185 anomalie |
| bureau au téléphone | alimentation | `/ordres/2181` | — | — | — | 1 506 anomalie |
| bureau au téléphone | alimentation | `/ordres/2181/retour` | — | — | — | 1 148 anomalie |
| bureau au téléphone | alimentation | `/operations/641` | — | — | — | 462 anomalie |

## 3. Anomalies relevées, par base

### referentiels

- [bureau, direction, 1440×900] `/stock?onglet=matieres` : tableau plus large que son cadre 2017>1142 (Stock par matière)
- [bureau, direction, 1440×900] `/stock/matieres/1` : tableau plus large que son cadre 2017>1142 (Stock par matière)
- [bureau, direction, 1440×900] `/production?onglet=plan` : tableau plus large que son cadre 1552>1142 (Plan de production)
- [bureau, direction, 1440×900] `/production?onglet=glissant` : tableau plus large que son cadre 1437>1142 (Plan glissant)
- [bureau, direction, 1440×900] `/production?onglet=realise` : tableau plus large que son cadre 1380>1142 (Plan et réalisé)
- [bureau, direction, 1440×900] `/production?onglet=besoins` : tableau plus large que son cadre 2269>1142 (Besoins matière)
- [bureau, direction, 1440×900] `/production/besoins/1` : tableau plus large que son cadre 2269>1142 (Besoins matière)
- [bureau, direction, 1440×900] `/analyse?onglet=opportunites` : tableau plus large que son cadre 1170>1142 (Opportunités d’économies)
- [bureau, direction, 1440×900] `/analyse?onglet=fournisseurs` : tableau plus large que son cadre 1228>1142 (Classement des fournisseurs)
- [bureau, direction, 1440×900] `/administration?onglet=journal` : tableau plus large que son cadre 2161>1142 (Journal des actions)
- [bureau, direction, 1440×900] `/administration?onglet=donnees` : tableau plus large que son cadre 3049>1142 (Table matiere)
- [bureau, achats, 1440×900] `/stock?onglet=matieres` : tableau plus large que son cadre 2017>1142 (Stock par matière)
- [bureau, achats, 1440×900] `/stock/matieres/1` : tableau plus large que son cadre 2017>1142 (Stock par matière)
- [bureau, achats, 1440×900] `/production?onglet=plan` : tableau plus large que son cadre 1300>1142 (Plan de production)
- [bureau, achats, 1440×900] `/production?onglet=glissant` : tableau plus large que son cadre 1437>1142 (Plan glissant)
- [bureau, achats, 1440×900] `/production?onglet=realise` : tableau plus large que son cadre 1380>1142 (Plan et réalisé)
- [bureau, achats, 1440×900] `/production?onglet=besoins` : tableau plus large que son cadre 2269>1142 (Besoins matière)
- [bureau, achats, 1440×900] `/production/besoins/1` : tableau plus large que son cadre 2269>1142 (Besoins matière)
- [bureau, achats, 1440×900] `/analyse?onglet=opportunites` : tableau plus large que son cadre 1170>1142 (Opportunités d’économies)
- [bureau, achats, 1440×900] `/analyse?onglet=fournisseurs` : tableau plus large que son cadre 1228>1142 (Classement des fournisseurs)
- [bureau, alimentation, 1440×900] `/stock?onglet=matieres` : tableau plus large que son cadre 1685>1142 (Stock par matière)
- [bureau, alimentation, 1440×900] `/stock/matieres/1` : tableau plus large que son cadre 1685>1142 (Stock par matière)
- [bureau, alimentation, 1440×900] `/production?onglet=plan` : tableau plus large que son cadre 1300>1142 (Plan de production)
- [bureau, alimentation, 1440×900] `/production?onglet=glissant` : tableau plus large que son cadre 1437>1142 (Plan glissant)
- [bureau, alimentation, 1440×900] `/production?onglet=realise` : tableau plus large que son cadre 1380>1142 (Plan et réalisé)
- [bureau, alimentation, 1440×900] `/production?onglet=besoins` : tableau plus large que son cadre 2123>1142 (Besoins matière)
- [bureau, alimentation, 1440×900] `/production/besoins/1` : tableau plus large que son cadre 2123>1142 (Besoins matière)
- [bureau au téléphone, alimentation, 375×812] `/stock?onglet=matieres` : tableau plus large que son cadre 1589>349 (Stock par matière)
- [bureau au téléphone, alimentation, 375×812] `/stock?onglet=lots` : tableau plus large que son cadre 830>349 (Lots)
- [bureau au téléphone, alimentation, 375×812] `/stock?onglet=mouvements` : tableau plus large que son cadre 578>349 (Mouvements de stock)
- [bureau au téléphone, alimentation, 375×812] `/stock?onglet=ordres` : tableau plus large que son cadre 701>349 (Ordres de fabrication)
- [bureau au téléphone, alimentation, 375×812] `/stock?onglet=a-valider` : tableau plus large que son cadre 490>349 (Brouillons à valider)
- [bureau au téléphone, alimentation, 375×812] `/stock/matieres/1` : tableau plus large que son cadre 1589>349 (Stock par matière)
- [bureau au téléphone, alimentation, 375×812] `/stock/matieres/1` : tableau plus large que son cadre 1043>341 (Besoins du plan, mois par mois (kg))
- [bureau au téléphone, alimentation, 375×812] `/tracabilite?matiere=1` : tableau plus large que son cadre 701>349 (Ordres de fabrication)
- [bureau au téléphone, alimentation, 375×812] `/sorties?onglet=valide` : tableau plus large que son cadre 737>349 (Ordres de fabrication)
- [bureau au téléphone, alimentation, 375×812] `/sorties?onglet=brouillon` : tableau plus large que son cadre 730>349 (Ordres de fabrication)
- [bureau au téléphone, alimentation, 375×812] `/sorties?onglet=annule` : tableau plus large que son cadre 737>349 (Ordres de fabrication)
- [bureau au téléphone, alimentation, 375×812] `/ordres/nouveau` : tableau plus large que son cadre 737>349 (Ordres de fabrication)
- [bureau au téléphone, alimentation, 375×812] `/ordres/nouveau` : tableau plus large que son cadre 483>341 (Les matières qui sortent)
- [bureau au téléphone, alimentation, 375×812] `/production?onglet=plan` : tableau plus large que son cadre 1172>349 (Plan de production)
- [bureau au téléphone, alimentation, 375×812] `/production?onglet=glissant` : tableau plus large que son cadre 1317>349 (Plan glissant)
- [bureau au téléphone, alimentation, 375×812] `/production?onglet=realise` : tableau plus large que son cadre 1260>349 (Plan et réalisé)
- [bureau au téléphone, alimentation, 375×812] `/production?onglet=besoins` : tableau plus large que son cadre 1979>349 (Besoins matière)
- [bureau au téléphone, alimentation, 375×812] `/production/besoins/1` : tableau plus large que son cadre 1979>349 (Besoins matière)
- [bureau au téléphone, alimentation, 375×812] `/production/besoins/1` : tableau plus large que son cadre 1043>341 (D’où vient le besoin)
- [bureau au téléphone, alimentation, 375×812] `/operations?onglet=transfert` : tableau plus large que son cadre 382>349 (Opérations)
- [bureau au téléphone, alimentation, 375×812] `/operations?onglet=retour_machine` : tableau plus large que son cadre 387>349 (Opérations)
- [bureau au téléphone, alimentation, 375×812] `/operations/nouvelle?type=transfert` : tableau plus large que son cadre 382>349 (Opérations)
- [bureau au téléphone, alimentation, 375×812] `/catalogue?onglet=matieres` : tableau plus large que son cadre 916>349 (Matières du catalogue)
- [bureau au téléphone, alimentation, 375×812] `/matieres/1?onglet=classification` : tableau plus large que son cadre 916>349 (Matières du catalogue)
- [bureau au téléphone, alimentation, 375×812] `/matieres/1?onglet=conditionnement` : tableau plus large que son cadre 916>349 (Matières du catalogue)
- [bureau au téléphone, alimentation, 375×812] `/matieres/1?onglet=historique` : tableau plus large que son cadre 916>349 (Matières du catalogue)
- [bureau au téléphone, alimentation, 375×812] `/qualites?onglet=qualites` : tableau plus large que son cadre 966>349 (Qualités)
- [bureau au téléphone, alimentation, 375×812] `/qualites?onglet=nomenclature` : tableau plus large que son cadre 491>349 (Nomenclature)
- [bureau au téléphone, alimentation, 375×812] `/qualites/1?onglet=recette` : tableau plus large que son cadre 966>349 (Qualités)
- [bureau au téléphone, alimentation, 375×812] `/qualites/1?onglet=recette` : tableau plus large que son cadre 545>341 (Recette)
- [bureau au téléphone, alimentation, 375×812] `/qualites/1?onglet=plan` : tableau plus large que son cadre 966>349 (Qualités)
- [bureau au téléphone, alimentation, 375×812] `/qualites/1?onglet=versions` : tableau plus large que son cadre 966>349 (Qualités)
- [bureau au téléphone, alimentation, 375×812] `/qualites/1?onglet=historique` : tableau plus large que son cadre 966>349 (Qualités)
- [bureau au téléphone, alimentation, 375×812] `/metiers` : tableau plus large que son cadre 874>349 (Métiers à tisser)
- [bureau au téléphone, alimentation, 375×812] `/metiers/2?onglet=fils` : tableau plus large que son cadre 874>349 (Métiers à tisser)
- [bureau au téléphone, alimentation, 375×812] `/metiers/2?onglet=fils` : tableau plus large que son cadre 588>341 (Fils montés)
- [bureau au téléphone, alimentation, 375×812] `/metiers/2?onglet=reglages` : tableau plus large que son cadre 874>349 (Métiers à tisser)
- [bureau au téléphone, alimentation, 375×812] `/metiers/2?onglet=historique` : tableau plus large que son cadre 874>349 (Métiers à tisser)
- [bureau au téléphone, alimentation, 375×812] `/metiers/2?onglet=historique` : tableau plus large que son cadre 712>341 (Montages)
- [bureau au téléphone, alimentation, 375×812] `/aide?onglet=calculs` : tableau plus large que son cadre 384>317 (2 col.)
- [bureau au téléphone, alimentation, 375×812] `/aide?onglet=analyse` : tableau plus large que son cadre 322>317 (0 col.)
- [bureau au téléphone, alimentation, 375×812] `/aide?onglet=ecrans` : tableau plus large que son cadre 344>317 (3 col.)

### x30

- [bureau, direction, 1440×900] `/cockpit?onglet=faire` : BLOQUANT 17035 ms — appel le plus lent : `/api/contexte` 8 387 ms
- [bureau, direction, 1440×900] `/cockpit?onglet=faire` : document BLOQUANT 6833 ms /api/documents/bilan?mois=2026-09
- [bureau, direction, 1440×900] `/cockpit?onglet=alertes` : BLOQUANT 5350 ms — appel le plus lent : `/api/brouillons` 3 609 ms
- [bureau, direction, 1440×900] `/cockpit?onglet=ensemble` : lent 2031 ms — appel le plus lent : `/api/commandes/ouverts` 1 666 ms
- [bureau, direction, 1440×900] `/cockpit?onglet=evolution` : lent 2082 ms — appel le plus lent : `/api/commandes/ouverts` 1 691 ms
- [bureau, direction, 1440×900] `/cockpit?onglet=economies` : lent 2573 ms — appel le plus lent : `/api/brouillons` 2 173 ms
- [bureau, direction, 1440×900] `/stock?onglet=matieres` : tableau plus large que son cadre 1951>1142 (Stock par matière)
- [bureau, direction, 1440×900] `/stock?onglet=matieres` : export lent 1438 ms /api/export/pilotage
- [bureau, direction, 1440×900] `/stock?onglet=lots` : BLOQUANT 5916 ms — appel le plus lent : `/api/lots` 1 859 ms
- [bureau, direction, 1440×900] `/stock?onglet=lots` : tableau sans pagination : 20160 lignes dans le DOM (Lots)
- [bureau, direction, 1440×900] `/stock?onglet=lots` : tableau plus large que son cadre 1313>1142 (Lots)
- [bureau, direction, 1440×900] `/stock?onglet=lots` : export BLOQUANT 3968 ms /api/export/lots
- [bureau, direction, 1440×900] `/stock?onglet=mouvements` : lent 1274 ms — appel le plus lent : `/api/mouvements?avec_valeur=true` 820 ms
- [bureau, direction, 1440×900] `/stock?onglet=mouvements` : recherche lente 2500 ms (« Plastique »)
- [bureau, direction, 1440×900] `/stock?onglet=mouvements` : export BLOQUANT 43578 ms /api/export/mouvements?avec_valeur=true
- [bureau, direction, 1440×900] `/stock?onglet=ordres` : BLOQUANT 4948 ms — appel le plus lent : `/api/ordres/consommation` 3 212 ms
- [bureau, direction, 1440×900] `/stock?onglet=ordres` : tableau sans pagination : 9570 lignes dans le DOM (Ordres de fabrication)
- [bureau, direction, 1440×900] `/stock?onglet=ordres` : export BLOQUANT 3332 ms /api/export/ordres?vue=consommation
- [bureau, direction, 1440×900] `/stock/matieres/111` : lent 1084 ms — appel le plus lent : `/api/brouillons` 700 ms
- [bureau, direction, 1440×900] `/stock/matieres/111` : tableau plus large que son cadre 1951>1142 (Stock par matière)
- [bureau, direction, 1440×900] `/lots/291565` : BLOQUANT 6315 ms — appel le plus lent : `/api/brouillons` 2 586 ms
- [bureau, direction, 1440×900] `/lots/291565` : tableau sans pagination : 20160 lignes dans le DOM (Lots)
- [bureau, direction, 1440×900] `/lots/291565` : tableau plus large que son cadre 1313>1142 (Lots)
- [bureau, direction, 1440×900] `/tracabilite?lot=291565` : BLOQUANT 5831 ms — appel le plus lent : `/api/brouillons` 3 914 ms
- [bureau, direction, 1440×900] `/tracabilite?lot=291565` : tableau sans pagination : 9570 lignes dans le DOM (Ordres de fabrication)
- [bureau, direction, 1440×900] `/tracabilite?matiere=111` : BLOQUANT 6805 ms — appel le plus lent : `/api/brouillons` 4 176 ms
- [bureau, direction, 1440×900] `/tracabilite?matiere=111` : tableau sans pagination : 9570 lignes dans le DOM (Ordres de fabrication)
- [bureau, direction, 1440×900] `/tracabilite?matiere=111` : tableau sans pagination : 1440 lignes dans le DOM (Mouvements suivis)
- [bureau, direction, 1440×900] `/sorties?onglet=valide` : BLOQUANT 7389 ms — appel le plus lent : `/api/ordres/apercu?statut=valide` 6 926 ms
- [bureau, direction, 1440×900] `/sorties?onglet=valide` : recherche lente 8141 ms (« Plastique »)
- [bureau, direction, 1440×900] `/sorties?onglet=valide` : export BLOQUANT 7207 ms /api/export/ordres?statut=valide
- [bureau, direction, 1440×900] `/ordres/nouveau` : BLOQUANT 13441 ms — appel le plus lent : `/api/ordres/apercu?statut=valide` 13 051 ms
- [bureau, direction, 1440×900] `/ordres/nouveau` : recherche lente 8749 ms (« Plastique »)
- [bureau, direction, 1440×900] `/ordres/29319` : BLOQUANT 8578 ms — appel le plus lent : `/api/ordres/apercu?statut=valide` 8 190 ms
- [bureau, direction, 1440×900] `/ordres/29319` : recherche lente 7918 ms (« Plastique »)
- [bureau, direction, 1440×900] `/ordres/29319/retour` : BLOQUANT 7720 ms — appel le plus lent : `/api/ordres/apercu?statut=valide` 7 012 ms
- [bureau, direction, 1440×900] `/ordres/29319/retour` : recherche lente 7607 ms (« Plastique »)
- [bureau, direction, 1440×900] `/production?onglet=plan` : tableau plus large que son cadre 1552>1142 (Plan de production)
- [bureau, direction, 1440×900] `/production?onglet=glissant` : tableau plus large que son cadre 1437>1142 (Plan glissant)
- [bureau, direction, 1440×900] `/production?onglet=realise` : tableau plus large que son cadre 1384>1142 (Plan et réalisé)
- [bureau, direction, 1440×900] `/production?onglet=besoins` : tableau plus large que son cadre 2325>1142 (Besoins matière)
- [bureau, direction, 1440×900] `/production/besoins/111` : tableau plus large que son cadre 2325>1142 (Besoins matière)
- [bureau, direction, 1440×900] `/commandes?onglet=brouillon` : lent 1581 ms — appel le plus lent : `/api/commandes/apercu` 1 202 ms
- [bureau, direction, 1440×900] `/commandes?onglet=a_approuver` : lent 1416 ms — appel le plus lent : `/api/commandes/apercu` 1 044 ms
- [bureau, direction, 1440×900] `/commandes?onglet=envoyee` : lent 1412 ms — appel le plus lent : `/api/commandes/apercu` 1 035 ms
- [bureau, direction, 1440×900] `/commandes?onglet=confirmee` : lent 2602 ms — appel le plus lent : `/api/commandes/apercu` 2 239 ms
- [bureau, direction, 1440×900] `/commandes?onglet=confirmee` : recherche lente 1045 ms (« HASIRCI »)
- [bureau, direction, 1440×900] `/commandes?onglet=confirmee` : export lent 2809 ms /api/export/commandes?statut=confirmee
- [bureau, direction, 1440×900] `/commandes?onglet=clos` : BLOQUANT 3549 ms — appel le plus lent : `/api/commandes/apercu?statut=clos` 3 169 ms
- [bureau, direction, 1440×900] `/commandes?onglet=clos` : recherche lente 1770 ms (« HASIRCI »)
- [bureau, direction, 1440×900] `/commandes?onglet=clos` : export BLOQUANT 9052 ms /api/export/commandes?statut=clos
- [bureau, direction, 1440×900] `/commandes/nouvelle` : lent 2978 ms — appel le plus lent : `/api/commandes/apercu` 1 304 ms
- [bureau, direction, 1440×900] `/commandes/nouvelle` : recherche lente 1054 ms (« HASIRCI »)
- [bureau, direction, 1440×900] `/commandes/29330?onglet=lignes` : lent 2518 ms — appel le plus lent : `/api/commandes/apercu?statut=confirmee` 1 223 ms
- [bureau, direction, 1440×900] `/commandes/29330?onglet=lignes` : recherche lente 1317 ms (« HASIRCI »)
- [bureau, direction, 1440×900] `/commandes/29330?onglet=prix` : BLOQUANT 3093 ms — appel le plus lent : `/api/commandes/apercu?statut=confirmee` 1 523 ms
- [bureau, direction, 1440×900] `/commandes/29330?onglet=prix` : recherche lente 1037 ms (« HASIRCI »)
- [bureau, direction, 1440×900] `/commandes/29330?onglet=expedition` : BLOQUANT 3011 ms — appel le plus lent : `/api/commandes/apercu` 1 429 ms
- [bureau, direction, 1440×900] `/commandes/29330?onglet=expedition` : recherche lente 1280 ms (« HASIRCI »)
- [bureau, direction, 1440×900] `/commandes/29330?onglet=receptions` : lent 2821 ms — appel le plus lent : `/api/commandes/apercu?statut=confirmee` 1 238 ms
- [bureau, direction, 1440×900] `/commandes/29330?onglet=receptions` : recherche lente 1345 ms (« HASIRCI »)
- [bureau, direction, 1440×900] `/commandes/29330?onglet=approbation` : BLOQUANT 3078 ms — appel le plus lent : `/api/commandes/apercu` 1 432 ms
- [bureau, direction, 1440×900] `/commandes/29330?onglet=approbation` : recherche lente 1292 ms (« HASIRCI »)
- [bureau, direction, 1440×900] `/commandes/29330?onglet=pieces` : lent 2641 ms — appel le plus lent : `/api/commandes/apercu?statut=confirmee` 1 213 ms
- [bureau, direction, 1440×900] `/commandes/29330?onglet=pieces` : recherche lente 1535 ms (« HASIRCI »)
- [bureau, direction, 1440×900] `/commandes/29330?onglet=historique` : lent 2830 ms — appel le plus lent : `/api/commandes/apercu?statut=confirmee` 1 606 ms
- [bureau, direction, 1440×900] `/commandes/29330?onglet=historique` : recherche lente 1304 ms (« HASIRCI »)
- [bureau, direction, 1440×900] `/receptions?onglet=brouillon` : BLOQUANT 4546 ms — appel le plus lent : `/api/receptions/pesees?limite=1` 4 184 ms
- [bureau, direction, 1440×900] `/receptions?onglet=validee` : BLOQUANT 4446 ms — appel le plus lent : `/api/receptions/pesees?limite=1` 4 052 ms
- [bureau, direction, 1440×900] `/receptions?onglet=validee` : recherche lente 2382 ms (« HASIRCI »)
- [bureau, direction, 1440×900] `/receptions?onglet=validee` : export BLOQUANT 14319 ms /api/export/receptions?statut=validee
- [bureau, direction, 1440×900] `/receptions?onglet=annulee` : BLOQUANT 4190 ms — appel le plus lent : `/api/receptions/pesees?limite=1` 3 781 ms
- [bureau, direction, 1440×900] `/receptions?onglet=reclamations` : BLOQUANT 4353 ms — appel le plus lent : `/api/receptions/pesees?limite=1` 3 981 ms
- [bureau, direction, 1440×900] `/receptions?onglet=bobines` : BLOQUANT 4610 ms — appel le plus lent : `/api/receptions/bobines` 4 197 ms
- [bureau, direction, 1440×900] `/receptions?onglet=bobines` : export lent 2098 ms /api/export/receptions/bobines
- [bureau, direction, 1440×900] `/receptions?onglet=pesees` : BLOQUANT 7895 ms — appel le plus lent : `/api/receptions/pesees?limite=1` 7 496 ms
- [bureau, direction, 1440×900] `/receptions?onglet=pesees` : recherche lente 4100 ms (« HASIRCI »)
- [bureau, direction, 1440×900] `/receptions?onglet=pesees` : export BLOQUANT 11098 ms /api/export/receptions/pesees
- [bureau, direction, 1440×900] `/receptions/nouvelle` : api: échec /api/receptions?statut=validee, échec /api/receptions?statut=validee&limite=1
- [bureau, direction, 1440×900] `/receptions/nouvelle` : BLOQUANT 4910 ms — appel le plus lent : `/api/receptions/pesees?limite=1` 4 521 ms
- [bureau, direction, 1440×900] `/receptions/29321?onglet=lignes` : api: échec /api/receptions?statut=validee, échec /api/receptions?statut=validee&limite=1
- [bureau, direction, 1440×900] `/receptions/29321?onglet=lignes` : BLOQUANT 4950 ms — appel le plus lent : `/api/receptions/pesees?limite=1` 4 562 ms
- [bureau, direction, 1440×900] `/receptions/29321?onglet=reclamations` : api: échec /api/receptions?statut=validee, échec /api/receptions?statut=validee&limite=1
- [bureau, direction, 1440×900] `/receptions/29321?onglet=reclamations` : BLOQUANT 4858 ms — appel le plus lent : `/api/receptions/pesees?limite=1` 4 470 ms
- [bureau, direction, 1440×900] `/receptions/29321?onglet=pieces` : api: échec /api/receptions?statut=validee, échec /api/receptions?statut=validee&limite=1
- [bureau, direction, 1440×900] `/receptions/29321?onglet=pieces` : BLOQUANT 4324 ms — appel le plus lent : `/api/receptions/pesees?limite=1` 3 955 ms
- [bureau, direction, 1440×900] `/receptions/29321?onglet=historique` : api: échec /api/receptions?statut=validee, échec /api/receptions?statut=validee&limite=1
- [bureau, direction, 1440×900] `/receptions/29321?onglet=historique` : BLOQUANT 4820 ms — appel le plus lent : `/api/receptions/pesees?limite=1` 4 419 ms
- [bureau, direction, 1440×900] `/reclamations/nouvelle` : api: échec /api/receptions?statut=validee, échec /api/receptions?statut=validee&limite=1
- [bureau, direction, 1440×900] `/reclamations/nouvelle` : BLOQUANT 4906 ms — appel le plus lent : `/api/receptions/pesees?limite=1` 4 514 ms
- [bureau, direction, 1440×900] `/reclamations/nouvelle` : recherche lente 2541 ms (« Plastique »)
- [bureau, direction, 1440×900] `/importations?onglet=ouverts` : BLOQUANT 3387 ms — appel le plus lent : `/api/dossiers/apercu` 2 997 ms
- [bureau, direction, 1440×900] `/importations?onglet=ouverts` : tableau plus large que son cadre 1283>1142 (Dossiers ouverts)
- [bureau, direction, 1440×900] `/importations?onglet=ouverts` : export lent 2001 ms /api/export/dossiers?statut=ouvert
- [bureau, direction, 1440×900] `/importations?onglet=clos` : BLOQUANT 3912 ms — appel le plus lent : `/api/dossiers/apercu` 3 514 ms
- [bureau, direction, 1440×900] `/importations?onglet=clos` : tableau plus large que son cadre 1396>1142 (Dossiers clos)
- [bureau, direction, 1440×900] `/importations?onglet=clos` : export BLOQUANT 8350 ms /api/export/dossiers?statut=clos
- [bureau, direction, 1440×900] `/importations?onglet=rattacher` : BLOQUANT 3184 ms — appel le plus lent : `/api/dossiers?statut=clos&limite=5000` 2 786 ms
- [bureau, direction, 1440×900] `/dossiers/nouveau?onglet=facture` : BLOQUANT 4663 ms — appel le plus lent : `/api/dossiers/apercu` 4 254 ms
- [bureau, direction, 1440×900] `/dossiers/nouveau?onglet=facture` : tableau plus large que son cadre 1283>1142 (Dossiers ouverts)
- [bureau, direction, 1440×900] `/dossiers/nouveau?onglet=main` : BLOQUANT 3801 ms — appel le plus lent : `/api/dossiers/apercu` 3 402 ms
- [bureau, direction, 1440×900] `/dossiers/nouveau?onglet=main` : tableau plus large que son cadre 1283>1142 (Dossiers ouverts)
- [bureau, direction, 1440×900] `/dossiers/2990?onglet=familles` : BLOQUANT 3271 ms — appel le plus lent : `/api/dossiers/apercu` 2 864 ms
- [bureau, direction, 1440×900] `/dossiers/2990?onglet=familles` : tableau plus large que son cadre 1283>1142 (Dossiers ouverts)
- [bureau, direction, 1440×900] `/dossiers/2990?onglet=marchandises` : BLOQUANT 4185 ms — appel le plus lent : `/api/dossiers/apercu` 3 792 ms
- [bureau, direction, 1440×900] `/dossiers/2990?onglet=marchandises` : tableau plus large que son cadre 1283>1142 (Dossiers ouverts)
- [bureau, direction, 1440×900] `/dossiers/2990?onglet=marchandises` : tableau plus large que son cadre 1527>1206 (Marchandises du dossier)
- [bureau, direction, 1440×900] `/dossiers/2990?onglet=frais` : BLOQUANT 3290 ms — appel le plus lent : `/api/dossiers/apercu` 2 885 ms
- [bureau, direction, 1440×900] `/dossiers/2990?onglet=frais` : tableau plus large que son cadre 1283>1142 (Dossiers ouverts)
- [bureau, direction, 1440×900] `/dossiers/2990?onglet=frais` : tableau plus large que son cadre 1404>1206 (Frais du dossier)
- [bureau, direction, 1440×900] `/dossiers/2990?onglet=echeancier` : BLOQUANT 4077 ms — appel le plus lent : `/api/dossiers/apercu` 3 671 ms
- [bureau, direction, 1440×900] `/dossiers/2990?onglet=echeancier` : tableau plus large que son cadre 1283>1142 (Dossiers ouverts)
- [bureau, direction, 1440×900] `/dossiers/2990?onglet=pieces` : BLOQUANT 4093 ms — appel le plus lent : `/api/dossiers/apercu` 3 705 ms
- [bureau, direction, 1440×900] `/dossiers/2990?onglet=pieces` : tableau plus large que son cadre 1283>1142 (Dossiers ouverts)
- [bureau, direction, 1440×900] `/dossiers/2990?onglet=facture` : BLOQUANT 3497 ms — appel le plus lent : `/api/dossiers/apercu` 3 107 ms
- [bureau, direction, 1440×900] `/dossiers/2990?onglet=facture` : tableau plus large que son cadre 1283>1142 (Dossiers ouverts)
- [bureau, direction, 1440×900] `/dossiers/2990?onglet=historique` : BLOQUANT 3832 ms — appel le plus lent : `/api/dossiers/apercu` 3 432 ms
- [bureau, direction, 1440×900] `/dossiers/2990?onglet=historique` : tableau plus large que son cadre 1283>1142 (Dossiers ouverts)
- [bureau, direction, 1440×900] `/inventaire?onglet=cours` : lent 1243 ms — appel le plus lent : `/api/inventaires` 845 ms
- [bureau, direction, 1440×900] `/inventaire?onglet=passes` : lent 1651 ms — appel le plus lent : `/api/inventaires` 1 258 ms
- [bureau, direction, 1440×900] `/inventaire?onglet=passes` : tableau plus large que son cadre 1187>1142 (Inventaires clos)
- [bureau, direction, 1440×900] `/inventaire?onglet=passes` : export lent 1237 ms /api/export/inventaires
- [bureau, direction, 1440×900] `/inventaires/nouveau` : lent 2221 ms — appel le plus lent : `/api/lots?non_nuls=true` 1 844 ms
- [bureau, direction, 1440×900] `/inventaires/2912?onglet=lots` : lent 1578 ms — appel le plus lent : `/api/inventaires` 1 179 ms
- [bureau, direction, 1440×900] `/inventaires/2912?onglet=lots` : tableau plus large que son cadre 1187>1142 (Inventaires clos)
- [bureau, direction, 1440×900] `/inventaires/2912?onglet=lots` : tableau plus large que son cadre 1603>1206 (Lots à compter)
- [bureau, direction, 1440×900] `/inventaires/2912?onglet=pieces` : lent 2482 ms — appel le plus lent : `/api/inventaires` 2 095 ms
- [bureau, direction, 1440×900] `/inventaires/2912?onglet=pieces` : tableau plus large que son cadre 1187>1142 (Inventaires clos)
- [bureau, direction, 1440×900] `/inventaires/2912?onglet=historique` : lent 2132 ms — appel le plus lent : `/api/inventaires` 1 746 ms
- [bureau, direction, 1440×900] `/inventaires/2912?onglet=historique` : tableau plus large que son cadre 1187>1142 (Inventaires clos)
- [bureau, direction, 1440×900] `/operations?onglet=retour_machine` : lent 1162 ms — appel le plus lent : `/api/brouillons` 775 ms
- [bureau, direction, 1440×900] `/operations?onglet=ajustement` : lent 1123 ms — appel le plus lent : `/api/brouillons` 751 ms
- [bureau, direction, 1440×900] `/operations/nouvelle?type=transfert` : lent 1123 ms — appel le plus lent : `/api/brouillons` 762 ms
- [bureau, direction, 1440×900] `/fournisseurs/nouveau` : lent 1122 ms — appel le plus lent : `/api/matieres` 756 ms
- [bureau, direction, 1440×900] `/metiers/1?onglet=fils` : lent 1206 ms — appel le plus lent : `/api/montage/matieres` 552 ms
- [bureau, direction, 1440×900] `/metiers/1?onglet=historique` : lent 1285 ms — appel le plus lent : `/api/metiers` 676 ms
- [bureau, direction, 1440×900] `/analyse?onglet=valorisation` : lent 1532 ms — appel le plus lent : `/api/controles` 1 147 ms
- [bureau, direction, 1440×900] `/analyse?onglet=valorisation` : tableau plus large que son cadre 1281>1142 (Valorisation par matière)
- [bureau, direction, 1440×900] `/analyse?onglet=matrice` : lent 1511 ms — appel le plus lent : `/api/opportunites?meme_couleur=true&autre_fournisseur=true&prix_catalogue=false` 1 117 ms
- [bureau, direction, 1440×900] `/analyse?onglet=matrice` : tableau plus large que son cadre 3617>1142 (Matrice des prix)
- [bureau, direction, 1440×900] `/analyse?onglet=matrice` : export BLOQUANT 5627 ms /api/export/prix
- [bureau, direction, 1440×900] `/analyse?onglet=historique` : BLOQUANT 6844 ms — appel le plus lent : `/api/controles` 927 ms
- [bureau, direction, 1440×900] `/analyse?onglet=historique` : tableau sans pagination : 43290 lignes dans le DOM (Prix payés)
- [bureau, direction, 1440×900] `/analyse?onglet=opportunites` : lent 1412 ms — appel le plus lent : `/api/prix/historique` 953 ms
- [bureau, direction, 1440×900] `/analyse?onglet=opportunites` : tableau plus large que son cadre 1299>1142 (Opportunités d’économies)
- [bureau, direction, 1440×900] `/analyse?onglet=fournisseurs` : lent 1345 ms — appel le plus lent : `/api/prix/historique` 909 ms
- [bureau, direction, 1440×900] `/analyse?onglet=fournisseurs` : tableau plus large que son cadre 1297>1142 (Classement des fournisseurs)
- [bureau, direction, 1440×900] `/analyse?onglet=fournisseurs` : export lent 1285 ms /api/export/fournisseurs
- [bureau, direction, 1440×900] `/analyse?onglet=revient` : lent 2266 ms — appel le plus lent : `/api/prix/historique` 1 790 ms
- [bureau, direction, 1440×900] `/analyse?onglet=revient` : tableau plus large que son cadre 1187>1116 (Coût de revient regroupé)
- [bureau, direction, 1440×900] `/analyse?onglet=revient` : recherche lente 1066 ms (« Plastique »)
- [bureau, direction, 1440×900] `/analyse?onglet=revient` : export BLOQUANT 3897 ms /api/export/revient?axe=titrage
- [bureau, direction, 1440×900] `/analyse?onglet=echeancier` : BLOQUANT 3455 ms — appel le plus lent : `/api/echeancier` 1 732 ms
- [bureau, direction, 1440×900] `/analyse?onglet=echeancier` : tableau sans pagination : 9480 lignes dans le DOM (Échéancier — echeances)
- [bureau, direction, 1440×900] `/analyse?onglet=echeancier` : export BLOQUANT 4320 ms /api/export/echeancier
- [bureau, direction, 1440×900] `/analyse?onglet=controles` : lent 1797 ms — appel le plus lent : `/api/controles/soldes` 1 400 ms
- [bureau, direction, 1440×900] `/analyse?onglet=production` : BLOQUANT 5644 ms — appel le plus lent : `/api/ordres/consommation` 4 644 ms
- [bureau, direction, 1440×900] `/analyse?onglet=production` : tableau sans pagination : 9570 lignes dans le DOM (Rendement par ordre)
- [bureau, direction, 1440×900] `/administration?onglet=journal` : export BLOQUANT 8824 ms /api/export/journal
- [bureau, direction, 1440×900] `/administration?onglet=courriel` : BLOQUANT 3159 ms — appel le plus lent : `/api/courriel/apercu` 2 771 ms
- [bureau, direction, 1440×900] `/administration?onglet=reprise` : BLOQUANT 6355 ms — appel le plus lent : `/api/reprise` 5 999 ms
- [bureau, direction, 1440×900] `/administration?onglet=donnees` : tableau plus large que son cadre 3060>1142 (Table matiere)
- [bureau, achats, 1440×900] `/accueil` : BLOQUANT 13926 ms — appel le plus lent : `/api/contexte` 9 760 ms
- [bureau, achats, 1440×900] `/stock?onglet=matieres` : BLOQUANT 8999 ms — appel le plus lent : `/api/stock` 8 568 ms
- [bureau, achats, 1440×900] `/stock?onglet=matieres` : tableau plus large que son cadre 1951>1142 (Stock par matière)
- [bureau, achats, 1440×900] `/stock?onglet=matieres` : export lent 1237 ms /api/export/pilotage
- [bureau, achats, 1440×900] `/stock?onglet=lots` : BLOQUANT 6969 ms — appel le plus lent : `/api/lots` 1 688 ms
- [bureau, achats, 1440×900] `/stock?onglet=lots` : tableau sans pagination : 20160 lignes dans le DOM (Lots)
- [bureau, achats, 1440×900] `/stock?onglet=lots` : tableau plus large que son cadre 1313>1142 (Lots)
- [bureau, achats, 1440×900] `/stock?onglet=lots` : export BLOQUANT 4181 ms /api/export/lots
- [bureau, achats, 1440×900] `/stock?onglet=mouvements` : lent 1868 ms — appel le plus lent : `/api/brouillons` 1 459 ms
- [bureau, achats, 1440×900] `/stock?onglet=mouvements` : recherche lente 2212 ms (« Plastique »)
- [bureau, achats, 1440×900] `/stock?onglet=mouvements` : export BLOQUANT 43756 ms /api/export/mouvements?avec_valeur=true
- [bureau, achats, 1440×900] `/stock?onglet=ordres` : BLOQUANT 5087 ms — appel le plus lent : `/api/ordres/consommation` 3 370 ms
- [bureau, achats, 1440×900] `/stock?onglet=ordres` : tableau sans pagination : 9570 lignes dans le DOM (Ordres de fabrication)
- [bureau, achats, 1440×900] `/stock?onglet=ordres` : export BLOQUANT 3203 ms /api/export/ordres?vue=consommation
- [bureau, achats, 1440×900] `/stock/matieres/111` : lent 1494 ms — appel le plus lent : `/api/brouillons` 1 069 ms
- [bureau, achats, 1440×900] `/stock/matieres/111` : tableau plus large que son cadre 1951>1142 (Stock par matière)
- [bureau, achats, 1440×900] `/lots/291565` : BLOQUANT 5541 ms — appel le plus lent : `/api/lots` 1 731 ms
- [bureau, achats, 1440×900] `/lots/291565` : tableau sans pagination : 20160 lignes dans le DOM (Lots)
- [bureau, achats, 1440×900] `/lots/291565` : tableau plus large que son cadre 1313>1142 (Lots)
- [bureau, achats, 1440×900] `/tracabilite?lot=291565` : BLOQUANT 5958 ms — appel le plus lent : `/api/brouillons` 4 002 ms
- [bureau, achats, 1440×900] `/tracabilite?lot=291565` : tableau sans pagination : 9570 lignes dans le DOM (Ordres de fabrication)
- [bureau, achats, 1440×900] `/tracabilite?matiere=111` : BLOQUANT 5721 ms — appel le plus lent : `/api/ordres/consommation` 3 876 ms
- [bureau, achats, 1440×900] `/tracabilite?matiere=111` : tableau sans pagination : 9570 lignes dans le DOM (Ordres de fabrication)
- [bureau, achats, 1440×900] `/tracabilite?matiere=111` : tableau sans pagination : 1440 lignes dans le DOM (Mouvements suivis)
- [bureau, achats, 1440×900] `/sorties?onglet=valide` : BLOQUANT 10237 ms — appel le plus lent : `/api/ordres/apercu?statut=valide` 8 408 ms
- [bureau, achats, 1440×900] `/sorties?onglet=valide` : recherche lente 8157 ms (« Plastique »)
- [bureau, achats, 1440×900] `/sorties?onglet=valide` : export BLOQUANT 6721 ms /api/export/ordres?statut=valide
- [bureau, achats, 1440×900] `/ordres/29319` : BLOQUANT 8762 ms — appel le plus lent : `/api/ordres/apercu?statut=valide` 8 386 ms
- [bureau, achats, 1440×900] `/ordres/29319` : recherche lente 7890 ms (« Plastique »)
- [bureau, achats, 1440×900] `/production?onglet=plan` : tableau plus large que son cadre 1372>1142 (Plan de production)
- [bureau, achats, 1440×900] `/production?onglet=glissant` : tableau plus large que son cadre 1437>1142 (Plan glissant)
- [bureau, achats, 1440×900] `/production?onglet=realise` : tableau plus large que son cadre 1384>1142 (Plan et réalisé)
- [bureau, achats, 1440×900] `/production?onglet=besoins` : tableau plus large que son cadre 2325>1142 (Besoins matière)
- [bureau, achats, 1440×900] `/production/besoins/111` : tableau plus large que son cadre 2325>1142 (Besoins matière)
- [bureau, achats, 1440×900] `/commandes?onglet=brouillon` : lent 1203 ms — appel le plus lent : `/api/commandes/apercu` 824 ms
- [bureau, achats, 1440×900] `/commandes?onglet=envoyee` : lent 1537 ms — appel le plus lent : `/api/commandes/apercu` 1 176 ms
- [bureau, achats, 1440×900] `/commandes?onglet=confirmee` : lent 1833 ms — appel le plus lent : `/api/commandes/apercu?statut=confirmee` 1 450 ms
- [bureau, achats, 1440×900] `/commandes?onglet=confirmee` : recherche lente 1417 ms (« HASIRCI »)
- [bureau, achats, 1440×900] `/commandes?onglet=confirmee` : export lent 2903 ms /api/export/commandes?statut=confirmee
- [bureau, achats, 1440×900] `/commandes?onglet=clos` : BLOQUANT 3053 ms — appel le plus lent : `/api/commandes/apercu?statut=clos` 2 676 ms
- [bureau, achats, 1440×900] `/commandes?onglet=clos` : recherche lente 1407 ms (« HASIRCI »)
- [bureau, achats, 1440×900] `/commandes?onglet=clos` : export BLOQUANT 8985 ms /api/export/commandes?statut=clos
- [bureau, achats, 1440×900] `/commandes/nouvelle` : BLOQUANT 3201 ms — appel le plus lent : `/api/commandes/apercu` 1 431 ms
- [bureau, achats, 1440×900] `/commandes/nouvelle` : recherche lente 1077 ms (« HASIRCI »)
- [bureau, achats, 1440×900] `/commandes/29330?onglet=lignes` : lent 2463 ms — appel le plus lent : `/api/commandes/apercu` 1 260 ms
- [bureau, achats, 1440×900] `/commandes/29330?onglet=lignes` : recherche lente 1110 ms (« HASIRCI »)
- [bureau, achats, 1440×900] `/commandes/29330?onglet=prix` : BLOQUANT 3060 ms — appel le plus lent : `/api/commandes/apercu?statut=confirmee` 1 366 ms
- [bureau, achats, 1440×900] `/commandes/29330?onglet=prix` : recherche lente 1420 ms (« HASIRCI »)
- [bureau, achats, 1440×900] `/commandes/29330?onglet=expedition` : BLOQUANT 3053 ms — appel le plus lent : `/api/commandes/apercu?statut=confirmee` 1 374 ms
- [bureau, achats, 1440×900] `/commandes/29330?onglet=expedition` : recherche lente 1455 ms (« HASIRCI »)
- [bureau, achats, 1440×900] `/commandes/29330?onglet=receptions` : BLOQUANT 3074 ms — appel le plus lent : `/api/commandes/apercu?statut=confirmee` 1 371 ms
- [bureau, achats, 1440×900] `/commandes/29330?onglet=receptions` : recherche lente 1461 ms (« HASIRCI »)
- [bureau, achats, 1440×900] `/commandes/29330?onglet=approbation` : BLOQUANT 3058 ms — appel le plus lent : `/api/commandes/apercu?statut=confirmee` 1 358 ms
- [bureau, achats, 1440×900] `/commandes/29330?onglet=approbation` : recherche lente 1085 ms (« HASIRCI »)
- [bureau, achats, 1440×900] `/commandes/29330?onglet=pieces` : lent 2888 ms — appel le plus lent : `/api/commandes/apercu` 1 339 ms
- [bureau, achats, 1440×900] `/commandes/29330?onglet=pieces` : recherche lente 1093 ms (« HASIRCI »)
- [bureau, achats, 1440×900] `/commandes/29330?onglet=historique` : lent 2951 ms — appel le plus lent : `/api/commandes/apercu?statut=confirmee` 1 366 ms
- [bureau, achats, 1440×900] `/commandes/29330?onglet=historique` : recherche lente 1081 ms (« HASIRCI »)
- [bureau, achats, 1440×900] `/receptions?onglet=brouillon` : BLOQUANT 4286 ms — appel le plus lent : `/api/receptions/pesees?limite=1` 3 906 ms
- [bureau, achats, 1440×900] `/receptions?onglet=validee` : BLOQUANT 5453 ms — appel le plus lent : `/api/receptions/pesees?limite=1` 5 078 ms
- [bureau, achats, 1440×900] `/receptions?onglet=validee` : recherche lente 2097 ms (« HASIRCI »)
- [bureau, achats, 1440×900] `/receptions?onglet=validee` : export BLOQUANT 14157 ms /api/export/receptions?statut=validee
- [bureau, achats, 1440×900] `/receptions?onglet=annulee` : BLOQUANT 4438 ms — appel le plus lent : `/api/receptions/pesees?limite=1` 4 045 ms
- [bureau, achats, 1440×900] `/receptions?onglet=reclamations` : BLOQUANT 4319 ms — appel le plus lent : `/api/receptions/pesees?limite=1` 3 969 ms
- [bureau, achats, 1440×900] `/receptions?onglet=bobines` : BLOQUANT 4627 ms — appel le plus lent : `/api/receptions/pesees?limite=1` 4 247 ms
- [bureau, achats, 1440×900] `/receptions?onglet=bobines` : export BLOQUANT 6011 ms /api/export/receptions/bobines
- [bureau, achats, 1440×900] `/receptions?onglet=pesees` : BLOQUANT 8133 ms — appel le plus lent : `/api/receptions/pesees` 7 704 ms
- [bureau, achats, 1440×900] `/receptions?onglet=pesees` : recherche lente 4702 ms (« HASIRCI »)
- [bureau, achats, 1440×900] `/receptions?onglet=pesees` : export BLOQUANT 11315 ms /api/export/receptions/pesees
- [bureau, achats, 1440×900] `/receptions/nouvelle` : api: échec /api/receptions?statut=validee, échec /api/receptions?statut=validee&limite=1
- [bureau, achats, 1440×900] `/receptions/nouvelle` : BLOQUANT 5670 ms — appel le plus lent : `/api/receptions/pesees?limite=1` 5 292 ms
- [bureau, achats, 1440×900] `/receptions/29321?onglet=lignes` : api: échec /api/receptions?statut=validee, échec /api/receptions?statut=validee&limite=1
- [bureau, achats, 1440×900] `/receptions/29321?onglet=lignes` : BLOQUANT 4910 ms — appel le plus lent : `/api/receptions/pesees?limite=1` 4 523 ms
- [bureau, achats, 1440×900] `/receptions/29321?onglet=reclamations` : api: échec /api/receptions?statut=validee, échec /api/receptions?statut=validee&limite=1
- [bureau, achats, 1440×900] `/receptions/29321?onglet=reclamations` : BLOQUANT 5732 ms — appel le plus lent : `/api/receptions/pesees?limite=1` 5 362 ms
- [bureau, achats, 1440×900] `/receptions/29321?onglet=pieces` : api: échec /api/receptions?statut=validee, échec /api/receptions?statut=validee&limite=1
- [bureau, achats, 1440×900] `/receptions/29321?onglet=pieces` : BLOQUANT 5853 ms — appel le plus lent : `/api/receptions/pesees?limite=1` 5 482 ms
- [bureau, achats, 1440×900] `/receptions/29321?onglet=historique` : api: échec /api/receptions?statut=validee, échec /api/receptions?statut=validee&limite=1
- [bureau, achats, 1440×900] `/receptions/29321?onglet=historique` : BLOQUANT 5597 ms — appel le plus lent : `/api/receptions/pesees?limite=1` 5 211 ms
- [bureau, achats, 1440×900] `/reclamations/nouvelle` : api: échec /api/receptions?statut=validee, échec /api/receptions?statut=validee&limite=1
- [bureau, achats, 1440×900] `/reclamations/nouvelle` : BLOQUANT 5607 ms — appel le plus lent : `/api/receptions/pesees?limite=1` 5 240 ms
- [bureau, achats, 1440×900] `/reclamations/nouvelle` : recherche lente 2961 ms (« Plastique »)
- [bureau, achats, 1440×900] `/importations?onglet=ouverts` : BLOQUANT 4273 ms — appel le plus lent : `/api/dossiers/apercu` 3 883 ms
- [bureau, achats, 1440×900] `/importations?onglet=ouverts` : tableau plus large que son cadre 1283>1142 (Dossiers ouverts)
- [bureau, achats, 1440×900] `/importations?onglet=ouverts` : export lent 1758 ms /api/export/dossiers?statut=ouvert
- [bureau, achats, 1440×900] `/importations?onglet=clos` : BLOQUANT 4007 ms — appel le plus lent : `/api/dossiers/apercu` 3 618 ms
- [bureau, achats, 1440×900] `/importations?onglet=clos` : tableau plus large que son cadre 1396>1142 (Dossiers clos)
- [bureau, achats, 1440×900] `/importations?onglet=clos` : export BLOQUANT 8295 ms /api/export/dossiers?statut=clos
- [bureau, achats, 1440×900] `/importations?onglet=rattacher` : BLOQUANT 5189 ms — appel le plus lent : `/api/dossiers/apercu` 4 800 ms
- [bureau, achats, 1440×900] `/dossiers/nouveau?onglet=facture` : BLOQUANT 4275 ms — appel le plus lent : `/api/dossiers/apercu` 3 892 ms
- [bureau, achats, 1440×900] `/dossiers/nouveau?onglet=facture` : tableau plus large que son cadre 1283>1142 (Dossiers ouverts)
- [bureau, achats, 1440×900] `/dossiers/nouveau?onglet=main` : BLOQUANT 4193 ms — appel le plus lent : `/api/dossiers/apercu` 3 809 ms
- [bureau, achats, 1440×900] `/dossiers/nouveau?onglet=main` : tableau plus large que son cadre 1283>1142 (Dossiers ouverts)
- [bureau, achats, 1440×900] `/dossiers/2990?onglet=familles` : BLOQUANT 3965 ms — appel le plus lent : `/api/dossiers/apercu` 3 563 ms
- [bureau, achats, 1440×900] `/dossiers/2990?onglet=familles` : tableau plus large que son cadre 1283>1142 (Dossiers ouverts)
- [bureau, achats, 1440×900] `/dossiers/2990?onglet=marchandises` : BLOQUANT 3515 ms — appel le plus lent : `/api/dossiers/apercu` 3 123 ms
- [bureau, achats, 1440×900] `/dossiers/2990?onglet=marchandises` : tableau plus large que son cadre 1283>1142 (Dossiers ouverts)
- [bureau, achats, 1440×900] `/dossiers/2990?onglet=marchandises` : tableau plus large que son cadre 1527>1206 (Marchandises du dossier)
- [bureau, achats, 1440×900] `/dossiers/2990?onglet=frais` : BLOQUANT 4203 ms — appel le plus lent : `/api/dossiers/apercu` 3 819 ms
- [bureau, achats, 1440×900] `/dossiers/2990?onglet=frais` : tableau plus large que son cadre 1283>1142 (Dossiers ouverts)
- [bureau, achats, 1440×900] `/dossiers/2990?onglet=frais` : tableau plus large que son cadre 1404>1206 (Frais du dossier)
- [bureau, achats, 1440×900] `/dossiers/2990?onglet=echeancier` : BLOQUANT 3463 ms — appel le plus lent : `/api/dossiers/apercu` 3 069 ms
- [bureau, achats, 1440×900] `/dossiers/2990?onglet=echeancier` : tableau plus large que son cadre 1283>1142 (Dossiers ouverts)
- [bureau, achats, 1440×900] `/dossiers/2990?onglet=pieces` : BLOQUANT 3942 ms — appel le plus lent : `/api/dossiers/apercu` 3 507 ms
- [bureau, achats, 1440×900] `/dossiers/2990?onglet=pieces` : tableau plus large que son cadre 1283>1142 (Dossiers ouverts)
- [bureau, achats, 1440×900] `/dossiers/2990?onglet=facture` : BLOQUANT 3307 ms — appel le plus lent : `/api/dossiers/apercu` 2 922 ms
- [bureau, achats, 1440×900] `/dossiers/2990?onglet=facture` : tableau plus large que son cadre 1283>1142 (Dossiers ouverts)
- [bureau, achats, 1440×900] `/dossiers/2990?onglet=historique` : BLOQUANT 3567 ms — appel le plus lent : `/api/dossiers/apercu` 3 175 ms
- [bureau, achats, 1440×900] `/dossiers/2990?onglet=historique` : tableau plus large que son cadre 1283>1142 (Dossiers ouverts)
- [bureau, achats, 1440×900] `/inventaire?onglet=cours` : lent 1623 ms — appel le plus lent : `/api/inventaires` 1 242 ms
- [bureau, achats, 1440×900] `/inventaire?onglet=passes` : lent 1640 ms — appel le plus lent : `/api/inventaires` 1 259 ms
- [bureau, achats, 1440×900] `/inventaire?onglet=passes` : tableau plus large que son cadre 1187>1142 (Inventaires clos)
- [bureau, achats, 1440×900] `/inventaire?onglet=passes` : export lent 1338 ms /api/export/inventaires
- [bureau, achats, 1440×900] `/inventaires/nouveau` : BLOQUANT 3408 ms — appel le plus lent : `/api/lots?non_nuls=true` 2 975 ms
- [bureau, achats, 1440×900] `/inventaires/2912?onglet=lots` : lent 2183 ms — appel le plus lent : `/api/inventaires` 1 782 ms
- [bureau, achats, 1440×900] `/inventaires/2912?onglet=lots` : tableau plus large que son cadre 1187>1142 (Inventaires clos)
- [bureau, achats, 1440×900] `/inventaires/2912?onglet=lots` : tableau plus large que son cadre 1603>1206 (Lots à compter)
- [bureau, achats, 1440×900] `/inventaires/2912?onglet=pieces` : lent 2170 ms — appel le plus lent : `/api/inventaires` 1 780 ms
- [bureau, achats, 1440×900] `/inventaires/2912?onglet=pieces` : tableau plus large que son cadre 1187>1142 (Inventaires clos)
- [bureau, achats, 1440×900] `/inventaires/2912?onglet=historique` : lent 2502 ms — appel le plus lent : `/api/inventaires` 2 104 ms
- [bureau, achats, 1440×900] `/inventaires/2912?onglet=historique` : tableau plus large que son cadre 1187>1142 (Inventaires clos)
- [bureau, achats, 1440×900] `/operations?onglet=retour_machine` : lent 1175 ms — appel le plus lent : `/api/brouillons` 794 ms
- [bureau, achats, 1440×900] `/operations?onglet=retour_fournisseur` : lent 1124 ms — appel le plus lent : `/api/brouillons` 765 ms
- [bureau, achats, 1440×900] `/operations/nouvelle?type=ajustement` : lent 1165 ms — appel le plus lent : `/api/brouillons` 801 ms
- [bureau, achats, 1440×900] `/catalogue?onglet=fournisseurs` : lent 1125 ms — appel le plus lent : `/api/fournisseurs/performance` 754 ms
- [bureau, achats, 1440×900] `/fournisseurs/1?onglet=pieces` : lent 1122 ms — appel le plus lent : `/api/fournisseurs/performance` 764 ms
- [bureau, achats, 1440×900] `/metiers` : lent 1041 ms — appel le plus lent : `/api/metiers` 668 ms
- [bureau, achats, 1440×900] `/metiers/1?onglet=fils` : lent 1451 ms — appel le plus lent : `/api/montage/matieres` 689 ms
- [bureau, achats, 1440×900] `/metiers/1?onglet=historique` : lent 1413 ms — appel le plus lent : `/api/metiers/1` 779 ms
- [bureau, achats, 1440×900] `/analyse?onglet=valorisation` : lent 1716 ms — appel le plus lent : `/api/opportunites?meme_couleur=true&autre_fournisseur=true&prix_catalogue=false` 1 357 ms
- [bureau, achats, 1440×900] `/analyse?onglet=valorisation` : tableau plus large que son cadre 1281>1142 (Valorisation par matière)
- [bureau, achats, 1440×900] `/analyse?onglet=valorisation` : document BLOQUANT 7721 ms /api/documents/bilan?mois=2026-09
- [bureau, achats, 1440×900] `/analyse?onglet=matrice` : lent 1473 ms — appel le plus lent : `/api/controles` 944 ms
- [bureau, achats, 1440×900] `/analyse?onglet=matrice` : tableau plus large que son cadre 3617>1142 (Matrice des prix)
- [bureau, achats, 1440×900] `/analyse?onglet=matrice` : export BLOQUANT 6288 ms /api/export/prix
- [bureau, achats, 1440×900] `/analyse?onglet=historique` : BLOQUANT 7158 ms — appel le plus lent : `/api/controles` 940 ms
- [bureau, achats, 1440×900] `/analyse?onglet=historique` : tableau sans pagination : 43290 lignes dans le DOM (Prix payés)
- [bureau, achats, 1440×900] `/analyse?onglet=opportunites` : lent 1484 ms — appel le plus lent : `/api/controles` 1 038 ms
- [bureau, achats, 1440×900] `/analyse?onglet=opportunites` : tableau plus large que son cadre 1299>1142 (Opportunités d’économies)
- [bureau, achats, 1440×900] `/analyse?onglet=fournisseurs` : lent 2051 ms — appel le plus lent : `/api/controles` 1 679 ms
- [bureau, achats, 1440×900] `/analyse?onglet=fournisseurs` : tableau plus large que son cadre 1297>1142 (Classement des fournisseurs)
- [bureau, achats, 1440×900] `/analyse?onglet=fournisseurs` : export lent 1430 ms /api/export/fournisseurs
- [bureau, achats, 1440×900] `/analyse?onglet=revient` : BLOQUANT 3303 ms — appel le plus lent : `/api/prix/historique` 2 842 ms
- [bureau, achats, 1440×900] `/analyse?onglet=revient` : tableau plus large que son cadre 1187>1116 (Coût de revient regroupé)
- [bureau, achats, 1440×900] `/analyse?onglet=revient` : export BLOQUANT 4610 ms /api/export/revient?axe=titrage
- [bureau, achats, 1440×900] `/analyse?onglet=echeancier` : BLOQUANT 3010 ms — appel le plus lent : `/api/controles` 1 359 ms
- [bureau, achats, 1440×900] `/analyse?onglet=echeancier` : tableau sans pagination : 9480 lignes dans le DOM (Échéancier — echeances)
- [bureau, achats, 1440×900] `/analyse?onglet=echeancier` : export BLOQUANT 4245 ms /api/export/echeancier
- [bureau, achats, 1440×900] `/analyse?onglet=controles` : lent 2039 ms — appel le plus lent : `/api/controles/soldes` 1 667 ms
- [bureau, achats, 1440×900] `/analyse?onglet=production` : BLOQUANT 6174 ms — appel le plus lent : `/api/ordres/consommation` 5 176 ms
- [bureau, achats, 1440×900] `/analyse?onglet=production` : tableau sans pagination : 9570 lignes dans le DOM (Rendement par ordre)
- [bureau, alimentation, 1440×900] `/accueil` : BLOQUANT 10451 ms — appel le plus lent : `/api/contexte` 9 769 ms
- [bureau, alimentation, 1440×900] `/stock?onglet=matieres` : tableau plus large que son cadre 1648>1142 (Stock par matière)
- [bureau, alimentation, 1440×900] `/stock?onglet=lots` : BLOQUANT 15757 ms — appel le plus lent : `/api/contexte` 8 871 ms
- [bureau, alimentation, 1440×900] `/stock?onglet=lots` : tableau sans pagination : 20160 lignes dans le DOM (Lots)
- [bureau, alimentation, 1440×900] `/stock?onglet=lots` : tableau plus large que son cadre 1313>1142 (Lots)
- [bureau, alimentation, 1440×900] `/stock?onglet=lots` : export BLOQUANT 3988 ms /api/export/lots
- [bureau, alimentation, 1440×900] `/stock?onglet=mouvements` : recherche lente 1613 ms (« Plastique »)
- [bureau, alimentation, 1440×900] `/stock?onglet=mouvements` : export BLOQUANT 33080 ms /api/export/mouvements
- [bureau, alimentation, 1440×900] `/stock?onglet=ordres` : BLOQUANT 6145 ms — appel le plus lent : `/api/ordres/consommation` 4 418 ms
- [bureau, alimentation, 1440×900] `/stock?onglet=ordres` : tableau sans pagination : 9570 lignes dans le DOM (Ordres de fabrication)
- [bureau, alimentation, 1440×900] `/stock?onglet=ordres` : export BLOQUANT 3384 ms /api/export/ordres?vue=consommation
- [bureau, alimentation, 1440×900] `/stock/matieres/111` : lent 1041 ms — appel le plus lent : `/api/brouillons` 676 ms
- [bureau, alimentation, 1440×900] `/stock/matieres/111` : tableau plus large que son cadre 1648>1142 (Stock par matière)
- [bureau, alimentation, 1440×900] `/lots/291565` : BLOQUANT 6447 ms — appel le plus lent : `/api/lots` 2 611 ms
- [bureau, alimentation, 1440×900] `/lots/291565` : tableau sans pagination : 20160 lignes dans le DOM (Lots)
- [bureau, alimentation, 1440×900] `/lots/291565` : tableau plus large que son cadre 1313>1142 (Lots)
- [bureau, alimentation, 1440×900] `/tracabilite?lot=291565` : BLOQUANT 6252 ms — appel le plus lent : `/api/ordres/consommation` 4 420 ms
- [bureau, alimentation, 1440×900] `/tracabilite?lot=291565` : tableau sans pagination : 9570 lignes dans le DOM (Ordres de fabrication)
- [bureau, alimentation, 1440×900] `/tracabilite?matiere=111` : BLOQUANT 7083 ms — appel le plus lent : `/api/brouillons` 5 098 ms
- [bureau, alimentation, 1440×900] `/tracabilite?matiere=111` : tableau sans pagination : 9570 lignes dans le DOM (Ordres de fabrication)
- [bureau, alimentation, 1440×900] `/tracabilite?matiere=111` : tableau sans pagination : 1440 lignes dans le DOM (Mouvements suivis)
- [bureau, alimentation, 1440×900] `/sorties?onglet=valide` : BLOQUANT 8413 ms — appel le plus lent : `/api/ordres/apercu?statut=valide` 8 022 ms
- [bureau, alimentation, 1440×900] `/sorties?onglet=valide` : recherche lente 9081 ms (« Plastique »)
- [bureau, alimentation, 1440×900] `/sorties?onglet=valide` : export BLOQUANT 8533 ms /api/export/ordres?statut=valide
- [bureau, alimentation, 1440×900] `/ordres/nouveau` : BLOQUANT 12119 ms — appel le plus lent : `/api/ordres/apercu?statut=valide` 11 715 ms
- [bureau, alimentation, 1440×900] `/ordres/nouveau` : recherche lente 7818 ms (« Plastique »)
- [bureau, alimentation, 1440×900] `/ordres/29319` : BLOQUANT 9162 ms — appel le plus lent : `/api/ordres/apercu?statut=valide` 8 724 ms
- [bureau, alimentation, 1440×900] `/ordres/29319` : recherche lente 8759 ms (« Plastique »)
- [bureau, alimentation, 1440×900] `/ordres/29319/retour` : BLOQUANT 8745 ms — appel le plus lent : `/api/ordres/apercu?statut=valide` 8 148 ms
- [bureau, alimentation, 1440×900] `/ordres/29319/retour` : recherche lente 8290 ms (« Plastique »)
- [bureau, alimentation, 1440×900] `/production?onglet=plan` : tableau plus large que son cadre 1372>1142 (Plan de production)
- [bureau, alimentation, 1440×900] `/production?onglet=glissant` : tableau plus large que son cadre 1437>1142 (Plan glissant)
- [bureau, alimentation, 1440×900] `/production?onglet=realise` : tableau plus large que son cadre 1384>1142 (Plan et réalisé)
- [bureau, alimentation, 1440×900] `/production?onglet=besoins` : tableau plus large que son cadre 2178>1142 (Besoins matière)
- [bureau, alimentation, 1440×900] `/production/besoins/111` : tableau plus large que son cadre 2178>1142 (Besoins matière)
- [bureau, alimentation, 1440×900] `/qualites?onglet=qualites` : BLOQUANT 4853 ms — appel le plus lent : `/api/qualites` 4 490 ms
- [bureau, alimentation, 1440×900] `/metiers/1?onglet=fils` : lent 1452 ms — appel le plus lent : `/api/montage/matieres` 654 ms
- [bureau, alimentation, 1440×900] `/metiers/1?onglet=historique` : lent 1333 ms — appel le plus lent : `/api/metiers` 762 ms
- [atelier, alimentation, 375×812] `/atelier` : BLOQUANT 11063 ms — appel le plus lent : `/api/contexte` 10 365 ms
- [atelier, alimentation, 375×812] `/atelier/envoyer` : BLOQUANT 6863 ms — appel le plus lent : `/api/ordres/ouverts` 6 082 ms
- [atelier, alimentation, 375×812] `/atelier/ordres` : BLOQUANT 6343 ms — appel le plus lent : `/api/ordres/ouverts` 5 973 ms
- [atelier, alimentation, 375×812] `/atelier/ordres/29319` : lent 1537 ms — appel le plus lent : `/api/ordres/29319` 1 178 ms
- [atelier, alimentation, 375×812] `/atelier/retour` : BLOQUANT 6066 ms — appel le plus lent : `/api/ordres/ouverts?statut=valide` 5 663 ms
- [atelier, alimentation, 375×812] `/atelier/retour` : recherche lente 6002 ms (« Plastique »)
- [atelier, alimentation, 375×812] `/atelier/chercher` : BLOQUANT 3221 ms — appel le plus lent : `/api/metiers` 2 751 ms
- [atelier, alimentation, 375×812] `/atelier/chercher` : recherche lente 1031 ms (« LOM260920-17 »)
- [atelier, alimentation, 375×812] `/atelier/lots/291565` : BLOQUANT 10654 ms — appel le plus lent : `/api/contexte` 10 295 ms
- [atelier, alimentation, 375×812] `/atelier/deplacer` : lent 2624 ms — appel le plus lent : `/api/lots?non_nuls=true` 2 216 ms
- [atelier, alimentation, 375×812] `/atelier/montage` : lent 1078 ms — appel le plus lent : `/api/metiers` 703 ms
- [atelier, direction, 375×812] `/atelier` : BLOQUANT 11678 ms — appel le plus lent : `/api/contexte` 11 038 ms
- [atelier, direction, 375×812] `/atelier/envoyer` : BLOQUANT 20618 ms — appel le plus lent : `/api/contexte` 11 032 ms
- [atelier, direction, 375×812] `/atelier/ordres` : BLOQUANT 5413 ms — appel le plus lent : `/api/ordres/ouverts` 4 992 ms
- [atelier, direction, 375×812] `/atelier/ordres/29319` : lent 1411 ms — appel le plus lent : `/api/ordres/29319` 1 039 ms
- [atelier, direction, 375×812] `/atelier/retour` : BLOQUANT 5025 ms — appel le plus lent : `/api/ordres/ouverts?statut=valide` 4 624 ms
- [atelier, direction, 375×812] `/atelier/retour` : recherche lente 5921 ms (« Plastique »)
- [atelier, direction, 375×812] `/atelier/chercher` : lent 2489 ms — appel le plus lent : `/api/metiers` 2 013 ms
- [atelier, direction, 375×812] `/atelier/chercher` : recherche lente 1070 ms (« LOM260920-17 »)
- [atelier, direction, 375×812] `/atelier/deplacer` : lent 2878 ms — appel le plus lent : `/api/lots?non_nuls=true` 2 487 ms
- [bureau au téléphone, alimentation, 375×812] `/accueil` : BLOQUANT 10309 ms — appel le plus lent : `/api/contexte` 9 654 ms
- [bureau au téléphone, alimentation, 375×812] `/stock?onglet=matieres` : BLOQUANT 10393 ms — appel le plus lent : `/api/stock` 9 993 ms
- [bureau au téléphone, alimentation, 375×812] `/stock?onglet=matieres` : tableau plus large que son cadre 1552>349 (Stock par matière)
- [bureau au téléphone, alimentation, 375×812] `/stock?onglet=lots` : BLOQUANT 6861 ms — appel le plus lent : `/api/lots` 2 227 ms
- [bureau au téléphone, alimentation, 375×812] `/stock?onglet=lots` : tableau sans pagination : 20160 lignes dans le DOM (Lots)
- [bureau au téléphone, alimentation, 375×812] `/stock?onglet=lots` : tableau plus large que son cadre 1225>349 (Lots)
- [bureau au téléphone, alimentation, 375×812] `/stock?onglet=mouvements` : tableau plus large que son cadre 782>349 (Mouvements de stock)
- [bureau au téléphone, alimentation, 375×812] `/stock?onglet=mouvements` : recherche lente 1773 ms (« Plastique »)
- [bureau au téléphone, alimentation, 375×812] `/stock?onglet=ordres` : BLOQUANT 7115 ms — appel le plus lent : `/api/ordres/consommation` 5 027 ms
- [bureau au téléphone, alimentation, 375×812] `/stock?onglet=ordres` : tableau sans pagination : 9570 lignes dans le DOM (Ordres de fabrication)
- [bureau au téléphone, alimentation, 375×812] `/stock?onglet=ordres` : tableau plus large que son cadre 821>349 (Ordres de fabrication)
- [bureau au téléphone, alimentation, 375×812] `/stock?onglet=a-valider` : tableau plus large que son cadre 629>349 (Brouillons à valider)
- [bureau au téléphone, alimentation, 375×812] `/stock/matieres/111` : lent 1338 ms — appel le plus lent : `/api/brouillons` 945 ms
- [bureau au téléphone, alimentation, 375×812] `/stock/matieres/111` : tableau plus large que son cadre 1552>349 (Stock par matière)
- [bureau au téléphone, alimentation, 375×812] `/stock/matieres/111` : tableau plus large que son cadre 1043>341 (Besoins du plan, mois par mois (kg))
- [bureau au téléphone, alimentation, 375×812] `/lots/291565` : BLOQUANT 7984 ms — appel le plus lent : `/api/brouillons` 2 639 ms
- [bureau au téléphone, alimentation, 375×812] `/lots/291565` : tableau sans pagination : 20160 lignes dans le DOM (Lots)
- [bureau au téléphone, alimentation, 375×812] `/lots/291565` : tableau plus large que son cadre 1225>349 (Lots)
- [bureau au téléphone, alimentation, 375×812] `/lots/291565` : tableau plus large que son cadre 479>341 (Mouvements du lot)
- [bureau au téléphone, alimentation, 375×812] `/tracabilite?lot=291565` : BLOQUANT 8263 ms — appel le plus lent : `/api/ordres/consommation` 6 055 ms
- [bureau au téléphone, alimentation, 375×812] `/tracabilite?lot=291565` : tableau sans pagination : 9570 lignes dans le DOM (Ordres de fabrication)
- [bureau au téléphone, alimentation, 375×812] `/tracabilite?lot=291565` : tableau plus large que son cadre 821>349 (Ordres de fabrication)
- [bureau au téléphone, alimentation, 375×812] `/tracabilite?lot=291565` : tableau plus large que son cadre 737>341 (Mouvements suivis)
- [bureau au téléphone, alimentation, 375×812] `/tracabilite?matiere=111` : BLOQUANT 14159 ms — appel le plus lent : `/api/brouillons` 13 064 ms
- [bureau au téléphone, alimentation, 375×812] `/tracabilite?matiere=111` : tableau sans pagination : 9570 lignes dans le DOM (Ordres de fabrication)
- [bureau au téléphone, alimentation, 375×812] `/tracabilite?matiere=111` : tableau plus large que son cadre 821>349 (Ordres de fabrication)
- [bureau au téléphone, alimentation, 375×812] `/tracabilite?matiere=111` : tableau sans pagination : 1440 lignes dans le DOM (Mouvements suivis)
- [bureau au téléphone, alimentation, 375×812] `/tracabilite?matiere=111` : tableau plus large que son cadre 802>341 (Mouvements suivis)
- [bureau au téléphone, alimentation, 375×812] `/sorties?onglet=valide` : BLOQUANT 20177 ms — appel le plus lent : `/api/ordres/apercu?statut=valide` 19 166 ms
- [bureau au téléphone, alimentation, 375×812] `/sorties?onglet=valide` : tableau plus large que son cadre 823>349 (Ordres de fabrication)
- [bureau au téléphone, alimentation, 375×812] `/sorties?onglet=valide` : recherche lente 9085 ms (« Plastique »)
- [bureau au téléphone, alimentation, 375×812] `/sorties?onglet=brouillon` : tableau plus large que son cadre 854>349 (Ordres de fabrication)
- [bureau au téléphone, alimentation, 375×812] `/sorties?onglet=annule` : tableau plus large que son cadre 737>349 (Ordres de fabrication)
- [bureau au téléphone, alimentation, 375×812] `/ordres/nouveau` : BLOQUANT 15111 ms — appel le plus lent : `/api/ordres/apercu?statut=valide` 14 683 ms
- [bureau au téléphone, alimentation, 375×812] `/ordres/nouveau` : tableau plus large que son cadre 823>349 (Ordres de fabrication)
- [bureau au téléphone, alimentation, 375×812] `/ordres/nouveau` : tableau plus large que son cadre 483>341 (Les matières qui sortent)
- [bureau au téléphone, alimentation, 375×812] `/ordres/nouveau` : recherche lente 10315 ms (« Plastique »)
- [bureau au téléphone, alimentation, 375×812] `/ordres/29319` : BLOQUANT 9217 ms — appel le plus lent : `/api/ordres/apercu?statut=valide` 8 830 ms
- [bureau au téléphone, alimentation, 375×812] `/ordres/29319` : tableau plus large que son cadre 823>349 (Ordres de fabrication)
- [bureau au téléphone, alimentation, 375×812] `/ordres/29319` : recherche lente 9233 ms (« Plastique »)
- [bureau au téléphone, alimentation, 375×812] `/ordres/29319/retour` : BLOQUANT 9390 ms — appel le plus lent : `/api/ordres/apercu?statut=valide` 8 884 ms
- [bureau au téléphone, alimentation, 375×812] `/ordres/29319/retour` : tableau plus large que son cadre 823>349 (Ordres de fabrication)
- [bureau au téléphone, alimentation, 375×812] `/ordres/29319/retour` : tableau plus large que son cadre 419>341 (Ce qui revient, lot par lot)
- [bureau au téléphone, alimentation, 375×812] `/ordres/29319/retour` : recherche lente 8353 ms (« Plastique »)
- [bureau au téléphone, alimentation, 375×812] `/production?onglet=plan` : tableau plus large que son cadre 1244>349 (Plan de production)
- [bureau au téléphone, alimentation, 375×812] `/production?onglet=glissant` : tableau plus large que son cadre 1317>349 (Plan glissant)
- [bureau au téléphone, alimentation, 375×812] `/production?onglet=realise` : tableau plus large que son cadre 1264>349 (Plan et réalisé)
- [bureau au téléphone, alimentation, 375×812] `/production?onglet=besoins` : tableau plus large que son cadre 2034>349 (Besoins matière)
- [bureau au téléphone, alimentation, 375×812] `/production/besoins/111` : tableau plus large que son cadre 2034>349 (Besoins matière)
- [bureau au téléphone, alimentation, 375×812] `/operations?onglet=transfert` : tableau plus large que son cadre 382>349 (Opérations)
- [bureau au téléphone, alimentation, 375×812] `/operations?onglet=retour_machine` : tableau plus large que son cadre 387>349 (Opérations)
- [bureau au téléphone, alimentation, 375×812] `/operations/nouvelle?type=transfert` : tableau plus large que son cadre 382>349 (Opérations)
- [bureau au téléphone, alimentation, 375×812] `/catalogue?onglet=matieres` : tableau plus large que son cadre 908>349 (Matières du catalogue)
- [bureau au téléphone, alimentation, 375×812] `/matieres/111?onglet=classification` : tableau plus large que son cadre 908>349 (Matières du catalogue)
- [bureau au téléphone, alimentation, 375×812] `/matieres/111?onglet=conditionnement` : tableau plus large que son cadre 908>349 (Matières du catalogue)
- [bureau au téléphone, alimentation, 375×812] `/matieres/111?onglet=historique` : tableau plus large que son cadre 908>349 (Matières du catalogue)
- [bureau au téléphone, alimentation, 375×812] `/qualites?onglet=qualites` : tableau plus large que son cadre 966>349 (Qualités)
- [bureau au téléphone, alimentation, 375×812] `/qualites?onglet=nomenclature` : BLOQUANT 4616 ms — appel le plus lent : `/api/qualites` 4 257 ms
- [bureau au téléphone, alimentation, 375×812] `/qualites?onglet=nomenclature` : tableau plus large que son cadre 491>349 (Nomenclature)
- [bureau au téléphone, alimentation, 375×812] `/qualites/1?onglet=recette` : tableau plus large que son cadre 966>349 (Qualités)
- [bureau au téléphone, alimentation, 375×812] `/qualites/1?onglet=recette` : tableau plus large que son cadre 545>341 (Recette)
- [bureau au téléphone, alimentation, 375×812] `/qualites/1?onglet=plan` : tableau plus large que son cadre 966>349 (Qualités)
- [bureau au téléphone, alimentation, 375×812] `/qualites/1?onglet=versions` : tableau plus large que son cadre 966>349 (Qualités)
- [bureau au téléphone, alimentation, 375×812] `/qualites/1?onglet=historique` : tableau plus large que son cadre 966>349 (Qualités)
- [bureau au téléphone, alimentation, 375×812] `/metiers` : tableau plus large que son cadre 943>349 (Métiers à tisser)
- [bureau au téléphone, alimentation, 375×812] `/metiers/1?onglet=fils` : lent 1453 ms — appel le plus lent : `/api/metiers/1` 811 ms
- [bureau au téléphone, alimentation, 375×812] `/metiers/1?onglet=fils` : tableau plus large que son cadre 943>349 (Métiers à tisser)
- [bureau au téléphone, alimentation, 375×812] `/metiers/1?onglet=fils` : tableau plus large que son cadre 588>341 (Fils montés)
- [bureau au téléphone, alimentation, 375×812] `/metiers/1?onglet=reglages` : lent 1371 ms — appel le plus lent : `/api/metiers/1` 747 ms
- [bureau au téléphone, alimentation, 375×812] `/metiers/1?onglet=reglages` : tableau plus large que son cadre 943>349 (Métiers à tisser)
- [bureau au téléphone, alimentation, 375×812] `/metiers/1?onglet=historique` : lent 1333 ms — appel le plus lent : `/api/montage/matieres` 673 ms
- [bureau au téléphone, alimentation, 375×812] `/metiers/1?onglet=historique` : tableau plus large que son cadre 943>349 (Métiers à tisser)
- [bureau au téléphone, alimentation, 375×812] `/metiers/1?onglet=historique` : tableau plus large que son cadre 712>341 (Montages)
- [bureau au téléphone, alimentation, 375×812] `/aide?onglet=calculs` : tableau plus large que son cadre 384>317 (2 col.)
- [bureau au téléphone, alimentation, 375×812] `/aide?onglet=analyse` : tableau plus large que son cadre 322>317 (0 col.)
- [bureau au téléphone, alimentation, 375×812] `/aide?onglet=ecrans` : tableau plus large que son cadre 344>317 (3 col.)

### annee-1

- [bureau, direction, 1440×900] `/cockpit?onglet=faire` : lent 1212 ms — appel le plus lent : `/api/contexte` 448 ms
- [bureau, direction, 1440×900] `/stock?onglet=matieres` : tableau plus large que son cadre 2024>1142 (Stock par matière)
- [bureau, direction, 1440×900] `/stock?onglet=lots` : tableau plus large que son cadre 1290>1142 (Lots)
- [bureau, direction, 1440×900] `/stock?onglet=mouvements` : export lent 2216 ms /api/export/mouvements?avec_valeur=true
- [bureau, direction, 1440×900] `/stock/matieres/124` : tableau plus large que son cadre 2024>1142 (Stock par matière)
- [bureau, direction, 1440×900] `/lots/353` : tableau plus large que son cadre 1290>1142 (Lots)
- [bureau, direction, 1440×900] `/ordres/nouveau` : lent 1455 ms — appel le plus lent : `/api/ordres/apercu?statut=valide` 1 092 ms
- [bureau, direction, 1440×900] `/ordres/1087` : lent 1079 ms — appel le plus lent : `/api/ordres/apercu?statut=valide` 706 ms
- [bureau, direction, 1440×900] `/ordres/1087/retour` : lent 1042 ms — appel le plus lent : `/api/ordres/apercu?statut=valide` 688 ms
- [bureau, direction, 1440×900] `/production?onglet=plan` : tableau plus large que son cadre 1574>1142 (Plan de production)
- [bureau, direction, 1440×900] `/production?onglet=glissant` : tableau plus large que son cadre 1437>1142 (Plan glissant)
- [bureau, direction, 1440×900] `/production?onglet=realise` : tableau plus large que son cadre 1384>1142 (Plan et réalisé)
- [bureau, direction, 1440×900] `/production?onglet=besoins` : tableau plus large que son cadre 2296>1142 (Besoins matière)
- [bureau, direction, 1440×900] `/production/besoins/124` : tableau plus large que son cadre 2296>1142 (Besoins matière)
- [bureau, direction, 1440×900] `/importations?onglet=clos` : tableau plus large que son cadre 1325>1142 (Dossiers clos)
- [bureau, direction, 1440×900] `/dossiers/58?onglet=familles` : tableau plus large que son cadre 1325>1142 (Dossiers clos)
- [bureau, direction, 1440×900] `/dossiers/58?onglet=marchandises` : tableau plus large que son cadre 1325>1142 (Dossiers clos)
- [bureau, direction, 1440×900] `/dossiers/58?onglet=marchandises` : tableau plus large que son cadre 1358>1206 (Marchandises du dossier)
- [bureau, direction, 1440×900] `/dossiers/58?onglet=frais` : tableau plus large que son cadre 1325>1142 (Dossiers clos)
- [bureau, direction, 1440×900] `/dossiers/58?onglet=echeancier` : tableau plus large que son cadre 1325>1142 (Dossiers clos)
- [bureau, direction, 1440×900] `/dossiers/58?onglet=pieces` : tableau plus large que son cadre 1325>1142 (Dossiers clos)
- [bureau, direction, 1440×900] `/dossiers/58?onglet=facture` : tableau plus large que son cadre 1325>1142 (Dossiers clos)
- [bureau, direction, 1440×900] `/dossiers/58?onglet=historique` : tableau plus large que son cadre 1325>1142 (Dossiers clos)
- [bureau, direction, 1440×900] `/inventaire?onglet=passes` : tableau plus large que son cadre 1303>1142 (Inventaires clos)
- [bureau, direction, 1440×900] `/inventaires/26?onglet=lots` : tableau plus large que son cadre 1303>1142 (Inventaires clos)
- [bureau, direction, 1440×900] `/inventaires/26?onglet=lots` : tableau plus large que son cadre 1451>1206 (Lots à compter)
- [bureau, direction, 1440×900] `/inventaires/26?onglet=pieces` : tableau plus large que son cadre 1303>1142 (Inventaires clos)
- [bureau, direction, 1440×900] `/inventaires/26?onglet=historique` : tableau plus large que son cadre 1303>1142 (Inventaires clos)
- [bureau, direction, 1440×900] `/analyse?onglet=valorisation` : tableau plus large que son cadre 1268>1142 (Valorisation par matière)
- [bureau, direction, 1440×900] `/analyse?onglet=matrice` : tableau plus large que son cadre 1504>1142 (Matrice des prix)
- [bureau, direction, 1440×900] `/analyse?onglet=opportunites` : tableau plus large que son cadre 1299>1142 (Opportunités d’économies)
- [bureau, direction, 1440×900] `/analyse?onglet=fournisseurs` : tableau plus large que son cadre 1279>1142 (Classement des fournisseurs)
- [bureau, direction, 1440×900] `/analyse?onglet=revient` : tableau plus large que son cadre 1127>1116 (Coût de revient regroupé)
- [bureau, direction, 1440×900] `/administration?onglet=journal` : tableau plus large que son cadre 2126>1142 (Journal des actions)
- [bureau, direction, 1440×900] `/administration?onglet=donnees` : tableau plus large que son cadre 3056>1142 (Table matiere)
- [bureau, achats, 1440×900] `/accueil` : lent 1082 ms — appel le plus lent : `/api/cockpit` 383 ms
- [bureau, achats, 1440×900] `/stock?onglet=matieres` : tableau plus large que son cadre 2024>1142 (Stock par matière)
- [bureau, achats, 1440×900] `/stock?onglet=lots` : tableau plus large que son cadre 1290>1142 (Lots)
- [bureau, achats, 1440×900] `/stock?onglet=mouvements` : export lent 2151 ms /api/export/mouvements?avec_valeur=true
- [bureau, achats, 1440×900] `/stock/matieres/124` : tableau plus large que son cadre 2024>1142 (Stock par matière)
- [bureau, achats, 1440×900] `/lots/353` : tableau plus large que son cadre 1290>1142 (Lots)
- [bureau, achats, 1440×900] `/ordres/1087` : lent 1045 ms — appel le plus lent : `/api/ordres/apercu?statut=valide` 662 ms
- [bureau, achats, 1440×900] `/production?onglet=plan` : tableau plus large que son cadre 1329>1142 (Plan de production)
- [bureau, achats, 1440×900] `/production?onglet=glissant` : tableau plus large que son cadre 1437>1142 (Plan glissant)
- [bureau, achats, 1440×900] `/production?onglet=realise` : tableau plus large que son cadre 1384>1142 (Plan et réalisé)
- [bureau, achats, 1440×900] `/production?onglet=besoins` : tableau plus large que son cadre 2296>1142 (Besoins matière)
- [bureau, achats, 1440×900] `/production/besoins/124` : tableau plus large que son cadre 2296>1142 (Besoins matière)
- [bureau, achats, 1440×900] `/importations?onglet=clos` : tableau plus large que son cadre 1325>1142 (Dossiers clos)
- [bureau, achats, 1440×900] `/dossiers/58?onglet=familles` : tableau plus large que son cadre 1325>1142 (Dossiers clos)
- [bureau, achats, 1440×900] `/dossiers/58?onglet=marchandises` : tableau plus large que son cadre 1325>1142 (Dossiers clos)
- [bureau, achats, 1440×900] `/dossiers/58?onglet=marchandises` : tableau plus large que son cadre 1358>1206 (Marchandises du dossier)
- [bureau, achats, 1440×900] `/dossiers/58?onglet=frais` : tableau plus large que son cadre 1325>1142 (Dossiers clos)
- [bureau, achats, 1440×900] `/dossiers/58?onglet=echeancier` : tableau plus large que son cadre 1325>1142 (Dossiers clos)
- [bureau, achats, 1440×900] `/dossiers/58?onglet=pieces` : tableau plus large que son cadre 1325>1142 (Dossiers clos)
- [bureau, achats, 1440×900] `/dossiers/58?onglet=facture` : tableau plus large que son cadre 1325>1142 (Dossiers clos)
- [bureau, achats, 1440×900] `/dossiers/58?onglet=historique` : tableau plus large que son cadre 1325>1142 (Dossiers clos)
- [bureau, achats, 1440×900] `/inventaire?onglet=passes` : tableau plus large que son cadre 1303>1142 (Inventaires clos)
- [bureau, achats, 1440×900] `/inventaires/26?onglet=lots` : tableau plus large que son cadre 1303>1142 (Inventaires clos)
- [bureau, achats, 1440×900] `/inventaires/26?onglet=lots` : tableau plus large que son cadre 1451>1206 (Lots à compter)
- [bureau, achats, 1440×900] `/inventaires/26?onglet=pieces` : tableau plus large que son cadre 1303>1142 (Inventaires clos)
- [bureau, achats, 1440×900] `/inventaires/26?onglet=historique` : tableau plus large que son cadre 1303>1142 (Inventaires clos)
- [bureau, achats, 1440×900] `/analyse?onglet=valorisation` : tableau plus large que son cadre 1268>1142 (Valorisation par matière)
- [bureau, achats, 1440×900] `/analyse?onglet=matrice` : tableau plus large que son cadre 1504>1142 (Matrice des prix)
- [bureau, achats, 1440×900] `/analyse?onglet=opportunites` : tableau plus large que son cadre 1299>1142 (Opportunités d’économies)
- [bureau, achats, 1440×900] `/analyse?onglet=fournisseurs` : tableau plus large que son cadre 1279>1142 (Classement des fournisseurs)
- [bureau, achats, 1440×900] `/analyse?onglet=revient` : tableau plus large que son cadre 1127>1116 (Coût de revient regroupé)
- [bureau, alimentation, 1440×900] `/stock?onglet=matieres` : tableau plus large que son cadre 1701>1142 (Stock par matière)
- [bureau, alimentation, 1440×900] `/stock?onglet=lots` : tableau plus large que son cadre 1290>1142 (Lots)
- [bureau, alimentation, 1440×900] `/stock?onglet=mouvements` : export lent 1592 ms /api/export/mouvements
- [bureau, alimentation, 1440×900] `/stock/matieres/124` : tableau plus large que son cadre 1701>1142 (Stock par matière)
- [bureau, alimentation, 1440×900] `/lots/353` : tableau plus large que son cadre 1290>1142 (Lots)
- [bureau, alimentation, 1440×900] `/sorties?onglet=valide` : lent 1041 ms — appel le plus lent : `/api/ordres/apercu?statut=valide` 676 ms
- [bureau, alimentation, 1440×900] `/ordres/nouveau` : lent 1532 ms — appel le plus lent : `/api/ordres/ouverts` 1 171 ms
- [bureau, alimentation, 1440×900] `/ordres/1087` : lent 1121 ms — appel le plus lent : `/api/ordres/apercu?statut=valide` 756 ms
- [bureau, alimentation, 1440×900] `/ordres/1087/retour` : lent 1061 ms — appel le plus lent : `/api/ordres/apercu?statut=valide` 716 ms
- [bureau, alimentation, 1440×900] `/production?onglet=plan` : tableau plus large que son cadre 1329>1142 (Plan de production)
- [bureau, alimentation, 1440×900] `/production?onglet=glissant` : tableau plus large que son cadre 1437>1142 (Plan glissant)
- [bureau, alimentation, 1440×900] `/production?onglet=realise` : tableau plus large que son cadre 1384>1142 (Plan et réalisé)
- [bureau, alimentation, 1440×900] `/production?onglet=besoins` : tableau plus large que son cadre 2149>1142 (Besoins matière)
- [bureau, alimentation, 1440×900] `/production/besoins/124` : tableau plus large que son cadre 2149>1142 (Besoins matière)
- [atelier, alimentation, 375×812] `/atelier/envoyer` : lent 1299 ms — appel le plus lent : `/api/ordres/ouverts` 801 ms
- [atelier, direction, 375×812] `/atelier/envoyer` : lent 1167 ms — appel le plus lent : `/api/ordres/ouverts` 789 ms
- [bureau au téléphone, alimentation, 375×812] `/stock?onglet=matieres` : tableau plus large que son cadre 1605>349 (Stock par matière)
- [bureau au téléphone, alimentation, 375×812] `/stock?onglet=lots` : tableau plus large que son cadre 1202>349 (Lots)
- [bureau au téléphone, alimentation, 375×812] `/stock?onglet=mouvements` : tableau plus large que son cadre 761>349 (Mouvements de stock)
- [bureau au téléphone, alimentation, 375×812] `/stock?onglet=ordres` : tableau plus large que son cadre 856>349 (Ordres de fabrication)
- [bureau au téléphone, alimentation, 375×812] `/stock?onglet=a-valider` : tableau plus large que son cadre 622>349 (Brouillons à valider)
- [bureau au téléphone, alimentation, 375×812] `/stock/matieres/124` : tableau plus large que son cadre 1605>349 (Stock par matière)
- [bureau au téléphone, alimentation, 375×812] `/stock/matieres/124` : tableau plus large que son cadre 1043>341 (Besoins du plan, mois par mois (kg))
- [bureau au téléphone, alimentation, 375×812] `/lots/353` : tableau plus large que son cadre 1202>349 (Lots)
- [bureau au téléphone, alimentation, 375×812] `/lots/353` : tableau plus large que son cadre 472>341 (Mouvements du lot)
- [bureau au téléphone, alimentation, 375×812] `/tracabilite?lot=353` : tableau plus large que son cadre 856>349 (Ordres de fabrication)
- [bureau au téléphone, alimentation, 375×812] `/tracabilite?lot=353` : tableau plus large que son cadre 720>341 (Mouvements suivis)
- [bureau au téléphone, alimentation, 375×812] `/tracabilite?matiere=124` : tableau plus large que son cadre 856>349 (Ordres de fabrication)
- [bureau au téléphone, alimentation, 375×812] `/tracabilite?matiere=124` : tableau plus large que son cadre 838>341 (Mouvements suivis)
- [bureau au téléphone, alimentation, 375×812] `/sorties?onglet=valide` : lent 1039 ms — appel le plus lent : `/api/ordres/apercu?statut=valide` 672 ms
- [bureau au téléphone, alimentation, 375×812] `/sorties?onglet=valide` : tableau plus large que son cadre 851>349 (Ordres de fabrication)
- [bureau au téléphone, alimentation, 375×812] `/sorties?onglet=brouillon` : tableau plus large que son cadre 841>349 (Ordres de fabrication)
- [bureau au téléphone, alimentation, 375×812] `/sorties?onglet=annule` : tableau plus large que son cadre 821>349 (Ordres de fabrication)
- [bureau au téléphone, alimentation, 375×812] `/ordres/nouveau` : lent 1106 ms — appel le plus lent : `/api/ordres/ouverts` 748 ms
- [bureau au téléphone, alimentation, 375×812] `/ordres/nouveau` : tableau plus large que son cadre 851>349 (Ordres de fabrication)
- [bureau au téléphone, alimentation, 375×812] `/ordres/nouveau` : tableau plus large que son cadre 483>341 (Les matières qui sortent)
- [bureau au téléphone, alimentation, 375×812] `/ordres/1087` : tableau plus large que son cadre 851>349 (Ordres de fabrication)
- [bureau au téléphone, alimentation, 375×812] `/ordres/1087/retour` : lent 1028 ms — appel le plus lent : `/api/ordres/apercu?statut=valide` 657 ms
- [bureau au téléphone, alimentation, 375×812] `/ordres/1087/retour` : tableau plus large que son cadre 851>349 (Ordres de fabrication)
- [bureau au téléphone, alimentation, 375×812] `/ordres/1087/retour` : tableau plus large que son cadre 385>341 (Ce qui revient, lot par lot)
- [bureau au téléphone, alimentation, 375×812] `/production?onglet=plan` : tableau plus large que son cadre 1201>349 (Plan de production)
- [bureau au téléphone, alimentation, 375×812] `/production?onglet=glissant` : tableau plus large que son cadre 1317>349 (Plan glissant)
- [bureau au téléphone, alimentation, 375×812] `/production?onglet=realise` : tableau plus large que son cadre 1264>349 (Plan et réalisé)
- [bureau au téléphone, alimentation, 375×812] `/production?onglet=besoins` : tableau plus large que son cadre 2005>349 (Besoins matière)
- [bureau au téléphone, alimentation, 375×812] `/production/besoins/124` : tableau plus large que son cadre 2005>349 (Besoins matière)
- [bureau au téléphone, alimentation, 375×812] `/production/besoins/124` : tableau plus large que son cadre 1049>341 (D’où vient le besoin)
- [bureau au téléphone, alimentation, 375×812] `/operations?onglet=transfert` : tableau plus large que son cadre 638>349 (Opérations)
- [bureau au téléphone, alimentation, 375×812] `/operations?onglet=retour_machine` : tableau plus large que son cadre 630>349 (Opérations)
- [bureau au téléphone, alimentation, 375×812] `/operations/nouvelle?type=transfert` : tableau plus large que son cadre 638>349 (Opérations)
- [bureau au téléphone, alimentation, 375×812] `/operations/337` : tableau plus large que son cadre 638>349 (Opérations)
- [bureau au téléphone, alimentation, 375×812] `/operations/337` : tableau plus large que son cadre 378>341 (Lignes de l’opération)
- [bureau au téléphone, alimentation, 375×812] `/catalogue?onglet=matieres` : tableau plus large que son cadre 934>349 (Matières du catalogue)
- [bureau au téléphone, alimentation, 375×812] `/matieres/124?onglet=classification` : tableau plus large que son cadre 934>349 (Matières du catalogue)
- [bureau au téléphone, alimentation, 375×812] `/matieres/124?onglet=conditionnement` : tableau plus large que son cadre 934>349 (Matières du catalogue)
- [bureau au téléphone, alimentation, 375×812] `/matieres/124?onglet=historique` : tableau plus large que son cadre 934>349 (Matières du catalogue)
- [bureau au téléphone, alimentation, 375×812] `/qualites?onglet=qualites` : tableau plus large que son cadre 966>349 (Qualités)
- [bureau au téléphone, alimentation, 375×812] `/qualites?onglet=nomenclature` : tableau plus large que son cadre 491>349 (Nomenclature)
- [bureau au téléphone, alimentation, 375×812] `/qualites/1?onglet=recette` : tableau plus large que son cadre 966>349 (Qualités)
- [bureau au téléphone, alimentation, 375×812] `/qualites/1?onglet=recette` : tableau plus large que son cadre 545>341 (Recette)
- [bureau au téléphone, alimentation, 375×812] `/qualites/1?onglet=plan` : tableau plus large que son cadre 966>349 (Qualités)
- [bureau au téléphone, alimentation, 375×812] `/qualites/1?onglet=versions` : tableau plus large que son cadre 966>349 (Qualités)
- [bureau au téléphone, alimentation, 375×812] `/qualites/1?onglet=historique` : tableau plus large que son cadre 966>349 (Qualités)
- [bureau au téléphone, alimentation, 375×812] `/metiers` : tableau plus large que son cadre 895>349 (Métiers à tisser)
- [bureau au téléphone, alimentation, 375×812] `/metiers/2?onglet=fils` : tableau plus large que son cadre 895>349 (Métiers à tisser)
- [bureau au téléphone, alimentation, 375×812] `/metiers/2?onglet=fils` : tableau plus large que son cadre 662>341 (Fils montés)
- [bureau au téléphone, alimentation, 375×812] `/metiers/2?onglet=reglages` : tableau plus large que son cadre 895>349 (Métiers à tisser)
- [bureau au téléphone, alimentation, 375×812] `/metiers/2?onglet=historique` : tableau plus large que son cadre 895>349 (Métiers à tisser)
- [bureau au téléphone, alimentation, 375×812] `/metiers/2?onglet=historique` : tableau plus large que son cadre 818>341 (Montages)
- [bureau au téléphone, alimentation, 375×812] `/aide?onglet=calculs` : tableau plus large que son cadre 384>317 (2 col.)
- [bureau au téléphone, alimentation, 375×812] `/aide?onglet=analyse` : tableau plus large que son cadre 322>317 (0 col.)
- [bureau au téléphone, alimentation, 375×812] `/aide?onglet=ecrans` : tableau plus large que son cadre 344>317 (3 col.)

### annee-2

- [bureau, direction, 1440×900] `/cockpit?onglet=faire` : lent 1840 ms — appel le plus lent : `/api/contexte` 806 ms
- [bureau, direction, 1440×900] `/stock?onglet=matieres` : tableau plus large que son cadre 2034>1142 (Stock par matière)
- [bureau, direction, 1440×900] `/stock?onglet=lots` : tableau plus large que son cadre 1432>1142 (Lots)
- [bureau, direction, 1440×900] `/stock?onglet=mouvements` : export BLOQUANT 4097 ms /api/export/mouvements?avec_valeur=true
- [bureau, direction, 1440×900] `/stock?onglet=ordres` : lent 1059 ms — appel le plus lent : `/api/ordres/consommation` 436 ms
- [bureau, direction, 1440×900] `/stock?onglet=ordres` : tableau sans pagination : 1871 lignes dans le DOM (Ordres de fabrication)
- [bureau, direction, 1440×900] `/stock/matieres/124` : tableau plus large que son cadre 2034>1142 (Stock par matière)
- [bureau, direction, 1440×900] `/lots/704` : tableau plus large que son cadre 1432>1142 (Lots)
- [bureau, direction, 1440×900] `/tracabilite?lot=704` : lent 1060 ms — appel le plus lent : `/api/ordres/consommation` 460 ms
- [bureau, direction, 1440×900] `/tracabilite?lot=704` : tableau sans pagination : 1871 lignes dans le DOM (Ordres de fabrication)
- [bureau, direction, 1440×900] `/tracabilite?matiere=124` : lent 1125 ms — appel le plus lent : `/api/ordres/consommation` 484 ms
- [bureau, direction, 1440×900] `/tracabilite?matiere=124` : tableau sans pagination : 1871 lignes dans le DOM (Ordres de fabrication)
- [bureau, direction, 1440×900] `/tracabilite?matiere=124` : tableau sans pagination : 1424 lignes dans le DOM (Mouvements suivis)
- [bureau, direction, 1440×900] `/sorties?onglet=valide` : lent 1236 ms — appel le plus lent : `/api/ordres/apercu?statut=valide` 855 ms
- [bureau, direction, 1440×900] `/sorties?onglet=valide` : recherche lente 1004 ms (« Plastique-140 »)
- [bureau, direction, 1440×900] `/ordres/nouveau` : lent 1535 ms — appel le plus lent : `/api/ordres/ouverts` 1 157 ms
- [bureau, direction, 1440×900] `/ordres/2181` : lent 1127 ms — appel le plus lent : `/api/ordres/apercu?statut=valide` 751 ms
- [bureau, direction, 1440×900] `/ordres/2181/retour` : lent 1311 ms — appel le plus lent : `/api/ordres/apercu?statut=valide` 955 ms
- [bureau, direction, 1440×900] `/production?onglet=plan` : tableau plus large que son cadre 1574>1142 (Plan de production)
- [bureau, direction, 1440×900] `/production?onglet=glissant` : tableau plus large que son cadre 1437>1142 (Plan glissant)
- [bureau, direction, 1440×900] `/production?onglet=realise` : tableau plus large que son cadre 1384>1142 (Plan et réalisé)
- [bureau, direction, 1440×900] `/production?onglet=besoins` : tableau plus large que son cadre 2326>1142 (Besoins matière)
- [bureau, direction, 1440×900] `/production/besoins/124` : tableau plus large que son cadre 2326>1142 (Besoins matière)
- [bureau, direction, 1440×900] `/importations?onglet=ouverts` : tableau plus large que son cadre 1162>1142 (Dossiers ouverts)
- [bureau, direction, 1440×900] `/importations?onglet=clos` : tableau plus large que son cadre 1325>1142 (Dossiers clos)
- [bureau, direction, 1440×900] `/dossiers/nouveau?onglet=facture` : tableau plus large que son cadre 1162>1142 (Dossiers ouverts)
- [bureau, direction, 1440×900] `/dossiers/nouveau?onglet=main` : tableau plus large que son cadre 1162>1142 (Dossiers ouverts)
- [bureau, direction, 1440×900] `/dossiers/160?onglet=familles` : tableau plus large que son cadre 1325>1142 (Dossiers clos)
- [bureau, direction, 1440×900] `/dossiers/160?onglet=marchandises` : tableau plus large que son cadre 1325>1142 (Dossiers clos)
- [bureau, direction, 1440×900] `/dossiers/160?onglet=marchandises` : tableau plus large que son cadre 1358>1206 (Marchandises du dossier)
- [bureau, direction, 1440×900] `/dossiers/160?onglet=frais` : tableau plus large que son cadre 1325>1142 (Dossiers clos)
- [bureau, direction, 1440×900] `/dossiers/160?onglet=echeancier` : tableau plus large que son cadre 1325>1142 (Dossiers clos)
- [bureau, direction, 1440×900] `/dossiers/160?onglet=pieces` : tableau plus large que son cadre 1325>1142 (Dossiers clos)
- [bureau, direction, 1440×900] `/dossiers/160?onglet=facture` : tableau plus large que son cadre 1325>1142 (Dossiers clos)
- [bureau, direction, 1440×900] `/dossiers/160?onglet=historique` : tableau plus large que son cadre 1325>1142 (Dossiers clos)
- [bureau, direction, 1440×900] `/inventaire?onglet=passes` : tableau plus large que son cadre 1303>1142 (Inventaires clos)
- [bureau, direction, 1440×900] `/inventaires/57?onglet=lots` : tableau plus large que son cadre 1303>1142 (Inventaires clos)
- [bureau, direction, 1440×900] `/inventaires/57?onglet=pieces` : tableau plus large que son cadre 1303>1142 (Inventaires clos)
- [bureau, direction, 1440×900] `/inventaires/57?onglet=historique` : tableau plus large que son cadre 1303>1142 (Inventaires clos)
- [bureau, direction, 1440×900] `/analyse?onglet=valorisation` : tableau plus large que son cadre 1275>1142 (Valorisation par matière)
- [bureau, direction, 1440×900] `/analyse?onglet=matrice` : tableau plus large que son cadre 2522>1142 (Matrice des prix)
- [bureau, direction, 1440×900] `/analyse?onglet=opportunites` : tableau plus large que son cadre 1299>1142 (Opportunités d’économies)
- [bureau, direction, 1440×900] `/analyse?onglet=fournisseurs` : tableau plus large que son cadre 1272>1142 (Classement des fournisseurs)
- [bureau, direction, 1440×900] `/analyse?onglet=production` : tableau sans pagination : 1871 lignes dans le DOM (Rendement par ordre)
- [bureau, direction, 1440×900] `/administration?onglet=journal` : tableau plus large que son cadre 2133>1142 (Journal des actions)
- [bureau, direction, 1440×900] `/administration?onglet=journal` : export lent 1028 ms /api/export/journal
- [bureau, direction, 1440×900] `/administration?onglet=donnees` : tableau plus large que son cadre 3056>1142 (Table matiere)
- [bureau, achats, 1440×900] `/accueil` : lent 1910 ms — appel le plus lent : `/api/cockpit` 859 ms
- [bureau, achats, 1440×900] `/stock?onglet=matieres` : tableau plus large que son cadre 2034>1142 (Stock par matière)
- [bureau, achats, 1440×900] `/stock?onglet=lots` : tableau plus large que son cadre 1432>1142 (Lots)
- [bureau, achats, 1440×900] `/stock?onglet=mouvements` : export BLOQUANT 4186 ms /api/export/mouvements?avec_valeur=true
- [bureau, achats, 1440×900] `/stock?onglet=ordres` : lent 1088 ms — appel le plus lent : `/api/ordres/consommation` 376 ms
- [bureau, achats, 1440×900] `/stock?onglet=ordres` : tableau sans pagination : 1871 lignes dans le DOM (Ordres de fabrication)
- [bureau, achats, 1440×900] `/stock/matieres/124` : tableau plus large que son cadre 2034>1142 (Stock par matière)
- [bureau, achats, 1440×900] `/lots/704` : tableau plus large que son cadre 1432>1142 (Lots)
- [bureau, achats, 1440×900] `/tracabilite?lot=704` : lent 1112 ms — appel le plus lent : `/api/ordres/consommation` 493 ms
- [bureau, achats, 1440×900] `/tracabilite?lot=704` : tableau sans pagination : 1871 lignes dans le DOM (Ordres de fabrication)
- [bureau, achats, 1440×900] `/tracabilite?matiere=124` : lent 1075 ms — appel le plus lent : `/api/ordres/consommation` 423 ms
- [bureau, achats, 1440×900] `/tracabilite?matiere=124` : tableau sans pagination : 1871 lignes dans le DOM (Ordres de fabrication)
- [bureau, achats, 1440×900] `/tracabilite?matiere=124` : tableau sans pagination : 1424 lignes dans le DOM (Mouvements suivis)
- [bureau, achats, 1440×900] `/sorties?onglet=valide` : lent 1383 ms — appel le plus lent : `/api/ordres/apercu?statut=valide` 1 021 ms
- [bureau, achats, 1440×900] `/ordres/2181` : lent 1616 ms — appel le plus lent : `/api/ordres/apercu?statut=valide` 1 228 ms
- [bureau, achats, 1440×900] `/production?onglet=plan` : tableau plus large que son cadre 1336>1142 (Plan de production)
- [bureau, achats, 1440×900] `/production?onglet=glissant` : tableau plus large que son cadre 1437>1142 (Plan glissant)
- [bureau, achats, 1440×900] `/production?onglet=realise` : tableau plus large que son cadre 1384>1142 (Plan et réalisé)
- [bureau, achats, 1440×900] `/production?onglet=besoins` : tableau plus large que son cadre 2326>1142 (Besoins matière)
- [bureau, achats, 1440×900] `/production/besoins/124` : tableau plus large que son cadre 2326>1142 (Besoins matière)
- [bureau, achats, 1440×900] `/importations?onglet=ouverts` : tableau plus large que son cadre 1162>1142 (Dossiers ouverts)
- [bureau, achats, 1440×900] `/importations?onglet=clos` : tableau plus large que son cadre 1325>1142 (Dossiers clos)
- [bureau, achats, 1440×900] `/dossiers/nouveau?onglet=facture` : tableau plus large que son cadre 1162>1142 (Dossiers ouverts)
- [bureau, achats, 1440×900] `/dossiers/nouveau?onglet=main` : tableau plus large que son cadre 1162>1142 (Dossiers ouverts)
- [bureau, achats, 1440×900] `/dossiers/160?onglet=familles` : tableau plus large que son cadre 1325>1142 (Dossiers clos)
- [bureau, achats, 1440×900] `/dossiers/160?onglet=marchandises` : tableau plus large que son cadre 1325>1142 (Dossiers clos)
- [bureau, achats, 1440×900] `/dossiers/160?onglet=marchandises` : tableau plus large que son cadre 1358>1206 (Marchandises du dossier)
- [bureau, achats, 1440×900] `/dossiers/160?onglet=frais` : tableau plus large que son cadre 1325>1142 (Dossiers clos)
- [bureau, achats, 1440×900] `/dossiers/160?onglet=echeancier` : tableau plus large que son cadre 1325>1142 (Dossiers clos)
- [bureau, achats, 1440×900] `/dossiers/160?onglet=pieces` : tableau plus large que son cadre 1325>1142 (Dossiers clos)
- [bureau, achats, 1440×900] `/dossiers/160?onglet=facture` : tableau plus large que son cadre 1325>1142 (Dossiers clos)
- [bureau, achats, 1440×900] `/dossiers/160?onglet=historique` : tableau plus large que son cadre 1325>1142 (Dossiers clos)
- [bureau, achats, 1440×900] `/inventaire?onglet=passes` : tableau plus large que son cadre 1303>1142 (Inventaires clos)
- [bureau, achats, 1440×900] `/inventaires/57?onglet=lots` : tableau plus large que son cadre 1303>1142 (Inventaires clos)
- [bureau, achats, 1440×900] `/inventaires/57?onglet=pieces` : tableau plus large que son cadre 1303>1142 (Inventaires clos)
- [bureau, achats, 1440×900] `/inventaires/57?onglet=historique` : tableau plus large que son cadre 1303>1142 (Inventaires clos)
- [bureau, achats, 1440×900] `/analyse?onglet=valorisation` : tableau plus large que son cadre 1275>1142 (Valorisation par matière)
- [bureau, achats, 1440×900] `/analyse?onglet=matrice` : tableau plus large que son cadre 2522>1142 (Matrice des prix)
- [bureau, achats, 1440×900] `/analyse?onglet=opportunites` : tableau plus large que son cadre 1299>1142 (Opportunités d’économies)
- [bureau, achats, 1440×900] `/analyse?onglet=fournisseurs` : tableau plus large que son cadre 1272>1142 (Classement des fournisseurs)
- [bureau, achats, 1440×900] `/analyse?onglet=production` : tableau sans pagination : 1871 lignes dans le DOM (Rendement par ordre)
- [bureau, alimentation, 1440×900] `/accueil` : lent 1057 ms — appel le plus lent : `/api/contexte` 720 ms
- [bureau, alimentation, 1440×900] `/stock?onglet=matieres` : tableau plus large que son cadre 1712>1142 (Stock par matière)
- [bureau, alimentation, 1440×900] `/stock?onglet=lots` : tableau plus large que son cadre 1432>1142 (Lots)
- [bureau, alimentation, 1440×900] `/stock?onglet=mouvements` : export BLOQUANT 3060 ms /api/export/mouvements
- [bureau, alimentation, 1440×900] `/stock?onglet=ordres` : lent 1203 ms — appel le plus lent : `/api/ordres/consommation` 581 ms
- [bureau, alimentation, 1440×900] `/stock?onglet=ordres` : tableau sans pagination : 1871 lignes dans le DOM (Ordres de fabrication)
- [bureau, alimentation, 1440×900] `/stock/matieres/124` : lent 1024 ms — appel le plus lent : `/api/stock/124` 675 ms
- [bureau, alimentation, 1440×900] `/stock/matieres/124` : tableau plus large que son cadre 1712>1142 (Stock par matière)
- [bureau, alimentation, 1440×900] `/lots/704` : tableau plus large que son cadre 1432>1142 (Lots)
- [bureau, alimentation, 1440×900] `/tracabilite?lot=704` : lent 1202 ms — appel le plus lent : `/api/ordres/consommation` 578 ms
- [bureau, alimentation, 1440×900] `/tracabilite?lot=704` : tableau sans pagination : 1871 lignes dans le DOM (Ordres de fabrication)
- [bureau, alimentation, 1440×900] `/tracabilite?matiere=124` : lent 1221 ms — appel le plus lent : `/api/ordres/consommation` 588 ms
- [bureau, alimentation, 1440×900] `/tracabilite?matiere=124` : tableau sans pagination : 1871 lignes dans le DOM (Ordres de fabrication)
- [bureau, alimentation, 1440×900] `/tracabilite?matiere=124` : tableau sans pagination : 1424 lignes dans le DOM (Mouvements suivis)
- [bureau, alimentation, 1440×900] `/ordres/nouveau` : lent 2153 ms — appel le plus lent : `/api/ordres/apercu?statut=valide` 1 784 ms
- [bureau, alimentation, 1440×900] `/ordres/2181` : lent 1445 ms — appel le plus lent : `/api/ordres/apercu?statut=valide` 1 082 ms
- [bureau, alimentation, 1440×900] `/production?onglet=plan` : tableau plus large que son cadre 1336>1142 (Plan de production)
- [bureau, alimentation, 1440×900] `/production?onglet=glissant` : tableau plus large que son cadre 1437>1142 (Plan glissant)
- [bureau, alimentation, 1440×900] `/production?onglet=realise` : tableau plus large que son cadre 1384>1142 (Plan et réalisé)
- [bureau, alimentation, 1440×900] `/production?onglet=besoins` : tableau plus large que son cadre 2179>1142 (Besoins matière)
- [bureau, alimentation, 1440×900] `/production/besoins/124` : tableau plus large que son cadre 2179>1142 (Besoins matière)
- [atelier, alimentation, 375×812] `/atelier/envoyer` : lent 1897 ms — appel le plus lent : `/api/ordres/ouverts` 839 ms
- [atelier, alimentation, 375×812] `/atelier/ordres` : lent 1311 ms — appel le plus lent : `/api/ordres/ouverts` 953 ms
- [atelier, alimentation, 375×812] `/atelier/retour` : lent 1273 ms — appel le plus lent : `/api/ordres/ouverts?statut=valide` 925 ms
- [atelier, alimentation, 375×812] `/atelier/retour` : recherche lente 1036 ms (« Plastique-140 »)
- [atelier, direction, 375×812] `/atelier` : lent 1054 ms — appel le plus lent : `/api/contexte` 724 ms
- [atelier, direction, 375×812] `/atelier/envoyer` : lent 1774 ms — appel le plus lent : `/api/ordres/ouverts` 1 420 ms
- [atelier, direction, 375×812] `/atelier/ordres` : lent 1434 ms — appel le plus lent : `/api/ordres/ouverts` 930 ms
- [atelier, direction, 375×812] `/atelier/retour` : lent 1267 ms — appel le plus lent : `/api/ordres/ouverts?statut=valide` 910 ms
- [bureau au téléphone, alimentation, 375×812] `/accueil` : lent 1098 ms — appel le plus lent : `/api/contexte` 735 ms
- [bureau au téléphone, alimentation, 375×812] `/stock?onglet=matieres` : tableau plus large que son cadre 1616>349 (Stock par matière)
- [bureau au téléphone, alimentation, 375×812] `/stock?onglet=lots` : tableau plus large que son cadre 1344>349 (Lots)
- [bureau au téléphone, alimentation, 375×812] `/stock?onglet=mouvements` : tableau plus large que son cadre 778>349 (Mouvements de stock)
- [bureau au téléphone, alimentation, 375×812] `/stock?onglet=ordres` : lent 1081 ms — appel le plus lent : `/api/ordres/consommation` 463 ms
- [bureau au téléphone, alimentation, 375×812] `/stock?onglet=ordres` : tableau sans pagination : 1871 lignes dans le DOM (Ordres de fabrication)
- [bureau au téléphone, alimentation, 375×812] `/stock?onglet=ordres` : tableau plus large que son cadre 856>349 (Ordres de fabrication)
- [bureau au téléphone, alimentation, 375×812] `/stock?onglet=a-valider` : tableau plus large que son cadre 490>349 (Brouillons à valider)
- [bureau au téléphone, alimentation, 375×812] `/stock/matieres/124` : tableau plus large que son cadre 1616>349 (Stock par matière)
- [bureau au téléphone, alimentation, 375×812] `/stock/matieres/124` : tableau plus large que son cadre 1043>341 (Besoins du plan, mois par mois (kg))
- [bureau au téléphone, alimentation, 375×812] `/lots/704` : tableau plus large que son cadre 1344>349 (Lots)
- [bureau au téléphone, alimentation, 375×812] `/lots/704` : tableau plus large que son cadre 494>341 (Mouvements du lot)
- [bureau au téléphone, alimentation, 375×812] `/tracabilite?lot=704` : lent 1185 ms — appel le plus lent : `/api/ordres/consommation` 592 ms
- [bureau au téléphone, alimentation, 375×812] `/tracabilite?lot=704` : tableau sans pagination : 1871 lignes dans le DOM (Ordres de fabrication)
- [bureau au téléphone, alimentation, 375×812] `/tracabilite?lot=704` : tableau plus large que son cadre 856>349 (Ordres de fabrication)
- [bureau au téléphone, alimentation, 375×812] `/tracabilite?lot=704` : tableau plus large que son cadre 725>341 (Mouvements suivis)
- [bureau au téléphone, alimentation, 375×812] `/tracabilite?matiere=124` : lent 1304 ms — appel le plus lent : `/api/ordres/consommation` 639 ms
- [bureau au téléphone, alimentation, 375×812] `/tracabilite?matiere=124` : tableau sans pagination : 1871 lignes dans le DOM (Ordres de fabrication)
- [bureau au téléphone, alimentation, 375×812] `/tracabilite?matiere=124` : tableau plus large que son cadre 856>349 (Ordres de fabrication)
- [bureau au téléphone, alimentation, 375×812] `/tracabilite?matiere=124` : tableau sans pagination : 1424 lignes dans le DOM (Mouvements suivis)
- [bureau au téléphone, alimentation, 375×812] `/tracabilite?matiere=124` : tableau plus large que son cadre 838>341 (Mouvements suivis)
- [bureau au téléphone, alimentation, 375×812] `/sorties?onglet=valide` : lent 1275 ms — appel le plus lent : `/api/ordres/apercu?statut=valide` 906 ms
- [bureau au téléphone, alimentation, 375×812] `/sorties?onglet=valide` : tableau plus large que son cadre 851>349 (Ordres de fabrication)
- [bureau au téléphone, alimentation, 375×812] `/sorties?onglet=brouillon` : tableau plus large que son cadre 730>349 (Ordres de fabrication)
- [bureau au téléphone, alimentation, 375×812] `/sorties?onglet=annule` : tableau plus large que son cadre 821>349 (Ordres de fabrication)
- [bureau au téléphone, alimentation, 375×812] `/ordres/nouveau` : lent 2140 ms — appel le plus lent : `/api/ordres/apercu?statut=valide` 1 758 ms
- [bureau au téléphone, alimentation, 375×812] `/ordres/nouveau` : tableau plus large que son cadre 851>349 (Ordres de fabrication)
- [bureau au téléphone, alimentation, 375×812] `/ordres/nouveau` : tableau plus large que son cadre 483>341 (Les matières qui sortent)
- [bureau au téléphone, alimentation, 375×812] `/ordres/nouveau` : recherche lente 1099 ms (« Plastique-140 »)
- [bureau au téléphone, alimentation, 375×812] `/ordres/2181` : lent 1506 ms — appel le plus lent : `/api/ordres/apercu?statut=valide` 1 136 ms
- [bureau au téléphone, alimentation, 375×812] `/ordres/2181` : tableau plus large que son cadre 851>349 (Ordres de fabrication)
- [bureau au téléphone, alimentation, 375×812] `/ordres/2181/retour` : lent 1148 ms — appel le plus lent : `/api/ordres/apercu?statut=valide` 767 ms
- [bureau au téléphone, alimentation, 375×812] `/ordres/2181/retour` : tableau plus large que son cadre 851>349 (Ordres de fabrication)
- [bureau au téléphone, alimentation, 375×812] `/ordres/2181/retour` : tableau plus large que son cadre 407>341 (Ce qui revient, lot par lot)
- [bureau au téléphone, alimentation, 375×812] `/production?onglet=plan` : tableau plus large que son cadre 1208>349 (Plan de production)
- [bureau au téléphone, alimentation, 375×812] `/production?onglet=glissant` : tableau plus large que son cadre 1317>349 (Plan glissant)
- [bureau au téléphone, alimentation, 375×812] `/production?onglet=realise` : tableau plus large que son cadre 1264>349 (Plan et réalisé)
- [bureau au téléphone, alimentation, 375×812] `/production?onglet=besoins` : tableau plus large que son cadre 2035>349 (Besoins matière)
- [bureau au téléphone, alimentation, 375×812] `/production/besoins/124` : tableau plus large que son cadre 2035>349 (Besoins matière)
- [bureau au téléphone, alimentation, 375×812] `/production/besoins/124` : tableau plus large que son cadre 1049>341 (D’où vient le besoin)
- [bureau au téléphone, alimentation, 375×812] `/operations?onglet=transfert` : tableau plus large que son cadre 640>349 (Opérations)
- [bureau au téléphone, alimentation, 375×812] `/operations?onglet=retour_machine` : tableau plus large que son cadre 630>349 (Opérations)
- [bureau au téléphone, alimentation, 375×812] `/operations/nouvelle?type=transfert` : tableau plus large que son cadre 640>349 (Opérations)
- [bureau au téléphone, alimentation, 375×812] `/operations/641` : tableau plus large que son cadre 630>349 (Opérations)
- [bureau au téléphone, alimentation, 375×812] `/catalogue?onglet=matieres` : tableau plus large que son cadre 934>349 (Matières du catalogue)
- [bureau au téléphone, alimentation, 375×812] `/matieres/124?onglet=classification` : tableau plus large que son cadre 934>349 (Matières du catalogue)
- [bureau au téléphone, alimentation, 375×812] `/matieres/124?onglet=conditionnement` : tableau plus large que son cadre 934>349 (Matières du catalogue)
- [bureau au téléphone, alimentation, 375×812] `/matieres/124?onglet=historique` : tableau plus large que son cadre 934>349 (Matières du catalogue)
- [bureau au téléphone, alimentation, 375×812] `/qualites?onglet=qualites` : tableau plus large que son cadre 966>349 (Qualités)
- [bureau au téléphone, alimentation, 375×812] `/qualites?onglet=nomenclature` : tableau plus large que son cadre 491>349 (Nomenclature)
- [bureau au téléphone, alimentation, 375×812] `/qualites/1?onglet=recette` : tableau plus large que son cadre 966>349 (Qualités)
- [bureau au téléphone, alimentation, 375×812] `/qualites/1?onglet=recette` : tableau plus large que son cadre 545>341 (Recette)
- [bureau au téléphone, alimentation, 375×812] `/qualites/1?onglet=plan` : tableau plus large que son cadre 966>349 (Qualités)
- [bureau au téléphone, alimentation, 375×812] `/qualites/1?onglet=versions` : tableau plus large que son cadre 966>349 (Qualités)
- [bureau au téléphone, alimentation, 375×812] `/qualites/1?onglet=historique` : tableau plus large que son cadre 966>349 (Qualités)
- [bureau au téléphone, alimentation, 375×812] `/metiers` : tableau plus large que son cadre 895>349 (Métiers à tisser)
- [bureau au téléphone, alimentation, 375×812] `/metiers/2?onglet=fils` : tableau plus large que son cadre 895>349 (Métiers à tisser)
- [bureau au téléphone, alimentation, 375×812] `/metiers/2?onglet=fils` : tableau plus large que son cadre 662>341 (Fils montés)
- [bureau au téléphone, alimentation, 375×812] `/metiers/2?onglet=reglages` : tableau plus large que son cadre 895>349 (Métiers à tisser)
- [bureau au téléphone, alimentation, 375×812] `/metiers/2?onglet=historique` : tableau plus large que son cadre 895>349 (Métiers à tisser)
- [bureau au téléphone, alimentation, 375×812] `/metiers/2?onglet=historique` : tableau plus large que son cadre 818>341 (Montages)
- [bureau au téléphone, alimentation, 375×812] `/aide?onglet=calculs` : tableau plus large que son cadre 384>317 (2 col.)
- [bureau au téléphone, alimentation, 375×812] `/aide?onglet=analyse` : tableau plus large que son cadre 322>317 (0 col.)
- [bureau au téléphone, alimentation, 375×812] `/aide?onglet=ecrans` : tableau plus large que son cadre 344>317 (3 col.)

## 4. Exports Excel et documents (A4) — par base

| Genre | Route | referentiels (ms, Ko, statut) | x30 (ms, Ko, statut) | annee-1 (ms, Ko, statut) | annee-2 (ms, Ko, statut) |
|---|---|---|---|---|---|
| document | `/api/documents/bilan?mois=2026-09` | 48 ms, 9 Ko | 7 721 ms, 11 Ko **BLOQUANT** | — | — |
| document | `/api/documents/bilan?mois=2026-10` | 59 ms, 9 Ko | 8 002 ms, 8 Ko **BLOQUANT** | — | — |
| document | `/api/documents/bilan?mois=2027-09` | — | — | 352 ms, 10 Ko | — |
| document | `/api/documents/bilan?mois=2027-10` | — | — | 231 ms, 10 Ko | — |
| document | `/api/documents/bilan?mois=2028-09` | — | — | — | 556 ms, 10 Ko |
| document | `/api/documents/bilan?mois=2028-10` | — | — | — | 783 ms, 10 Ko |
| document | `/api/documents/commandes/275/bon` | — | — | — | 7 ms, 9 Ko |
| document | `/api/documents/commandes/29330/bon` | — | 7 ms, 10 Ko | — | — |
| document | `/api/documents/commandes/85/bon` | — | — | 9 ms, 9 Ko | — |
| document | `/api/documents/etiquettes?lots=280002%2C280041%2C280067%2C280344%2C280412%2C280469%2C280481` | — | 23 ms, 19 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280003%2C280043%2C280069%2C280346%2C280413%2C280470%2C280483` | — | 23 ms, 19 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280004%2C280046%2C280073%2C280350%2C280414%2C280437` | — | 20 ms, 17 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280005%2C280048%2C280075%2C280352%2C280415%2C280439` | — | 21 ms, 17 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280015%2C280038%2C280062%2C280331%2C280410%2C280426` | — | 20 ms, 17 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280016%2C280027%2C280063%2C280340%2C280411%2C280432` | — | 20 ms, 17 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280017%2C280039%2C280065%2C280342%2C280450` | — | 20 ms, 15 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280018%2C280040%2C280066%2C280343%2C280451` | — | 18 ms, 16 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280019%2C280042%2C280068%2C280345%2C280433%2C280482` | — | 21 ms, 18 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280020%2C280045%2C280071%2C280348%2C280435%2C280446%2C280471%2C280504` | — | 25 ms, 21 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280021` | — | 11 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280022%2C280028%2C280072%2C280349%2C280436` | — | 18 ms, 16 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280023%2C280047%2C280074%2C280351%2C280438%2C280452%2C280472%2C280485%2C280505` | — | 25 ms, 23 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280024%2C280049%2C280076%2C280353%2C280416%2C280427` | — | 22 ms, 18 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280025%2C280050%2C280077%2C280354%2C280440%2C280453%2C280473%2C280486%2C280509` | — | 28 ms, 23 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280044%2C280070%2C280347%2C280434%2C280484` | — | 19 ms, 16 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280064%2C280341%2C280449%2C280480` | — | 16 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280082%2C280151%2C280171` | — | 14 ms, 12 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280083%2C280152%2C280172` | — | 15 ms, 12 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280084%2C280119%2C280130%2C280173%2C280636` | — | 19 ms, 16 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280085%2C280104%2C280554` | — | 14 ms, 12 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280086%2C280116%2C280555` | — | 15 ms, 12 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280087%2C280105%2C280153%2C280565` | — | 16 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280088%2C280106%2C280556` | — | 14 ms, 12 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280089%2C280107%2C280131%2C280516%2C280557` | — | 18 ms, 16 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280090%2C280108%2C280154%2C280558` | — | 17 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280091%2C280110%2C280134%2C280157%2C280174%2C280519%2C280561%2C280637` | — | 25 ms, 21 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280092%2C280113%2C280122%2C280137%2C280161%2C280176%2C280566` | — | 22 ms, 19 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280095%2C280111%2C280120%2C280135%2C280158%2C280178%2C280520%2C280562` | — | 25 ms, 21 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280096%2C280112%2C280121%2C280136%2C280159%2C280175%2C280521%2C280563%2C280638` | — | 25 ms, 23 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280109%2C280132%2C280155%2C280517%2C280559` | — | 63 ms, 16 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280117%2C280133%2C280156%2C280518%2C280560` | — | 20 ms, 15 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280180%2C280186%2C280444%2C280457%2C280794%2C280907%2C281009%2C281013` | — | 25 ms, 21 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280182%2C280185%2C280455%2C280793%2C281008` | — | 19 ms, 16 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280189%2C280194%2C280592%2C280595%2C280599%2C280603%2C280607%2C280618%2C280622%2C280626%2C280629` | — | 30 ms, 27 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280201%2C280221%2C280226%2C280239%2C280273%2C280291%2C280299%2C280327` | — | 23 ms, 22 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280202%2C280214%2C280280%2C280310%2C280398` | — | 21 ms, 16 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280203%2C280215%2C280274%2C280281%2C280293%2C280300%2C280317` | — | 22 ms, 20 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280204%2C280217%2C280227%2C280234%2C280240` | — | 19 ms, 16 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280205%2C280218%2C280222%2C280241%2C280282%2C280325` | — | 28 ms, 18 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280212%2C280290%2C280308%2C280315%2C280396` | — | 19 ms, 16 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280213%2C280292%2C280309%2C280316%2C280397` | — | 20 ms, 16 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280231%2C280269%2C280288%2C280322` | — | 16 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280232%2C280270%2C280289%2C280323` | — | 17 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280244%2C280388` | — | 12 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280245%2C280257%2C280363%2C280375%2C280391` | — | 20 ms, 16 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280250%2C280263%2C280389` | — | 15 ms, 12 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280251%2C280253%2C280361%2C280370` | — | 17 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280256%2C280262%2C280360%2C280381` | — | 17 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280264%2C280362%2C280371%2C280374%2C280390` | — | 18 ms, 16 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280271%2C280297` | — | 12 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280272%2C280298` | — | 13 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280307%2C280314%2C280324%2C280395` | — | 16 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280364%2C280372%2C280382` | — | 14 ms, 12 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280365%2C280383` | — | 15 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280404%2C280422` | — | 13 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280405%2C280423%2C280865%2C280897` | — | 17 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280406%2C280419%2C280866%2C280894` | — | 16 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280476%2C280501` | — | 13 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280494` | — | 11 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280495` | — | 12 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280496` | — | 11 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280497` | — | 11 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280498` | — | 11 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280533%2C280576` | — | 15 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280534%2C280578` | — | 13 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280535%2C280581` | — | 13 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280536%2C280582` | — | 14 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280537%2C280583` | — | 14 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280538%2C280589` | — | 14 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280539%2C280584` | — | 13 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280540%2C280585` | — | 12 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280541%2C280586` | — | 12 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280542%2C280587` | — | 12 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280544%2C280577` | — | 13 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280545%2C280579` | — | 12 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280546%2C280580` | — | 12 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280596%2C280600%2C280604%2C280623` | — | 19 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280598%2C280617%2C280628` | — | 15 ms, 12 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280612` | — | 11 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280613` | — | 11 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280614` | — | 11 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280615` | — | 12 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280619` | — | 12 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280643%2C280674%2C280726%2C280745%2C280842` | — | 18 ms, 16 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280644%2C280677%2C280728%2C280747%2C280769%2C280844%2C280887%2C280963%2C281025%2C281054` | — | 30 ms, 25 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280645%2C280678%2C280717%2C280748%2C280749%2C280798%2C280818%2C280845%2C280874%2C280929%2C281026` | — | 30 ms, 27 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280646%2C280679%2C280718%2C280756%2C280770%2C280799%2C280819%2C280858%2C280875%2C280930%2C281027` | — | 29 ms, 27 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280647%2C280680%2C280729%2C280750%2C280771%2C280800%2C280826%2C280846%2C280876%2C280931%2C280964%2C281028%2C281044%2C281055` | — | 36 ms, 33 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280648%2C280681%2C280730%2C280772%2C280801%2C280847%2C280877%2C280932%2C280944%2C280965%2C281038%2C281056` | — | 32 ms, 29 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280649%2C280692%2C280731%2C280751%2C280773%2C280802%2C280820%2C280848%2C280878%2C280933%2C280966%2C281029%2C281045%2C281057` | — | 36 ms, 33 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280650%2C280683%2C280720%2C280775%2C280803%2C280850%2C280880%2C280934%2C280967%2C281031%2C281059` | — | 30 ms, 27 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280651%2C280684%2C280732%2C280776%2C280804%2C280822%2C280859%2C280881%2C280935%2C280968%2C280987%2C281032%2C281047%2C281060` | — | 35 ms, 33 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280652%2C280693%2C280721%2C280778%2C280788%2C280806%2C280811%2C280823%2C280851%2C280883%2C280901%2C280940%2C280947%2C280970%2C280994%2C280998%2C281005%2C281034%2C281048%2C281061` | — | 49 ms, 44 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280653%2C280654%2C280686%2C280722%2C280723%2C280781%2C280824%2C280852%2C280884%2C280971%2C280991%2C280999%2C281035%2C281062%2C281063` | — | 39 ms, 35 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280658%2C280662%2C280701%2C280758%2C280829%2C280890%2C280981` | — | 22 ms, 20 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280659%2C280663%2C280702%2C280760%2C280784%2C280830%2C280891%2C280982` | — | 24 ms, 21 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280669%2C280711%2C280740%2C280837` | — | 16 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280670%2C280712%2C280741%2C280838%2C280928%2C280943%2C280962%2C281022` | — | 25 ms, 21 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280671%2C280713%2C280742%2C280839` | — | 16 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280672%2C280714%2C280743%2C280840` | — | 17 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280673%2C280715%2C280744%2C280841%2C281023` | — | 17 ms, 15 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280675%2C280746` | — | 13 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280676%2C280727%2C280768%2C280817%2C280857%2C280873%2C281024%2C281053` | — | 24 ms, 22 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280682%2C280719%2C280752%2C280774%2C280821%2C280849%2C280879%2C281030%2C281058` | — | 27 ms, 23 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280685%2C280753%2C280777%2C280805%2C280860%2C280882%2C280917%2C280936%2C280946%2C280969%2C280977%2C281033` | — | 31 ms, 29 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280687%2C280724%2C280754%2C280853%2C280885%2C281036%2C281065` | — | 23 ms, 20 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280696%2C280951` | — | 13 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280697%2C280922` | — | 12 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280698%2C280923%2C280954` | — | 15 ms, 12 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280716%2C280843` | — | 14 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280787%2C280810%2C280900` | — | 14 ms, 12 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280864%2C280896` | — | 14 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280898` | — | 10 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280921` | — | 10 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280945` | — | 11 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=280953%2C280983` | — | 13 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281043` | — | 11 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281083%2C281110%2C281142%2C281261` | — | 16 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281084%2C281145%2C281248` | — | 15 ms, 12 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281085%2C281112%2C281149` | — | 15 ms, 12 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281086%2C281151%2C281184` | — | 16 ms, 12 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281087%2C281153%2C281262` | — | 17 ms, 12 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281088%2C281113%2C281154%2C281186%2C281228%2C281251` | — | 23 ms, 17 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281089%2C281155%2C281187%2C281218` | — | 16 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281090%2C281157%2C281188%2C281219%2C281252` | — | 19 ms, 16 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281091%2C281115%2C281158%2C281220%2C281253%2C281268` | — | 20 ms, 17 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281092%2C281116%2C281160%2C281222%2C281255` | — | 19 ms, 16 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281093%2C281117%2C281161%2C281230%2C281256` | — | 21 ms, 15 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281094%2C281167%2C281190%2C281223%2C281257` | — | 22 ms, 15 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281111%2C281166%2C281250%2C281267` | — | 16 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281114%2C281156%2C281196%2C281229%2C281263` | — | 19 ms, 15 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281140` | — | 10 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281141%2C281244` | — | 12 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281143%2C281246` | — | 13 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281144%2C281182%2C281214%2C281247` | — | 17 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281146%2C281215` | — | 13 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281147%2C281195%2C281216%2C281249` | — | 15 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281148` | — | 11 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281150%2C281183%2C281217` | — | 15 ms, 12 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281152%2C281185%2C281227` | — | 17 ms, 12 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281159%2C281197%2C281221%2C281254` | — | 16 ms, 13 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281165%2C281245` | — | 13 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281189` | — | 10 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281291%2C281335%2C281377%2C281524` | — | 17 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281292%2C281336%2C281378%2C281419%2C281454%2C281544` | — | 20 ms, 17 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281293%2C281337%2C281379%2C281420%2C281455%2C281486%2C281525` | — | 22 ms, 19 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281294%2C281338%2C281380%2C281421%2C281526` | — | 18 ms, 16 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281295%2C281339%2C281381%2C281527` | — | 17 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281296%2C281340%2C281382%2C281435%2C281456%2C281487%2C281528` | — | 23 ms, 19 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281297%2C281341%2C281383%2C281422%2C281457%2C281488%2C281529` | — | 22 ms, 19 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281298%2C281342%2C281384%2C281530` | — | 17 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281299%2C281343%2C281385%2C281423%2C281458%2C281489%2C281531` | — | 24 ms, 19 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281300%2C281345%2C281386%2C281532` | — | 17 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281301%2C281346%2C281388%2C281426%2C281460%2C281491%2C281534` | — | 25 ms, 19 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281302%2C281347%2C281400%2C281427%2C281462%2C281493` | — | 22 ms, 17 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281303%2C281356%2C281391%2C281428%2C281463%2C281494%2C281536` | — | 22 ms, 19 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281304%2C281348%2C281392%2C281429%2C281464%2C281495%2C281537` | — | 25 ms, 19 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281305%2C281306%2C281349%2C281350%2C281393%2C281394%2C281430%2C281431%2C281465%2C281466%2C281496%2C281497%2C281538%2C281545` | — | 36 ms, 32 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281307%2C281351%2C281395%2C281432%2C281467%2C281498%2C281539` | — | 21 ms, 19 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281308%2C281352%2C281396%2C281433%2C281468%2C281499%2C281540` | — | 23 ms, 19 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281312%2C281344%2C281399%2C281424%2C281459%2C281490` | — | 20 ms, 17 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281313%2C281355%2C281390%2C281535` | — | 18 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281375` | — | 10 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281376` | — | 10 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281387%2C281425%2C281471` | — | 28 ms, 12 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281389%2C281436%2C281461%2C281492` | — | 18 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281453` | — | 10 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281533` | — | 11 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281556` | — | 10 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281557` | — | 11 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281558` | — | 12 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281559` | — | 10 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281560` | — | 10 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281561` | — | 10 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281562` | — | 12 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281563` | — | 12 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281564` | — | 13 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281565` | — | 10 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=281567` | — | 12 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290002%2C290041%2C290067%2C290344%2C290412%2C290469%2C290481` | — | 24 ms, 19 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290003%2C290043%2C290069%2C290346%2C290413%2C290470%2C290483` | — | 22 ms, 19 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290004%2C290046%2C290073%2C290350%2C290414%2C290437` | — | 21 ms, 18 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290005%2C290048%2C290075%2C290352%2C290415%2C290439` | — | 21 ms, 17 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290006%2C290029%2C290053%2C290329%2C290408` | — | 19 ms, 15 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290007%2C290030%2C290054%2C290330%2C290428%2C290506` | — | 20 ms, 18 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290008%2C290031%2C290055%2C290332%2C290466%2C290479` | — | 20 ms, 17 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290009%2C290032%2C290333%2C290429%2C290507` | — | 18 ms, 16 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290010%2C290033%2C290057%2C290334%2C290447` | — | 19 ms, 16 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290011%2C290034%2C290052%2C290335%2C290467%2C290503` | — | 20 ms, 17 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290012%2C290035%2C290058%2C290336%2C290425` | — | 18 ms, 15 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290013%2C290036%2C290059%2C290337` | — | 18 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290014%2C290037%2C290060%2C290338%2C290409%2C290431%2C290448%2C290478%2C290508` | — | 26 ms, 23 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290015%2C290038%2C290062%2C290331%2C290410%2C290426` | — | 20 ms, 17 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290016%2C290027%2C290063%2C290340%2C290411%2C290432` | — | 20 ms, 17 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290017%2C290039%2C290065%2C290342%2C290450` | — | 19 ms, 16 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290018%2C290040%2C290066%2C290343%2C290451` | — | 18 ms, 16 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290019%2C290042%2C290068%2C290345%2C290433%2C290482` | — | 22 ms, 18 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290020%2C290045%2C290071%2C290348%2C290435%2C290446%2C290471%2C290504` | — | 24 ms, 21 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290021` | — | 12 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290022%2C290028%2C290072%2C290349%2C290436` | — | 19 ms, 16 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290023%2C290047%2C290074%2C290351%2C290438%2C290452%2C290472%2C290485%2C290505` | — | 25 ms, 23 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290024%2C290049%2C290076%2C290353%2C290416%2C290427` | — | 20 ms, 17 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290025%2C290050%2C290077%2C290354%2C290440%2C290453%2C290473%2C290486%2C290509` | — | 27 ms, 23 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290044%2C290070%2C290347%2C290434%2C290484` | — | 18 ms, 16 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290056` | — | 12 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290061%2C290339%2C290468` | — | 15 ms, 12 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290064%2C290341%2C290449%2C290480` | — | 17 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290078%2C290125%2C290142%2C290163` | — | 17 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290079%2C290097%2C290143%2C290164%2C290523%2C290547%2C290631` | — | 23 ms, 19 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290080%2C290098%2C290126%2C290144%2C290165%2C290510%2C290548%2C290632` | — | 25 ms, 21 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290081%2C290100%2C290139%2C290146%2C290167%2C290512%2C290550%2C290633` | — | 23 ms, 21 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290082%2C290151%2C290171` | — | 14 ms, 12 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290083%2C290152%2C290172` | — | 14 ms, 12 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290084%2C290119%2C290130%2C290173%2C290636` | — | 18 ms, 15 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290085%2C290104%2C290554` | — | 23 ms, 12 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290086%2C290116%2C290555` | — | 14 ms, 12 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290087%2C290105%2C290153%2C290565` | — | 16 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290088%2C290106%2C290556` | — | 15 ms, 12 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290089%2C290107%2C290131%2C290516%2C290557` | — | 19 ms, 15 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290090%2C290108%2C290154%2C290558` | — | 17 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290091%2C290110%2C290134%2C290157%2C290174%2C290519%2C290561%2C290637` | — | 24 ms, 21 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290092%2C290113%2C290122%2C290137%2C290161%2C290176%2C290566` | — | 23 ms, 19 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290094%2C290118%2C290124%2C290141%2C290162%2C290630` | — | 20 ms, 17 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290095%2C290111%2C290120%2C290135%2C290158%2C290178%2C290520%2C290562` | — | 27 ms, 21 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290096%2C290112%2C290121%2C290136%2C290159%2C290175%2C290521%2C290563%2C290638` | — | 25 ms, 23 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290099%2C290127%2C290145%2C290166%2C290511%2C290549` | — | 20 ms, 17 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290101%2C290128%2C290148%2C290168%2C290514%2C290552` | — | 21 ms, 17 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290102%2C290149%2C290169%2C290515%2C290553%2C290634` | — | 21 ms, 17 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290103%2C290129%2C290150%2C290170%2C290635` | — | 19 ms, 16 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290109%2C290132%2C290155%2C290517%2C290559` | — | 18 ms, 15 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290115%2C290140%2C290147%2C290513%2C290551` | — | 18 ms, 16 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290117%2C290133%2C290156%2C290518%2C290560` | — | 18 ms, 15 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290180%2C290186%2C290444%2C290457%2C290794%2C290907%2C291009%2C291013` | — | 23 ms, 21 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290181%2C290442%2C290463%2C290905%2C290910%2C291007%2C291011` | — | 23 ms, 20 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290182%2C290185%2C290455%2C290793%2C291008` | — | 18 ms, 16 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290184%2C290792` | — | 12 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290188%2C290610` | — | 13 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290189%2C290194%2C290592%2C290595%2C290599%2C290603%2C290607%2C290618%2C290622%2C290626%2C290629` | — | 30 ms, 27 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290191%2C290606%2C290609%2C290621` | — | 16 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290192` | — | 10 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290195%2C290591%2C290594%2C290602%2C290625` | — | 18 ms, 16 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290196` | — | 10 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290197%2C290208%2C290219%2C290224%2C290229%2C290235%2C290276` | — | 22 ms, 19 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290198%2C290266%2C290285%2C290295%2C290320%2C290393` | — | 20 ms, 18 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290199%2C290220%2C290225%2C290230%2C290296%2C290313%2C290321%2C290394` | — | 25 ms, 21 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290200%2C290210%2C290238%2C290279%2C290306` | — | 18 ms, 16 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290201%2C290221%2C290226%2C290239%2C290273%2C290291%2C290299%2C290327` | — | 24 ms, 21 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290202%2C290214%2C290280%2C290310%2C290398` | — | 18 ms, 16 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290203%2C290215%2C290274%2C290281%2C290293%2C290300%2C290317` | — | 22 ms, 20 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290204%2C290217%2C290227%2C290234%2C290240` | — | 19 ms, 16 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290205%2C290218%2C290222%2C290241%2C290282%2C290325` | — | 22 ms, 18 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290207%2C290265%2C290284%2C290302%2C290303%2C290312%2C290319%2C290392` | — | 24 ms, 21 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290209%2C290236%2C290267%2C290277%2C290286%2C290304` | — | 21 ms, 18 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290211` | — | 10 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290212%2C290290%2C290308%2C290315%2C290396` | — | 19 ms, 16 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290213%2C290292%2C290309%2C290316%2C290397` | — | 18 ms, 16 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290231%2C290269%2C290288%2C290322` | — | 16 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290232%2C290270%2C290289%2C290323` | — | 16 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290237%2C290268%2C290278%2C290287%2C290305` | — | 20 ms, 16 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290244%2C290388` | — | 13 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290245%2C290257%2C290363%2C290375%2C290391` | — | 20 ms, 16 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290246%2C290254%2C290259%2C290356%2C290377` | — | 19 ms, 16 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290247%2C290260%2C290357%2C290368%2C290378%2C290385` | — | 20 ms, 18 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290248%2C290255%2C290261%2C290359%2C290369%2C290380%2C290386` | — | 22 ms, 19 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290249%2C290387` | — | 12 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290250%2C290263%2C290389` | — | 14 ms, 12 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290251%2C290253%2C290361%2C290370` | — | 17 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290256%2C290262%2C290360%2C290381` | — | 16 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290264%2C290362%2C290371%2C290374%2C290390` | — | 17 ms, 16 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290271%2C290297` | — | 12 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290272%2C290298` | — | 12 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290307%2C290314%2C290324%2C290395` | — | 16 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290358%2C290379` | — | 13 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290364%2C290372%2C290382` | — | 14 ms, 12 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290365%2C290383` | — | 13 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290367%2C290376` | — | 13 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290401%2C290420%2C290443%2C290456%2C290464%2C290895%2C290906%2C290911` | — | 23 ms, 21 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290402%2C290462%2C290909` | — | 14 ms, 12 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290403%2C290421%2C290863%2C291012` | — | 16 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290404%2C290422` | — | 12 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290405%2C290423%2C290865%2C290897` | — | 17 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290406%2C290419%2C290866%2C290894` | — | 18 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290418%2C290862%2C290893` | — | 15 ms, 12 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290430` | — | 11 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290459%2C290488%2C290491` | — | 14 ms, 12 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290460%2C290475%2C290489` | — | 15 ms, 12 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290476%2C290501` | — | 14 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290492` | — | 12 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290493%2C290500` | — | 13 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290494` | — | 11 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290495` | — | 13 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290496` | — | 11 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290497` | — | 10 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290498` | — | 11 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290525%2C290568` | — | 14 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290526%2C290569` | — | 13 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290527%2C290570` | — | 12 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290528%2C290588` | — | 13 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290529%2C290571` | — | 14 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290530%2C290573` | — | 14 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290531%2C290574` | — | 13 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290532%2C290575` | — | 12 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290533%2C290576` | — | 17 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290534%2C290578` | — | 12 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290535%2C290581` | — | 13 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290536%2C290582` | — | 12 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290537%2C290583` | — | 13 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290538%2C290589` | — | 13 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290539%2C290584` | — | 12 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290540%2C290585` | — | 13 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290541%2C290586` | — | 12 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290542%2C290587` | — | 13 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290543%2C290572` | — | 14 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290544%2C290577` | — | 12 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290545%2C290579` | — | 14 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290546%2C290580` | — | 13 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290596%2C290600%2C290604%2C290623` | — | 17 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290598%2C290617%2C290628` | — | 14 ms, 12 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290611` | — | 12 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290612` | — | 10 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290613` | — | 11 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290614` | — | 12 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290615` | — | 11 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290619` | — | 11 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290640%2C290664%2C290703%2C290733%2C290761%2C290785%2C290795%2C290808%2C290813%2C290831%2C290867%2C290903%2C290912%2C290924%2C290941%2C290955%2C290973%2C290984%2C290989%2C290995%2C291001%2C291014%2C291039%2C291049` | — | 54 ms, 51 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290641%2C290665%2C290704%2C290734%2C290762%2C290786%2C290796%2C290809%2C290814%2C290832%2C290868%2C290899%2C290913%2C290925%2C290942%2C290956%2C290974%2C290985%2C290990%2C290996%2C291002%2C291015%2C291040%2C291050` | — | 55 ms, 52 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290642%2C290666%2C290705%2C290735%2C290780%2C290855%2C290869%2C291016%2C291041%2C291051` | — | 28 ms, 25 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290643%2C290674%2C290726%2C290745%2C290842` | — | 17 ms, 16 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290644%2C290677%2C290728%2C290747%2C290769%2C290844%2C290887%2C290963%2C291025%2C291054` | — | 28 ms, 25 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290645%2C290678%2C290717%2C290748%2C290749%2C290798%2C290818%2C290845%2C290874%2C290929%2C291026` | — | 30 ms, 27 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290646%2C290679%2C290718%2C290756%2C290770%2C290799%2C290819%2C290858%2C290875%2C290930%2C291027` | — | 29 ms, 27 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290647%2C290680%2C290729%2C290750%2C290771%2C290800%2C290826%2C290846%2C290876%2C290931%2C290964%2C291028%2C291044%2C291055` | — | 35 ms, 33 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290648%2C290681%2C290730%2C290772%2C290801%2C290847%2C290877%2C290932%2C290944%2C290965%2C291038%2C291056` | — | 32 ms, 29 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290649%2C290692%2C290731%2C290751%2C290773%2C290802%2C290820%2C290848%2C290878%2C290933%2C290966%2C291029%2C291045%2C291057` | — | 34 ms, 33 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290650%2C290683%2C290720%2C290775%2C290803%2C290850%2C290880%2C290934%2C290967%2C291031%2C291059` | — | 30 ms, 27 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290651%2C290684%2C290732%2C290776%2C290804%2C290822%2C290859%2C290881%2C290935%2C290968%2C290987%2C291032%2C291047%2C291060` | — | 35 ms, 33 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290652%2C290693%2C290721%2C290778%2C290788%2C290806%2C290811%2C290823%2C290851%2C290883%2C290901%2C290940%2C290947%2C290970%2C290994%2C290998%2C291005%2C291034%2C291048%2C291061` | — | 47 ms, 44 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290653%2C290654%2C290686%2C290722%2C290723%2C290781%2C290824%2C290852%2C290884%2C290971%2C290991%2C290999%2C291035%2C291062%2C291063` | — | 36 ms, 35 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290657%2C290759%2C290828` | — | 14 ms, 12 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290658%2C290662%2C290701%2C290758%2C290829%2C290890%2C290981` | — | 22 ms, 20 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290659%2C290663%2C290702%2C290760%2C290784%2C290830%2C290891%2C290982` | — | 25 ms, 22 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290661` | — | 12 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290667%2C290706%2C290736%2C290763%2C290797%2C290815%2C290833%2C290870` | — | 24 ms, 21 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290668%2C290710%2C290739%2C290767%2C290836%2C290872` | — | 20 ms, 18 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290669%2C290711%2C290740%2C290837` | — | 17 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290670%2C290712%2C290741%2C290838%2C290928%2C290943%2C290962%2C291022` | — | 24 ms, 21 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290671%2C290713%2C290742%2C290839` | — | 16 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290672%2C290714%2C290743%2C290840` | — | 17 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290673%2C290715%2C290744%2C290841%2C291023` | — | 18 ms, 16 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290675%2C290746` | — | 13 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290676%2C290727%2C290768%2C290817%2C290857%2C290873%2C291024%2C291053` | — | 25 ms, 22 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290682%2C290719%2C290752%2C290774%2C290821%2C290849%2C290879%2C291030%2C291058` | — | 29 ms, 24 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290685%2C290753%2C290777%2C290805%2C290860%2C290882%2C290917%2C290936%2C290946%2C290969%2C290977%2C291033` | — | 32 ms, 29 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290687%2C290724%2C290754%2C290853%2C290885%2C291036%2C291065` | — | 33 ms, 20 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290689%2C290707%2C290764%2C290856%2C290915%2C290960%2C291019` | — | 23 ms, 20 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290690%2C290708%2C290738%2C290765%2C290816%2C290834%2C290871%2C290927%2C291020%2C291042%2C291052` | — | 29 ms, 27 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290691%2C290709%2C290766%2C290835%2C290916%2C290961%2C291021` | — | 22 ms, 19 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290695%2C290700%2C290783%2C290920%2C290952%2C290980` | — | 21 ms, 18 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290696%2C290951` | — | 14 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290697%2C290922` | — | 15 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290698%2C290923%2C290954` | — | 15 ms, 12 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290716%2C290843` | — | 13 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290737%2C290914%2C290926%2C290949%2C290957%2C290986%2C290993%2C290997%2C291003` | — | 27 ms, 23 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290787%2C290810%2C290900` | — | 14 ms, 12 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290791` | — | 11 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290864%2C290896` | — | 13 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290889` | — | 11 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290898` | — | 11 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290921` | — | 10 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290938%2C290958%2C290975%2C291017` | — | 16 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290939%2C290959%2C290976%2C291018` | — | 15 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290945` | — | 11 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=290953%2C290983` | — | 13 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291043` | — | 11 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291066%2C291097%2C291168%2C291198%2C291231%2C291264` | — | 21 ms, 17 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291067%2C291098%2C291192%2C291233` | — | 17 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291068%2C291099%2C291170%2C291200%2C291234%2C291270` | — | 20 ms, 17 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291069%2C291100%2C291121%2C291173` | — | 15 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291070%2C291101%2C291122%2C291193%2C291226%2C291236` | — | 19 ms, 17 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291071%2C291123%2C291174%2C291203%2C291237` | — | 19 ms, 15 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291072%2C291102%2C291124%2C291204` | — | 17 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291073%2C291103%2C291125%2C291265` | — | 16 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291074%2C291104%2C291127%2C291194%2C291207%2C291240` | — | 20 ms, 17 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291075%2C291105%2C291128%2C291177%2C291208%2C291241%2C291266` | — | 23 ms, 19 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291076%2C291106%2C291129%2C291178%2C291209%2C291260` | — | 20 ms, 17 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291077%2C291130%2C291179%2C291210%2C291242` | — | 18 ms, 16 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291078%2C291107%2C291132` | — | 15 ms, 12 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291079%2C291133%2C291181%2C291212%2C291243` | — | 18 ms, 15 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291080%2C291108%2C291134%2C291213` | — | 18 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291081%2C291109%2C291136` | — | 14 ms, 12 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291082%2C291138` | — | 13 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291083%2C291110%2C291142%2C291261` | — | 16 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291084%2C291145%2C291248` | — | 15 ms, 12 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291085%2C291112%2C291149` | — | 15 ms, 12 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291086%2C291151%2C291184` | — | 15 ms, 12 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291087%2C291153%2C291262` | — | 15 ms, 12 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291088%2C291113%2C291154%2C291186%2C291228%2C291251` | — | 22 ms, 17 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291089%2C291155%2C291187%2C291218` | — | 17 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291090%2C291157%2C291188%2C291219%2C291252` | — | 18 ms, 16 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291091%2C291115%2C291158%2C291220%2C291253%2C291268` | — | 21 ms, 17 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291092%2C291116%2C291160%2C291222%2C291255` | — | 19 ms, 16 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291093%2C291117%2C291161%2C291230%2C291256` | — | 18 ms, 15 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291094%2C291167%2C291190%2C291223%2C291257` | — | 25 ms, 15 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291096%2C291169%2C291199%2C291232` | — | 16 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291111%2C291166%2C291250%2C291267` | — | 17 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291114%2C291156%2C291196%2C291229%2C291263` | — | 20 ms, 15 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291119%2C291171%2C291225%2C291235` | — | 16 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291120%2C291172%2C291202%2C291259` | — | 16 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291126%2C291175%2C291205%2C291238` | — | 16 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291131%2C291211` | — | 12 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291135` | — | 12 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291137` | — | 10 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291139` | — | 9 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291140` | — | 10 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291141%2C291244` | — | 13 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291143%2C291246` | — | 12 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291144%2C291182%2C291214%2C291247` | — | 19 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291146%2C291215` | — | 11 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291147%2C291195%2C291216%2C291249` | — | 16 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291148` | — | 11 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291150%2C291183%2C291217` | — | 15 ms, 12 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291152%2C291185%2C291227` | — | 14 ms, 12 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291159%2C291197%2C291221%2C291254` | — | 17 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291163%2C291176%2C291206%2C291239` | — | 17 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291164` | — | 12 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291165%2C291245` | — | 12 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291180` | — | 11 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291189` | — | 11 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291201` | — | 11 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291271%2C291314%2C291401%2C291437%2C291472%2C291502` | — | 20 ms, 17 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291272%2C291310%2C291315%2C291316%2C291402%2C291403%2C291438%2C291439%2C291473%2C291503%2C291542` | — | 30 ms, 27 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291273%2C291317%2C291404%2C291440%2C291474%2C291504` | — | 20 ms, 17 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291274%2C291318%2C291358%2C291405%2C291470%2C291475%2C291505` | — | 21 ms, 19 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291275%2C291319%2C291359%2C291406%2C291506` | — | 17 ms, 15 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291276%2C291321%2C291407%2C291442%2C291477%2C291508` | — | 20 ms, 17 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291277%2C291322%2C291361%2C291408%2C291443%2C291501%2C291509` | — | 22 ms, 19 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291278%2C291311%2C291323%2C291362%2C291409%2C291444%2C291478%2C291510` | — | 26 ms, 21 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291279%2C291363%2C291445%2C291512` | — | 17 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291280%2C291325%2C291364%2C291411%2C291446%2C291480%2C291513` | — | 22 ms, 19 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291281%2C291354%2C291365%2C291412%2C291447%2C291481%2C291514` | — | 23 ms, 19 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291282%2C291327%2C291366%2C291413%2C291448%2C291482%2C291515` | — | 22 ms, 19 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291283%2C291367%2C291414%2C291516` | — | 16 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291284%2C291328%2C291415%2C291449%2C291483%2C291517` | — | 22 ms, 17 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291285%2C291329%2C291368%2C291543` | — | 17 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291286%2C291330%2C291369%2C291416%2C291450%2C291484%2C291518` | — | 23 ms, 19 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291287%2C291331%2C291370%2C291485%2C291519` | — | 19 ms, 16 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291288%2C291371%2C291417%2C291451%2C291520` | — | 18 ms, 15 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291289%2C291332%2C291372%2C291418%2C291452%2C291521` | — | 20 ms, 17 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291290%2C291334%2C291374%2C291523` | — | 16 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291291%2C291335%2C291377%2C291524` | — | 16 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291292%2C291336%2C291378%2C291419%2C291454%2C291544` | — | 20 ms, 17 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291293%2C291337%2C291379%2C291420%2C291455%2C291486%2C291525` | — | 22 ms, 19 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291294%2C291338%2C291380%2C291421%2C291526` | — | 18 ms, 15 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291295%2C291339%2C291381%2C291527` | — | 18 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291296%2C291340%2C291382%2C291435%2C291456%2C291487%2C291528` | — | 23 ms, 19 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291297%2C291341%2C291383%2C291422%2C291457%2C291488%2C291529` | — | 21 ms, 19 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291298%2C291342%2C291384%2C291530` | — | 16 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291299%2C291343%2C291385%2C291423%2C291458%2C291489%2C291531` | — | 22 ms, 19 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291300%2C291345%2C291386%2C291532` | — | 17 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291301%2C291346%2C291388%2C291426%2C291460%2C291491%2C291534` | — | 22 ms, 19 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291302%2C291347%2C291400%2C291427%2C291462%2C291493` | — | 20 ms, 17 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291303%2C291356%2C291391%2C291428%2C291463%2C291494%2C291536` | — | 23 ms, 19 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291304%2C291348%2C291392%2C291429%2C291464%2C291495%2C291537` | — | 23 ms, 19 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291305%2C291306%2C291349%2C291350%2C291393%2C291394%2C291430%2C291431%2C291465%2C291466%2C291496%2C291497%2C291538%2C291545` | — | 36 ms, 32 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291307%2C291351%2C291395%2C291432%2C291467%2C291498%2C291539` | — | 22 ms, 19 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291308%2C291352%2C291396%2C291433%2C291468%2C291499%2C291540` | — | 23 ms, 19 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291312%2C291344%2C291399%2C291424%2C291459%2C291490` | — | 21 ms, 17 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291313%2C291355%2C291390%2C291535` | — | 18 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291320%2C291360%2C291441%2C291476%2C291507` | — | 18 ms, 15 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291324%2C291398%2C291410%2C291479%2C291511` | — | 18 ms, 16 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291326` | — | 11 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291333%2C291373%2C291522` | — | 17 ms, 12 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291357` | — | 11 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291375` | — | 10 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291376` | — | 10 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291387%2C291425%2C291471` | — | 15 ms, 12 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291389%2C291436%2C291461%2C291492` | — | 18 ms, 14 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291453` | — | 11 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291533` | — | 12 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291547` | — | 11 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291548` | — | 10 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291549` | — | 11 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291550` | — | 11 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291551` | — | 12 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291552` | — | 11 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291553` | — | 13 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291554%2C291555` | — | 13 ms, 10 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291556` | — | 10 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291557` | — | 23 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291558` | — | 12 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291559` | — | 11 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291560` | — | 11 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291561` | — | 13 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291562` | — | 11 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291563` | — | 10 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291564` | — | 17 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291565` | — | 18 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291566` | — | 11 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=291567` | — | 19 ms, 8 Ko | — | — |
| document | `/api/documents/etiquettes?lots=349` | — | — | 11 ms, 8 Ko | — |
| document | `/api/documents/etiquettes?lots=350%2C351` | — | — | 12 ms, 10 Ko | — |
| document | `/api/documents/etiquettes?lots=352` | — | — | 10 ms, 8 Ko | — |
| document | `/api/documents/etiquettes?lots=353` | — | — | 12 ms, 8 Ko | — |
| document | `/api/documents/etiquettes?lots=696%2C697%2C698%2C699` | — | — | — | 14 ms, 14 Ko |
| document | `/api/documents/etiquettes?lots=700%2C701%2C702` | — | — | — | 110 ms, 12 Ko |
| document | `/api/documents/etiquettes?lots=703%2C704` | — | — | — | 12 ms, 10 Ko |
| document | `/api/documents/etiquettes?lots=703,704` | — | — | — | 11 ms, 10 Ko |
| document | `/api/documents/etiquettes?lots=704` | — | — | — | 11 ms, 8 Ko |
| document | `/api/documents/inventaires/26/feuille` | — | — | 17 ms, 8 Ko | — |
| document | `/api/documents/inventaires/26/feuille?recomptage=true` | — | — | 7 ms, 6 Ko | — |
| document | `/api/documents/inventaires/26/feuille?theorique=true` | — | — | 6 ms, 8 Ko | — |
| document | `/api/documents/inventaires/2912/feuille` | — | 18 ms, 16 Ko | — | — |
| document | `/api/documents/inventaires/2912/feuille?recomptage=true` | — | 10 ms, 6 Ko | — | — |
| document | `/api/documents/inventaires/2912/feuille?theorique=true` | — | 8 ms, 17 Ko | — | — |
| document | `/api/documents/inventaires/57/feuille` | — | — | — | 14 ms, 116 Ko |
| document | `/api/documents/inventaires/57/feuille?recomptage=true` | — | — | — | 15 ms, 6 Ko |
| document | `/api/documents/inventaires/57/feuille?theorique=true` | — | — | — | 19 ms, 127 Ko |
| export | `/api/export/commandes` | 17 ms, 6 Ko | 11 878 ms, 4663 Ko **BLOQUANT** | 64 ms, 33 Ko | 157 ms, 82 Ko |
| export | `/api/export/commandes/275/bon` | — | — | — | 11 ms, 6 Ko |
| export | `/api/export/commandes/29330/bon` | — | 7 ms, 0 Ko **409** | — | — |
| export | `/api/export/commandes/85/bon` | — | — | 14 ms, 6 Ko | — |
| export | `/api/export/commandes?statut=a_approuver` | 13 ms, 6 Ko | 199 ms, 6 Ko | 20 ms, 6 Ko | 21 ms, 6 Ko |
| export | `/api/export/commandes?statut=brouillon` | 15 ms, 6 Ko | 199 ms, 6 Ko | 20 ms, 6 Ko | 19 ms, 6 Ko |
| export | `/api/export/commandes?statut=clos` | 14 ms, 6 Ko | 8 985 ms, 3601 Ko **BLOQUANT** | 55 ms, 25 Ko | 131 ms, 66 Ko |
| export | `/api/export/commandes?statut=confirmee` | 16 ms, 6 Ko | 2 903 ms, 928 Ko lent | 39 ms, 14 Ko | 58 ms, 23 Ko |
| export | `/api/export/commandes?statut=envoyee` | 16 ms, 6 Ko | 201 ms, 6 Ko | 21 ms, 7 Ko | 27 ms, 6 Ko |
| export | `/api/export/controles` | 19 ms, 22 Ko | 333 ms, 249 Ko | 30 ms, 30 Ko | 31 ms, 34 Ko |
| export | `/api/export/dossiers` | 13 ms, 7 Ko | 11 417 ms, 4726 Ko **BLOQUANT** | 99 ms, 70 Ko | 377 ms, 174 Ko |
| export | `/api/export/dossiers?statut=clos` | 13 ms, 7 Ko | 8 295 ms, 3861 Ko **BLOQUANT** | 112 ms, 70 Ko | 341 ms, 173 Ko |
| export | `/api/export/dossiers?statut=ouvert` | 13 ms, 7 Ko | 1 758 ms, 874 Ko lent | 13 ms, 7 Ko | 24 ms, 9 Ko |
| export | `/api/export/echeancier` | 15 ms, 7 Ko | 4 245 ms, 958 Ko **BLOQUANT** | 45 ms, 24 Ko | 150 ms, 29 Ko |
| export | `/api/export/fournisseurs` | 11 ms, 6 Ko | 1 430 ms, 364 Ko lent | 21 ms, 11 Ko | 38 ms, 19 Ko |
| export | `/api/export/fournisseurs/fiches` | 13 ms, 6 Ko | 35 ms, 6 Ko | 16 ms, 6 Ko | 17 ms, 6 Ko |
| export | `/api/export/inventaires` | 11 ms, 5 Ko | 1 338 ms, 35 Ko lent | 79 ms, 8 Ko | 266 ms, 11 Ko |
| export | `/api/export/inventaires/26` | — | — | 36 ms, 6 Ko | — |
| export | `/api/export/inventaires/2912` | — | 601 ms, 8 Ko | — | — |
| export | `/api/export/inventaires/57` | — | — | — | 93 ms, 27 Ko |
| export | `/api/export/inventaires?statut=ouvert` | 11 ms, 5 Ko | 602 ms, 5 Ko | 32 ms, 5 Ko | 52 ms, 5 Ko |
| export | `/api/export/journal` | 4 ms, 0 Ko **403** | 8 824 ms, 4652 Ko **BLOQUANT** | 436 ms, 329 Ko | 1 028 ms, 777 Ko lent |
| export | `/api/export/lots` | 13 ms, 5 Ko | 3 988 ms, 1371 Ko **BLOQUANT** | 212 ms, 46 Ko | 210 ms, 79 Ko |
| export | `/api/export/matieres` | 102 ms, 20 Ko | 151 ms, 44 Ko | 55 ms, 21 Ko | 69 ms, 21 Ko |
| export | `/api/export/matieres?actif=true` | 39 ms, 20 Ko | 134 ms, 44 Ko | 53 ms, 21 Ko | 60 ms, 21 Ko |
| export | `/api/export/metiers` | 13 ms, 5 Ko | 670 ms, 5 Ko | 43 ms, 8 Ko | 58 ms, 9 Ko |
| export | `/api/export/mouvements` | 13 ms, 5 Ko | 46 006 ms, 27585 Ko **BLOQUANT** | 2 143 ms, 1247 Ko lent | 3 978 ms, 2425 Ko **BLOQUANT** |
| export | `/api/export/mouvements?avec_valeur=true` | 12 ms, 5 Ko | 43 756 ms, 27585 Ko **BLOQUANT** | 2 151 ms, 1247 Ko lent | 4 186 ms, 2425 Ko **BLOQUANT** |
| export | `/api/export/operations` | 8 ms, 5 Ko | 9 ms, 5 Ko | 80 ms, 47 Ko | 228 ms, 77 Ko |
| export | `/api/export/operations?type=ajustement` | 8 ms, 5 Ko | 8 ms, 5 Ko | 13 ms, 6 Ko | 17 ms, 7 Ko |
| export | `/api/export/operations?type=ouverture` | 9 ms, 5 Ko | 11 ms, 5 Ko | 29 ms, 15 Ko | 28 ms, 15 Ko |
| export | `/api/export/operations?type=retour_fournisseur` | 8 ms, 5 Ko | 9 ms, 5 Ko | 14 ms, 6 Ko | 20 ms, 7 Ko |
| export | `/api/export/operations?type=retour_machine` | 8 ms, 5 Ko | 9 ms, 5 Ko | 125 ms, 22 Ko | 62 ms, 38 Ko |
| export | `/api/export/operations?type=transfert` | 8 ms, 5 Ko | 9 ms, 5 Ko | 30 ms, 16 Ko | 47 ms, 27 Ko |
| export | `/api/export/opportunites` | 10 ms, 5 Ko | 278 ms, 12 Ko | 12 ms, 6 Ko | 19 ms, 6 Ko |
| export | `/api/export/opportunites?meme_couleur=true&autre_fournisseur=true&prix_catalogue=false` | 12 ms, 5 Ko | 335 ms, 12 Ko | 14 ms, 6 Ko | 21 ms, 6 Ko |
| export | `/api/export/ordres` | 7 ms, 5 Ko | 8 162 ms, 704 Ko **BLOQUANT** | 524 ms, 92 Ko | 888 ms, 176 Ko |
| export | `/api/export/ordres?statut=annule` | 9 ms, 5 Ko | 8 ms, 5 Ko | 64 ms, 7 Ko | 116 ms, 9 Ko |
| export | `/api/export/ordres?statut=brouillon` | 9 ms, 5 Ko | 301 ms, 6 Ko | 22 ms, 5 Ko | 9 ms, 5 Ko |
| export | `/api/export/ordres?statut=valide` | 7 ms, 5 Ko | 8 533 ms, 702 Ko **BLOQUANT** | 482 ms, 90 Ko | 894 ms, 171 Ko |
| export | `/api/export/ordres?vue=consommation` | 12 ms, 5 Ko | 3 384 ms, 1567 Ko **BLOQUANT** | 279 ms, 104 Ko | 545 ms, 202 Ko |
| export | `/api/export/pilotage` | 62 ms, 47 Ko | 1 237 ms, 79 Ko lent | 111 ms, 44 Ko | 166 ms, 47 Ko |
| export | `/api/export/plan-achat?onglet=fournisseurs` | 15 ms, 6 Ko | 261 ms, 5 Ko | 29 ms, 5 Ko | 41 ms, 5 Ko |
| export | `/api/export/plan-achat?onglet=references` | 27 ms, 15 Ko | 260 ms, 5 Ko | 33 ms, 6 Ko | 41 ms, 6 Ko |
| export | `/api/export/prix` | 13 ms, 5 Ko | 6 288 ms, 2800 Ko **BLOQUANT** | 42 ms, 27 Ko | 76 ms, 56 Ko |
| export | `/api/export/production?onglet=besoins` | 30 ms, 16 Ko | 313 ms, 34 Ko | 45 ms, 21 Ko | 54 ms, 21 Ko |
| export | `/api/export/production?onglet=glissant` | 12 ms, 6 Ko | 48 ms, 8 Ko | 19 ms, 7 Ko | 19 ms, 7 Ko |
| export | `/api/export/production?onglet=realise` | 13 ms, 7 Ko | 43 ms, 12 Ko | 16 ms, 8 Ko | 21 ms, 9 Ko |
| export | `/api/export/qualites` | 37 ms, 26 Ko | 106 ms, 61 Ko | 46 ms, 28 Ko | 46 ms, 29 Ko |
| export | `/api/export/receptions` | 11 ms, 6 Ko | 16 296 ms, 5696 Ko **BLOQUANT** | 87 ms, 42 Ko | 193 ms, 94 Ko |
| export | `/api/export/receptions/bobines` | 11 ms, 6 Ko | 6 011 ms, 985 Ko **BLOQUANT** | 31 ms, 22 Ko | 39 ms, 31 Ko |
| export | `/api/export/receptions/pesees` | 10 ms, 5 Ko | 11 315 ms, 4395 Ko **BLOQUANT** | 73 ms, 35 Ko | 136 ms, 72 Ko |
| export | `/api/export/receptions?statut=annulee` | 11 ms, 6 Ko | 12 ms, 6 Ko | 12 ms, 6 Ko | 11 ms, 6 Ko |
| export | `/api/export/receptions?statut=brouillon` | 12 ms, 6 Ko | 750 ms, 67 Ko | 31 ms, 6 Ko | 13 ms, 6 Ko |
| export | `/api/export/receptions?statut=validee` | 10 ms, 6 Ko | 14 157 ms, 5614 Ko **BLOQUANT** | 99 ms, 42 Ko | 195 ms, 94 Ko |
| export | `/api/export/revient` | 32 ms, 6 Ko | 8 712 ms, 2745 Ko **BLOQUANT** | 106 ms, 38 Ko | 170 ms, 70 Ko |
| export | `/api/export/revient?axe=titrage` | 9 ms, 6 Ko | 4 610 ms, 2708 Ko **BLOQUANT** | 32 ms, 31 Ko | 59 ms, 63 Ko |
| export | `/api/export/valorisation` | 10 ms, 5 Ko | 672 ms, 28 Ko | 37 ms, 14 Ko | 54 ms, 14 Ko |

## 5. Recherche à la frappe (liste de l'écran) et recherche globale

| Rôle | Écran | referentiels (mot → ms, lignes) | x30 (mot → ms, lignes) | annee-1 (mot → ms, lignes) | annee-2 (mot → ms, lignes) |
|---|---|---|---|---|---|
| direction | `/cockpit?onglet=alertes` | « PP » → 106 ms (écran), 83→29 l. | « Plastique » → 105 ms (écran), 0→0 l. | « Plastique-140 » → 106 ms (écran), 1→0 l. | « Plastique-140 » → 106 ms (écran), 3→0 l. |
| direction | `/stock?onglet=matieres` | « PP » → 105 ms (écran), 124→42 l. | « Plastique » → 106 ms (écran), 372→42 l. | « Plastique-140 » → 105 ms (écran), 128→1 l. | « Plastique-140 » → 105 ms (écran), 132→1 l. |
| direction | `/stock?onglet=lots` | « PP » → 104 ms (écran), 0→0 l. | « LOM260920-17 » → 266 ms (écran), 20160→30 l. | « LOT-2027-001 » → 105 ms (écran), 313→6 l. | « G-281013-061 » → 108 ms (écran), 525→2 l. |
| direction | `/stock?onglet=mouvements` | « PP » → 350 ms (serveur), 0→0 l. | « Plastique » → 2 500 ms (serveur), 500→500 l. | « Plastique-140 » → 592 ms (serveur), 500→500 l. | « Plastique-140 » → 765 ms (serveur), 500→500 l. |
| direction | `/stock?onglet=ordres` | « PP » → 104 ms (écran), 0→0 l. | « Plastique » → 161 ms (écran), 9570→9570 l. | « Plastique-140 » → 109 ms (écran), 951→653 l. | « Plastique-140 » → 136 ms (écran), 1871→1237 l. |
| direction | `/stock?onglet=a-valider` | « PP » → 105 ms (écran), 0→0 l. | « Plastique » → 105 ms (écran), 60→0 l. | « Plastique-140 » → 105 ms (écran), 3→0 l. | « Plastique-140 » → 105 ms (écran), 0→0 l. |
| direction | `/stock/matieres/1` | « PP » → 105 ms (écran), 151→69 l. | — | — | — |
| direction | `/tracabilite?matiere=1` | « PP » → 104 ms (écran), 0→0 l. | — | — | — |
| direction | `/sorties?onglet=valide` | « PP » → 104 ms (serveur), 0→0 l. | « Plastique » → 8 141 ms (serveur), 500→500 l. | « Plastique-140 » → 681 ms (serveur), 500→500 l. | « Plastique-140 » → 1 004 ms (serveur), 500→500 l. |
| direction | `/sorties?onglet=brouillon` | « PP » → 104 ms (serveur), 0→0 l. | « Plastique » → 354 ms (serveur), 30→30 l. | « Plastique-140 » → 106 ms (serveur), 1→0 l. | « Plastique-140 » → 105 ms (serveur), 0→0 l. |
| direction | `/sorties?onglet=annule` | « PP » → 105 ms (serveur), 0→0 l. | « Plastique » → 272 ms (serveur), 0→0 l. | « Plastique-140 » → 230 ms (serveur), 34→25 l. | « Plastique-140 » → 312 ms (serveur), 78→52 l. |
| direction | `/ordres/nouveau` | « PP » → 104 ms (serveur), 1→1 l. | « Plastique » → 8 749 ms (serveur), 501→501 l. | « Plastique-140 » → 651 ms (serveur), 501→501 l. | « Plastique-140 » → 700 ms (serveur), 501→501 l. |
| direction | `/production?onglet=plan` | « PP » → 105 ms (écran), 18→0 l. | « Plastique » → 106 ms (écran), 54→0 l. | « Plastique-140 » → 105 ms (écran), 22→0 l. | « Plastique-140 » → 111 ms (écran), 26→0 l. |
| direction | `/production?onglet=glissant` | « PP » → 105 ms (écran), 18→0 l. | « Plastique » → 106 ms (écran), 54→0 l. | « Plastique-140 » → 104 ms (écran), 22→0 l. | « Plastique-140 » → 105 ms (écran), 26→0 l. |
| direction | `/production?onglet=realise` | « PP » → 105 ms (écran), 18→0 l. | « Plastique » → 104 ms (écran), 54→0 l. | « Plastique-140 » → 106 ms (écran), 22→0 l. | « Plastique-140 » → 107 ms (écran), 26→0 l. |
| direction | `/production?onglet=besoins` | « PP » → 105 ms (écran), 83→29 l. | « Plastique » → 109 ms (écran), 267→36 l. | « Plastique-140 » → 104 ms (écran), 88→1 l. | « Plastique-140 » → 104 ms (écran), 92→1 l. |
| direction | `/production/besoins/1` | « PP » → 104 ms (écran), 87→33 l. | — | — | — |
| direction | `/plan-achat?onglet=fournisseurs` | « HASIRCI » → 104 ms (écran), 12→1 l. | « HASIRCI » → 105 ms (écran), 0→0 l. | « HASIRCI » → 105 ms (écran), 2→0 l. | « HASIRCI » → 105 ms (écran), 5→1 l. |
| direction | `/plan-achat?onglet=references` | « HASIRCI » → 105 ms (écran), 83→24 l. | « HASIRCI » → 105 ms (écran), 0→0 l. | « HASIRCI » → 105 ms (écran), 3→0 l. | « HASIRCI » → 105 ms (écran), 9→1 l. |
| direction | `/plan-achat/preparer/1` | « HASIRCI » → 105 ms (écran), 36→25 l. | « HASIRCI » → 105 ms (écran), 0→0 l. | « HASIRCI » → 105 ms (écran), 2→0 l. | « HASIRCI » → 104 ms (écran), 6→2 l. |
| direction | `/commandes?onglet=brouillon` | « HASIRCI » → 104 ms (serveur), 0→0 l. | « HASIRCI » → 394 ms (serveur), 0→0 l. | « HASIRCI » → 106 ms (serveur), 0→0 l. | « HASIRCI » → 106 ms (serveur), 0→0 l. |
| direction | `/commandes?onglet=a_approuver` | « HASIRCI » → 105 ms (serveur), 0→0 l. | « HASIRCI » → 353 ms (serveur), 0→0 l. | « HASIRCI » → 108 ms (serveur), 0→0 l. | « HASIRCI » → 106 ms (serveur), 0→0 l. |
| direction | `/commandes?onglet=envoyee` | « HASIRCI » → 104 ms (serveur), 0→0 l. | « HASIRCI » → 355 ms (serveur), 0→0 l. | « HASIRCI » → 110 ms (serveur), 3→1 l. | « HASIRCI » → 105 ms (serveur), 0→0 l. |
| direction | `/commandes?onglet=confirmee` | « HASIRCI » → 104 ms (serveur), 0→0 l. | « HASIRCI » → 1 045 ms (serveur), 500→300 l. | « HASIRCI » → 105 ms (serveur), 26→2 l. | « HASIRCI » → 104 ms (serveur), 56→8 l. |
| direction | `/commandes?onglet=clos` | « HASIRCI » → 105 ms (serveur), 0→0 l. | « HASIRCI » → 1 770 ms (serveur), 500→500 l. | « HASIRCI » → 108 ms (serveur), 51→6 l. | « HASIRCI » → 105 ms (serveur), 214→31 l. |
| direction | `/commandes/nouvelle` | « HASIRCI » → 104 ms (serveur), 12→12 l. | « HASIRCI » → 1 054 ms (serveur), 500→300 l. | « HASIRCI » → 104 ms (serveur), 5→3 l. | « HASIRCI » → 106 ms (serveur), 61→13 l. |
| direction | `/receptions?onglet=brouillon` | « HASIRCI » → 105 ms (serveur), 0→0 l. | « HASIRCI » → 646 ms (serveur), 30→30 l. | « HASIRCI » → 106 ms (serveur), 1→0 l. | « HASIRCI » → 105 ms (serveur), 0→0 l. |
| direction | `/receptions?onglet=validee` | « HASIRCI » → 105 ms (serveur), 0→0 l. | « HASIRCI » → 2 382 ms (serveur), 500→500 l. | « HASIRCI » → 105 ms (serveur), 88→8 l. | « HASIRCI » → 106 ms (serveur), 258→44 l. |
| direction | `/receptions?onglet=annulee` | « HASIRCI » → 104 ms (serveur), 0→0 l. | « HASIRCI » → 604 ms (serveur), 0→0 l. | « HASIRCI » → 105 ms (serveur), 0→0 l. | « HASIRCI » → 105 ms (serveur), 0→0 l. |
| direction | `/receptions?onglet=reclamations` | « HASIRCI » → 104 ms (serveur), 0→0 l. | « HASIRCI » → 604 ms (serveur), 0→0 l. | « HASIRCI » → 105 ms (serveur), 0→0 l. | « HASIRCI » → 108 ms (serveur), 0→0 l. |
| direction | `/receptions?onglet=bobines` | « HASIRCI » → 105 ms (serveur), 0→0 l. | « HASIRCI » → 603 ms (serveur), 282→72 l. | « HASIRCI » → 104 ms (serveur), 59→24 l. | « HASIRCI » → 105 ms (serveur), 62→25 l. |
| direction | `/receptions?onglet=pesees` | « HASIRCI » → 353 ms (serveur), 0→0 l. | « HASIRCI » → 4 100 ms (serveur), 500→500 l. | « HASIRCI » → 398 ms (serveur), 236→48 l. | « HASIRCI » → 442 ms (serveur), 500→132 l. |
| direction | `/receptions/nouvelle` | « HASIRCI » → 104 ms (serveur), 0→0 l. | « HASIRCI » → 773 ms (serveur), 30→30 l. | « HASIRCI » → 105 ms (serveur), 1→8 l. | « HASIRCI » → 105 ms (serveur), 258→44 l. |
| direction | `/reclamations/nouvelle` | « PP » → 104 ms (serveur), 0→0 l. | « Plastique » → 2 541 ms (serveur), 30→500 l. | « Plastique-140 » → 104 ms (serveur), 1→12 l. | « Plastique-140 » → 107 ms (serveur), 258→49 l. |
| direction | `/importations?onglet=ouverts` | « PP » → 104 ms (serveur), 0→0 l. | « Plastique » → 313 ms (serveur), 500→30 l. | « Plastique-140 » → 104 ms (serveur), 0→0 l. | « Plastique-140 » → 106 ms (serveur), 1→0 l. |
| direction | `/importations?onglet=clos` | « PP » → 104 ms (serveur), 0→0 l. | « Plastique » → 853 ms (serveur), 500→0 l. | « Plastique-140 » → 106 ms (serveur), 54→0 l. | « Plastique-140 » → 105 ms (serveur), 155→0 l. |
| direction | `/dossiers/nouveau?onglet=facture` | « PP » → 102 ms (écran), 0→0 l. | « Plastique » → 106 ms (écran), 500→500 l. | « Plastique-140 » → 103 ms (écran), 2→2 l. | « Plastique-140 » → 102 ms (écran), 5→5 l. |
| direction | `/dossiers/nouveau?onglet=main` | « PP » → 103 ms (écran), 0→0 l. | « Plastique » → 107 ms (écran), 500→500 l. | « Plastique-140 » → 102 ms (écran), 0→0 l. | « Plastique-140 » → 102 ms (écran), 1→1 l. |
| direction | `/inventaire?onglet=passes` | « PP » → 104 ms (écran), 0→0 l. | « Plastique » → 105 ms (écran), 360→0 l. | « Plastique-140 » → 105 ms (écran), 25→0 l. | « Plastique-140 » → 105 ms (écran), 56→0 l. |
| direction | `/operations?onglet=transfert` | « PP » → 104 ms (serveur), 0→0 l. | « Plastique » → 105 ms (serveur), 0→0 l. | « Plastique-140 » → 104 ms (serveur), 118→2 l. | « Plastique-140 » → 104 ms (serveur), 235→5 l. |
| direction | `/operations?onglet=retour_machine` | « PP » → 105 ms (serveur), 0→0 l. | « Plastique » → 105 ms (serveur), 0→0 l. | « Plastique-140 » → 105 ms (serveur), 192→0 l. | « Plastique-140 » → 105 ms (serveur), 362→0 l. |
| direction | `/operations?onglet=ouverture` | « PP » → 105 ms (serveur), 0→0 l. | « Plastique » → 104 ms (serveur), 0→0 l. | « Plastique-140 » → 105 ms (serveur), 5→1 l. | « Plastique-140 » → 105 ms (serveur), 5→1 l. |
| direction | `/operations?onglet=ajustement` | « PP » → 104 ms (serveur), 0→0 l. | « Plastique » → 106 ms (serveur), 0→0 l. | « Plastique-140 » → 105 ms (serveur), 7→0 l. | « Plastique-140 » → 105 ms (serveur), 16→0 l. |
| direction | `/operations?onglet=retour_fournisseur` | « PP » → 105 ms (serveur), 0→0 l. | « Plastique » → 105 ms (serveur), 0→0 l. | « Plastique-140 » → 105 ms (serveur), 9→0 l. | « Plastique-140 » → 105 ms (serveur), 16→0 l. |
| direction | `/operations/nouvelle?type=transfert` | « PP » → 104 ms (serveur), 0→0 l. | « Plastique » → 105 ms (serveur), 0→0 l. | « Plastique-140 » → 104 ms (serveur), 118→2 l. | « Plastique-140 » → 104 ms (serveur), 235→5 l. |
| direction | `/operations/nouvelle?type=ajustement` | « PP » → 105 ms (serveur), 0→0 l. | « Plastique » → 106 ms (serveur), 0→0 l. | « Plastique-140 » → 105 ms (serveur), 7→0 l. | « Plastique-140 » → 104 ms (serveur), 16→0 l. |
| direction | `/catalogue?onglet=matieres` | « PP » → 105 ms (écran), 124→42 l. | « Plastique » → 105 ms (écran), 372→42 l. | « Plastique-140 » → 105 ms (écran), 127→1 l. | « Plastique-140 » → 105 ms (écran), 128→1 l. |
| direction | `/catalogue?onglet=classification` | « PP » → 105 ms (écran), 7→1 l. | « Plastique » → 105 ms (écran), 7→1 l. | « Plastique-140 » → 106 ms (écran), 7→0 l. | « Plastique-140 » → 105 ms (écran), 7→0 l. |
| direction | `/catalogue?onglet=fournisseurs` | « HASIRCI » → 105 ms (écran), 12→1 l. | « HASIRCI » → 105 ms (écran), 12→1 l. | « HASIRCI » → 103 ms (écran), 12→1 l. | « HASIRCI » → 105 ms (écran), 12→1 l. |
| direction | `/catalogue/tableur` | « PP » → 105 ms (écran), 124→42 l. | « Plastique » → 105 ms (écran), 372→42 l. | « Plastique-140 » → 105 ms (écran), 127→1 l. | « Plastique-140 » → 105 ms (écran), 128→1 l. |
| direction | `/matieres/nouvelle` | « PP » → 105 ms (écran), 124→42 l. | « Plastique » → 105 ms (écran), 372→42 l. | « Plastique-140 » → 105 ms (écran), 127→1 l. | « Plastique-140 » → 105 ms (écran), 128→1 l. |
| direction | `/matieres/1?onglet=classification` | « PP » → 105 ms (écran), 124→42 l. | — | — | — |
| direction | `/matieres/1?onglet=conditionnement` | « PP » → 105 ms (écran), 124→42 l. | — | — | — |
| direction | `/matieres/1?onglet=historique` | « PP » → 104 ms (écran), 124→42 l. | — | — | — |
| direction | `/matieres/1?onglet=achat` | « PP » → 105 ms (écran), 124→42 l. | — | — | — |
| direction | `/matieres/1?onglet=pieces` | « PP » → 105 ms (écran), 124→42 l. | — | — | — |
| direction | `/fournisseurs/nouveau` | « PP » → 104 ms (écran), 12→1 l. | « Plastique » → 104 ms (écran), 12→1 l. | « Plastique-140 » → 104 ms (écran), 12→0 l. | « Plastique-140 » → 104 ms (écran), 12→0 l. |
| direction | `/fournisseurs/1?onglet=fiche` | « PP » → 104 ms (écran), 12→1 l. | « Plastique » → 105 ms (écran), 12→1 l. | « Plastique-140 » → 104 ms (écran), 12→0 l. | « Plastique-140 » → 105 ms (écran), 12→0 l. |
| direction | `/fournisseurs/1?onglet=pieces` | « PP » → 105 ms (écran), 12→1 l. | « Plastique » → 105 ms (écran), 12→1 l. | « Plastique-140 » → 105 ms (écran), 12→0 l. | « Plastique-140 » → 106 ms (écran), 12→0 l. |
| direction | `/fournisseurs/1?onglet=historique` | « PP » → 105 ms (écran), 12→1 l. | « Plastique » → 106 ms (écran), 12→1 l. | « Plastique-140 » → 105 ms (écran), 12→0 l. | « Plastique-140 » → 106 ms (écran), 12→0 l. |
| direction | `/qualites?onglet=qualites` | « PP » → 110 ms (écran), 18→15 l. | « Plastique » → 106 ms (écran), 54→54 l. | « Plastique-140 » → 104 ms (écran), 22→8 l. | « Plastique-140 » → 105 ms (écran), 26→8 l. |
| direction | `/qualites?onglet=nomenclature` | « PP » → 104 ms (écran), 319→75 l. | « Plastique » → 105 ms (écran), 957→198 l. | « Plastique-140 » → 105 ms (écran), 342→8 l. | « Plastique-140 » → 106 ms (écran), 366→8 l. |
| direction | `/qualites/nouvelle` | « PP » → 105 ms (écran), 18→15 l. | « Plastique » → 105 ms (écran), 54→54 l. | « Plastique-140 » → 104 ms (écran), 22→8 l. | « Plastique-140 » → 106 ms (écran), 26→8 l. |
| direction | `/qualites/1?onglet=recette` | « PP » → 104 ms (écran), 45→42 l. | « Plastique » → 106 ms (écran), 81→81 l. | « Plastique-140 » → 103 ms (écran), 49→35 l. | « Plastique-140 » → 104 ms (écran), 53→35 l. |
| direction | `/qualites/1?onglet=plan` | « PP » → 104 ms (écran), 18→15 l. | « Plastique » → 106 ms (écran), 54→54 l. | « Plastique-140 » → 105 ms (écran), 22→8 l. | « Plastique-140 » → 105 ms (écran), 26→8 l. |
| direction | `/qualites/1?onglet=versions` | « PP » → 105 ms (écran), 19→16 l. | « Plastique » → 105 ms (écran), 55→55 l. | « Plastique-140 » → 103 ms (écran), 23→9 l. | « Plastique-140 » → 105 ms (écran), 27→9 l. |
| direction | `/qualites/1?onglet=historique` | « PP » → 105 ms (écran), 18→15 l. | « Plastique » → 106 ms (écran), 54→54 l. | « Plastique-140 » → 104 ms (écran), 22→8 l. | « Plastique-140 » → 105 ms (écran), 26→8 l. |
| direction | `/metiers` | « PP » → 105 ms (écran), 4→0 l. | « Plastique » → 105 ms (écran), 4→0 l. | « Plastique-140 » → 105 ms (écran), 4→0 l. | « Plastique-140 » → 106 ms (écran), 4→0 l. |
| direction | `/metiers/nouveau` | « PP » → 104 ms (écran), 4→0 l. | « Plastique » → 106 ms (écran), 4→0 l. | « Plastique-140 » → 105 ms (écran), 4→0 l. | « Plastique-140 » → 104 ms (écran), 4→0 l. |
| direction | `/metiers/2?onglet=fils` | « PP » → 105 ms (écran), 10→6 l. | — | « Plastique-140 » → 104 ms (écran), 16→12 l. | « Plastique-140 » → 105 ms (écran), 18→14 l. |
| direction | `/metiers/2?onglet=reglages` | « PP » → 105 ms (écran), 4→0 l. | — | « Plastique-140 » → 105 ms (écran), 4→0 l. | « Plastique-140 » → 105 ms (écran), 4→0 l. |
| direction | `/metiers/2?onglet=historique` | « PP » → 105 ms (écran), 4→0 l. | — | « Plastique-140 » → 105 ms (écran), 12→8 l. | « Plastique-140 » → 105 ms (écran), 22→18 l. |
| direction | `/analyse?onglet=valorisation` | « PP » → 105 ms (écran), 0→0 l. | « Plastique » → 106 ms (écran), 372→42 l. | « Plastique-140 » → 105 ms (écran), 87→1 l. | « Plastique-140 » → 105 ms (écran), 91→1 l. |
| direction | `/analyse?onglet=matrice` | « PP » → 105 ms (écran), 0→0 l. | « Plastique » → 107 ms (écran), 372→42 l. | « Plastique-140 » → 105 ms (écran), 87→1 l. | « Plastique-140 » → 104 ms (écran), 91→1 l. |
| direction | `/analyse?onglet=historique` | « PP » → 105 ms (écran), 0→0 l. | « Plastique » → 154 ms (écran), 43290→43290 l. | « Plastique-140 » → 105 ms (écran), 222→12 l. | « Plastique-140 » → 105 ms (écran), 572→67 l. |
| direction | `/analyse?onglet=opportunites` | « PP » → 104 ms (écran), 0→0 l. | « Plastique » → 106 ms (écran), 69→21 l. | « Plastique-140 » → 105 ms (écran), 8→1 l. | « Plastique-140 » → 105 ms (écran), 8→1 l. |
| direction | `/analyse?onglet=fournisseurs` | « PP » → 105 ms (écran), 0→0 l. | « Plastique » → 105 ms (écran), 12→1 l. | « Plastique-140 » → 105 ms (écran), 12→0 l. | « Plastique-140 » → 105 ms (écran), 12→0 l. |
| direction | `/analyse?onglet=revient` | « PP » → 354 ms (serveur), 0→0 l. | « Plastique » → 1 066 ms (serveur), 29→7 l. | « Plastique-140 » → 353 ms (serveur), 20→0 l. | « Plastique-140 » → 353 ms (serveur), 21→0 l. |
| direction | `/analyse?onglet=echeancier` | « PP » → 104 ms (serveur), 0→0 l. | « Plastique » → 127 ms (écran), 9480→9480 l. | « Plastique-140 » → 106 ms (serveur), 31→0 l. | « Plastique-140 » → 104 ms (serveur), 95→0 l. |
| direction | `/analyse?onglet=controles` | « PP » → 105 ms (écran), 6→1 l. | « Plastique » → 105 ms (écran), 12→0 l. | « Plastique-140 » → 105 ms (écran), 15→0 l. | « Plastique-140 » → 105 ms (écran), 14→0 l. |
| direction | `/analyse?onglet=production` | « PP » → 105 ms (écran), 0→0 l. | « Plastique » → 124 ms (écran), 9570→9570 l. | « Plastique-140 » → 108 ms (écran), 951→653 l. | « Plastique-140 » → 109 ms (écran), 1871→1237 l. |
| direction | `/reglages?onglet=postes` | « PP » → 104 ms (écran), 11→0 l. | « Plastique » → 106 ms (écran), 11→0 l. | « Plastique-140 » → 105 ms (écran), 15→0 l. | « Plastique-140 » → 104 ms (écran), 19→0 l. |
| direction | `/reglages?onglet=codes` | « PP » → 105 ms (écran), 0→0 l. | « Plastique » → 105 ms (écran), 0→0 l. | « Plastique-140 » → 105 ms (écran), 0→0 l. | « Plastique-140 » → 105 ms (écran), 0→0 l. |
| direction | `/administration?onglet=comptes` | « PP » → 104 ms (écran), 6→0 l. | « Plastique » → 105 ms (écran), 10→0 l. | « Plastique-140 » → 105 ms (écran), 11→0 l. | « Plastique-140 » → 105 ms (écran), 11→0 l. |
| direction | `/administration?onglet=journal` | « PP » → 104 ms (serveur), 157→11 l. | « Plastique » → 960 ms (serveur), 500→500 l. | « Plastique-140 » → 440 ms (serveur), 500→1 l. | « Plastique-140 » → 521 ms (serveur), 500→11 l. |
| direction | `/administration?onglet=donnees` | « PP » → 108 ms (écran), 124→42 l. | « Plastique » → 113 ms (écran), 372→42 l. | « Plastique-140 » → 107 ms (écran), 128→1 l. | « Plastique-140 » → 107 ms (écran), 132→1 l. |
| achats | `/stock?onglet=matieres` | « PP » → 105 ms (écran), 124→42 l. | « Plastique » → 105 ms (écran), 372→42 l. | « Plastique-140 » → 105 ms (écran), 128→1 l. | « Plastique-140 » → 105 ms (écran), 132→1 l. |
| achats | `/stock?onglet=lots` | « PP » → 105 ms (écran), 0→0 l. | « LOM260920-17 » → 255 ms (écran), 20160→30 l. | « LOT-2027-001 » → 106 ms (écran), 313→6 l. | « G-281013-061 » → 108 ms (écran), 525→2 l. |
| achats | `/stock?onglet=mouvements` | « PP » → 352 ms (serveur), 0→0 l. | « Plastique » → 2 212 ms (serveur), 500→500 l. | « Plastique-140 » → 595 ms (serveur), 500→500 l. | « Plastique-140 » → 767 ms (serveur), 500→500 l. |
| achats | `/stock?onglet=ordres` | « PP » → 105 ms (écran), 0→0 l. | « Plastique » → 157 ms (écran), 9570→9570 l. | « Plastique-140 » → 109 ms (écran), 951→653 l. | « Plastique-140 » → 143 ms (écran), 1871→1237 l. |
| achats | `/stock?onglet=a-valider` | « PP » → 104 ms (écran), 0→0 l. | « Plastique » → 104 ms (écran), 60→0 l. | « Plastique-140 » → 104 ms (écran), 3→0 l. | « Plastique-140 » → 106 ms (écran), 0→0 l. |
| achats | `/stock/matieres/1` | « PP » → 105 ms (écran), 151→69 l. | — | — | — |
| achats | `/tracabilite?matiere=1` | « PP » → 103 ms (écran), 0→0 l. | — | — | — |
| achats | `/sorties?onglet=valide` | « PP » → 103 ms (serveur), 0→0 l. | « Plastique » → 8 157 ms (serveur), 500→500 l. | « Plastique-140 » → 491 ms (serveur), 500→500 l. | « Plastique-140 » → 844 ms (serveur), 500→500 l. |
| achats | `/sorties?onglet=brouillon` | « PP » → 104 ms (serveur), 0→0 l. | « Plastique » → 361 ms (serveur), 30→30 l. | « Plastique-140 » → 106 ms (serveur), 1→0 l. | « Plastique-140 » → 106 ms (serveur), 0→0 l. |
| achats | `/sorties?onglet=annule` | « PP » → 104 ms (serveur), 0→0 l. | « Plastique » → 272 ms (serveur), 0→0 l. | « Plastique-140 » → 105 ms (serveur), 34→25 l. | « Plastique-140 » → 446 ms (serveur), 78→52 l. |
| achats | `/production?onglet=plan` | « PP » → 105 ms (écran), 18→0 l. | « Plastique » → 106 ms (écran), 54→0 l. | « Plastique-140 » → 106 ms (écran), 22→0 l. | « Plastique-140 » → 106 ms (écran), 26→0 l. |
| achats | `/production?onglet=glissant` | « PP » → 105 ms (écran), 18→0 l. | « Plastique » → 105 ms (écran), 54→0 l. | « Plastique-140 » → 105 ms (écran), 22→0 l. | « Plastique-140 » → 104 ms (écran), 26→0 l. |
| achats | `/production?onglet=realise` | « PP » → 104 ms (écran), 18→0 l. | « Plastique » → 105 ms (écran), 54→0 l. | « Plastique-140 » → 104 ms (écran), 22→0 l. | « Plastique-140 » → 106 ms (écran), 26→0 l. |
| achats | `/production?onglet=besoins` | « PP » → 104 ms (écran), 83→29 l. | « Plastique » → 107 ms (écran), 267→36 l. | « Plastique-140 » → 105 ms (écran), 88→1 l. | « Plastique-140 » → 106 ms (écran), 92→1 l. |
| achats | `/production/besoins/1` | « PP » → 105 ms (écran), 87→33 l. | — | — | — |
| achats | `/plan-achat?onglet=fournisseurs` | « HASIRCI » → 105 ms (écran), 12→1 l. | « HASIRCI » → 105 ms (écran), 0→0 l. | « HASIRCI » → 107 ms (écran), 2→0 l. | « HASIRCI » → 108 ms (écran), 5→1 l. |
| achats | `/plan-achat?onglet=references` | « HASIRCI » → 105 ms (écran), 83→24 l. | « HASIRCI » → 106 ms (écran), 0→0 l. | « HASIRCI » → 105 ms (écran), 3→0 l. | « HASIRCI » → 105 ms (écran), 9→1 l. |
| achats | `/plan-achat/preparer/1` | « HASIRCI » → 105 ms (écran), 36→25 l. | « HASIRCI » → 106 ms (écran), 0→0 l. | « HASIRCI » → 104 ms (écran), 2→0 l. | « HASIRCI » → 104 ms (écran), 6→2 l. |
| achats | `/commandes?onglet=brouillon` | « HASIRCI » → 105 ms (serveur), 0→0 l. | « HASIRCI » → 353 ms (serveur), 0→0 l. | « HASIRCI » → 105 ms (serveur), 0→0 l. | « HASIRCI » → 106 ms (serveur), 0→0 l. |
| achats | `/commandes?onglet=a_approuver` | « HASIRCI » → 105 ms (serveur), 0→0 l. | « HASIRCI » → 355 ms (serveur), 0→0 l. | « HASIRCI » → 104 ms (serveur), 0→0 l. | « HASIRCI » → 105 ms (serveur), 0→0 l. |
| achats | `/commandes?onglet=envoyee` | « HASIRCI » → 105 ms (serveur), 0→0 l. | « HASIRCI » → 354 ms (serveur), 0→0 l. | « HASIRCI » → 105 ms (serveur), 3→1 l. | « HASIRCI » → 105 ms (serveur), 0→0 l. |
| achats | `/commandes?onglet=confirmee` | « HASIRCI » → 103 ms (serveur), 0→0 l. | « HASIRCI » → 1 417 ms (serveur), 500→300 l. | « HASIRCI » → 104 ms (serveur), 26→2 l. | « HASIRCI » → 105 ms (serveur), 56→8 l. |
| achats | `/commandes?onglet=clos` | « HASIRCI » → 105 ms (serveur), 0→0 l. | « HASIRCI » → 1 407 ms (serveur), 500→500 l. | « HASIRCI » → 105 ms (serveur), 51→6 l. | « HASIRCI » → 106 ms (serveur), 214→31 l. |
| achats | `/commandes/nouvelle` | « HASIRCI » → 105 ms (serveur), 12→12 l. | « HASIRCI » → 1 077 ms (serveur), 500→300 l. | « HASIRCI » → 105 ms (serveur), 5→3 l. | « HASIRCI » → 106 ms (serveur), 61→13 l. |
| achats | `/receptions?onglet=brouillon` | « HASIRCI » → 105 ms (serveur), 0→0 l. | « HASIRCI » → 643 ms (serveur), 30→30 l. | « HASIRCI » → 105 ms (serveur), 1→0 l. | « HASIRCI » → 105 ms (serveur), 0→0 l. |
| achats | `/receptions?onglet=validee` | « HASIRCI » → 104 ms (serveur), 0→0 l. | « HASIRCI » → 2 097 ms (serveur), 500→500 l. | « HASIRCI » → 105 ms (serveur), 88→8 l. | « HASIRCI » → 106 ms (serveur), 258→44 l. |
| achats | `/receptions?onglet=annulee` | « HASIRCI » → 104 ms (serveur), 0→0 l. | « HASIRCI » → 603 ms (serveur), 0→0 l. | « HASIRCI » → 105 ms (serveur), 0→0 l. | « HASIRCI » → 106 ms (serveur), 0→0 l. |
| achats | `/receptions?onglet=reclamations` | « HASIRCI » → 105 ms (serveur), 0→0 l. | « HASIRCI » → 563 ms (serveur), 0→0 l. | « HASIRCI » → 104 ms (serveur), 0→0 l. | « HASIRCI » → 106 ms (serveur), 0→0 l. |
| achats | `/receptions?onglet=bobines` | « HASIRCI » → 105 ms (serveur), 0→0 l. | « HASIRCI » → 606 ms (serveur), 282→72 l. | « HASIRCI » → 105 ms (serveur), 59→24 l. | « HASIRCI » → 106 ms (serveur), 62→25 l. |
| achats | `/receptions?onglet=pesees` | « HASIRCI » → 351 ms (serveur), 0→0 l. | « HASIRCI » → 4 702 ms (serveur), 500→500 l. | « HASIRCI » → 400 ms (serveur), 236→48 l. | « HASIRCI » → 539 ms (serveur), 500→132 l. |
| achats | `/receptions/nouvelle` | « HASIRCI » → 105 ms (serveur), 0→0 l. | « HASIRCI » → 604 ms (serveur), 30→30 l. | « HASIRCI » → 104 ms (serveur), 1→8 l. | « HASIRCI » → 106 ms (serveur), 258→44 l. |
| achats | `/reclamations/nouvelle` | « PP » → 104 ms (serveur), 0→0 l. | « Plastique » → 2 961 ms (serveur), 30→500 l. | « Plastique-140 » → 104 ms (serveur), 1→12 l. | « Plastique-140 » → 108 ms (serveur), 258→49 l. |
| achats | `/importations?onglet=ouverts` | « PP » → 105 ms (serveur), 0→0 l. | « Plastique » → 278 ms (serveur), 500→30 l. | « Plastique-140 » → 106 ms (serveur), 0→0 l. | « Plastique-140 » → 106 ms (serveur), 1→0 l. |
| achats | `/importations?onglet=clos` | « PP » → 104 ms (serveur), 0→0 l. | « Plastique » → 853 ms (serveur), 500→0 l. | « Plastique-140 » → 105 ms (serveur), 54→0 l. | « Plastique-140 » → 110 ms (serveur), 155→0 l. |
| achats | `/dossiers/nouveau?onglet=facture` | « PP » → 103 ms (écran), 0→0 l. | « Plastique » → 106 ms (écran), 500→500 l. | « Plastique-140 » → 103 ms (écran), 2→2 l. | « Plastique-140 » → 104 ms (écran), 5→5 l. |
| achats | `/dossiers/nouveau?onglet=main` | « PP » → 102 ms (écran), 0→0 l. | « Plastique » → 107 ms (écran), 500→500 l. | « Plastique-140 » → 103 ms (écran), 0→0 l. | « Plastique-140 » → 103 ms (écran), 1→1 l. |
| achats | `/inventaire?onglet=passes` | « PP » → 104 ms (écran), 0→0 l. | « Plastique » → 106 ms (écran), 360→0 l. | « Plastique-140 » → 104 ms (écran), 25→0 l. | « Plastique-140 » → 106 ms (écran), 56→0 l. |
| achats | `/operations?onglet=transfert` | « PP » → 103 ms (serveur), 0→0 l. | « Plastique » → 105 ms (serveur), 0→0 l. | « Plastique-140 » → 105 ms (serveur), 118→2 l. | « Plastique-140 » → 107 ms (serveur), 235→5 l. |
| achats | `/operations?onglet=retour_machine` | « PP » → 105 ms (serveur), 0→0 l. | « Plastique » → 105 ms (serveur), 0→0 l. | « Plastique-140 » → 105 ms (serveur), 192→0 l. | « Plastique-140 » → 106 ms (serveur), 362→0 l. |
| achats | `/operations?onglet=ouverture` | « PP » → 105 ms (serveur), 0→0 l. | « Plastique » → 106 ms (serveur), 0→0 l. | « Plastique-140 » → 104 ms (serveur), 5→1 l. | « Plastique-140 » → 106 ms (serveur), 5→1 l. |
| achats | `/operations?onglet=ajustement` | « PP » → 104 ms (serveur), 0→0 l. | « Plastique » → 105 ms (serveur), 0→0 l. | « Plastique-140 » → 105 ms (serveur), 7→0 l. | « Plastique-140 » → 105 ms (serveur), 16→0 l. |
| achats | `/operations?onglet=retour_fournisseur` | « PP » → 104 ms (serveur), 0→0 l. | « Plastique » → 105 ms (serveur), 0→0 l. | « Plastique-140 » → 105 ms (serveur), 9→0 l. | « Plastique-140 » → 105 ms (serveur), 16→0 l. |
| achats | `/operations/nouvelle?type=transfert` | « PP » → 104 ms (serveur), 0→0 l. | « Plastique » → 105 ms (serveur), 0→0 l. | « Plastique-140 » → 104 ms (serveur), 118→2 l. | « Plastique-140 » → 104 ms (serveur), 235→5 l. |
| achats | `/operations/nouvelle?type=ajustement` | « PP » → 104 ms (serveur), 0→0 l. | « Plastique » → 105 ms (serveur), 0→0 l. | « Plastique-140 » → 104 ms (serveur), 7→0 l. | « Plastique-140 » → 106 ms (serveur), 16→0 l. |
| achats | `/catalogue?onglet=matieres` | « PP » → 104 ms (écran), 124→42 l. | « Plastique » → 105 ms (écran), 372→42 l. | « Plastique-140 » → 105 ms (écran), 127→1 l. | « Plastique-140 » → 106 ms (écran), 128→1 l. |
| achats | `/catalogue?onglet=classification` | « PP » → 104 ms (écran), 7→1 l. | « Plastique » → 105 ms (écran), 7→1 l. | « Plastique-140 » → 105 ms (écran), 7→0 l. | « Plastique-140 » → 106 ms (écran), 7→0 l. |
| achats | `/catalogue?onglet=fournisseurs` | « HASIRCI » → 105 ms (écran), 12→1 l. | « HASIRCI » → 105 ms (écran), 12→1 l. | « HASIRCI » → 104 ms (écran), 12→1 l. | « HASIRCI » → 106 ms (écran), 12→1 l. |
| achats | `/catalogue/tableur` | « PP » → 105 ms (écran), 124→42 l. | « Plastique » → 105 ms (écran), 372→42 l. | « Plastique-140 » → 105 ms (écran), 127→1 l. | « Plastique-140 » → 105 ms (écran), 128→1 l. |
| achats | `/matieres/nouvelle` | « PP » → 104 ms (écran), 124→42 l. | « Plastique » → 105 ms (écran), 372→42 l. | « Plastique-140 » → 105 ms (écran), 127→1 l. | « Plastique-140 » → 106 ms (écran), 128→1 l. |
| achats | `/matieres/1?onglet=classification` | « PP » → 104 ms (écran), 124→42 l. | — | — | — |
| achats | `/matieres/1?onglet=conditionnement` | « PP » → 105 ms (écran), 124→42 l. | — | — | — |
| achats | `/matieres/1?onglet=historique` | « PP » → 106 ms (écran), 124→42 l. | — | — | — |
| achats | `/matieres/1?onglet=achat` | « PP » → 105 ms (écran), 124→42 l. | — | — | — |
| achats | `/matieres/1?onglet=pieces` | « PP » → 104 ms (écran), 124→42 l. | — | — | — |
| achats | `/fournisseurs/nouveau` | « PP » → 105 ms (écran), 12→1 l. | « Plastique » → 105 ms (écran), 12→1 l. | « Plastique-140 » → 105 ms (écran), 12→0 l. | « Plastique-140 » → 104 ms (écran), 12→0 l. |
| achats | `/fournisseurs/1?onglet=fiche` | « PP » → 105 ms (écran), 12→1 l. | « Plastique » → 104 ms (écran), 12→1 l. | « Plastique-140 » → 105 ms (écran), 12→0 l. | « Plastique-140 » → 105 ms (écran), 12→0 l. |
| achats | `/fournisseurs/1?onglet=pieces` | « PP » → 105 ms (écran), 12→1 l. | « Plastique » → 106 ms (écran), 12→1 l. | « Plastique-140 » → 105 ms (écran), 12→0 l. | « Plastique-140 » → 106 ms (écran), 12→0 l. |
| achats | `/fournisseurs/1?onglet=historique` | « PP » → 105 ms (écran), 12→1 l. | « Plastique » → 105 ms (écran), 12→1 l. | « Plastique-140 » → 105 ms (écran), 12→0 l. | « Plastique-140 » → 106 ms (écran), 12→0 l. |
| achats | `/qualites?onglet=qualites` | « PP » → 105 ms (écran), 18→15 l. | « Plastique » → 106 ms (écran), 54→54 l. | « Plastique-140 » → 105 ms (écran), 22→8 l. | « Plastique-140 » → 106 ms (écran), 26→8 l. |
| achats | `/qualites?onglet=nomenclature` | « PP » → 105 ms (écran), 319→75 l. | « Plastique » → 105 ms (écran), 957→198 l. | « Plastique-140 » → 105 ms (écran), 342→8 l. | « Plastique-140 » → 106 ms (écran), 366→8 l. |
| achats | `/qualites/1?onglet=recette` | « PP » → 104 ms (écran), 45→42 l. | « Plastique » → 105 ms (écran), 81→81 l. | « Plastique-140 » → 105 ms (écran), 49→35 l. | « Plastique-140 » → 107 ms (écran), 53→35 l. |
| achats | `/qualites/1?onglet=plan` | « PP » → 104 ms (écran), 18→15 l. | « Plastique » → 105 ms (écran), 54→54 l. | « Plastique-140 » → 105 ms (écran), 22→8 l. | « Plastique-140 » → 106 ms (écran), 26→8 l. |
| achats | `/qualites/1?onglet=versions` | « PP » → 104 ms (écran), 19→16 l. | « Plastique » → 106 ms (écran), 55→55 l. | « Plastique-140 » → 104 ms (écran), 23→9 l. | « Plastique-140 » → 105 ms (écran), 27→9 l. |
| achats | `/qualites/1?onglet=historique` | « PP » → 104 ms (écran), 18→15 l. | « Plastique » → 106 ms (écran), 54→54 l. | « Plastique-140 » → 104 ms (écran), 22→8 l. | « Plastique-140 » → 104 ms (écran), 26→8 l. |
| achats | `/metiers` | « PP » → 104 ms (écran), 4→0 l. | « Plastique » → 106 ms (écran), 4→0 l. | « Plastique-140 » → 105 ms (écran), 4→0 l. | « Plastique-140 » → 106 ms (écran), 4→0 l. |
| achats | `/metiers/2?onglet=fils` | « PP » → 105 ms (écran), 10→6 l. | — | « Plastique-140 » → 105 ms (écran), 16→12 l. | « Plastique-140 » → 104 ms (écran), 18→14 l. |
| achats | `/metiers/2?onglet=reglages` | « PP » → 103 ms (écran), 4→0 l. | — | « Plastique-140 » → 105 ms (écran), 4→0 l. | « Plastique-140 » → 105 ms (écran), 4→0 l. |
| achats | `/metiers/2?onglet=historique` | « PP » → 104 ms (écran), 4→0 l. | — | « Plastique-140 » → 105 ms (écran), 12→8 l. | « Plastique-140 » → 105 ms (écran), 22→18 l. |
| achats | `/analyse?onglet=valorisation` | « PP » → 105 ms (écran), 0→0 l. | « Plastique » → 106 ms (écran), 372→42 l. | « Plastique-140 » → 105 ms (écran), 87→1 l. | « Plastique-140 » → 105 ms (écran), 91→1 l. |
| achats | `/analyse?onglet=matrice` | « PP » → 105 ms (écran), 0→0 l. | « Plastique » → 108 ms (écran), 372→42 l. | « Plastique-140 » → 104 ms (écran), 87→1 l. | « Plastique-140 » → 107 ms (écran), 91→1 l. |
| achats | `/analyse?onglet=historique` | « PP » → 105 ms (écran), 0→0 l. | « Plastique » → 153 ms (écran), 43290→43290 l. | « Plastique-140 » → 105 ms (écran), 222→12 l. | « Plastique-140 » → 106 ms (écran), 572→67 l. |
| achats | `/analyse?onglet=opportunites` | « PP » → 104 ms (écran), 0→0 l. | « Plastique » → 106 ms (écran), 69→21 l. | « Plastique-140 » → 105 ms (écran), 8→1 l. | « Plastique-140 » → 106 ms (écran), 8→1 l. |
| achats | `/analyse?onglet=fournisseurs` | « PP » → 104 ms (écran), 0→0 l. | « Plastique » → 105 ms (écran), 12→1 l. | « Plastique-140 » → 105 ms (écran), 12→0 l. | « Plastique-140 » → 104 ms (écran), 12→0 l. |
| achats | `/analyse?onglet=revient` | « PP » → 352 ms (serveur), 0→0 l. | « Plastique » → 743 ms (serveur), 29→7 l. | « Plastique-140 » → 105 ms (serveur), 20→0 l. | « Plastique-140 » → 359 ms (serveur), 21→0 l. |
| achats | `/analyse?onglet=echeancier` | « PP » → 105 ms (serveur), 0→0 l. | « Plastique » → 129 ms (écran), 9480→9480 l. | « Plastique-140 » → 104 ms (serveur), 31→0 l. | « Plastique-140 » → 106 ms (serveur), 95→0 l. |
| achats | `/analyse?onglet=controles` | « PP » → 105 ms (écran), 6→1 l. | « Plastique » → 105 ms (écran), 12→0 l. | « Plastique-140 » → 106 ms (écran), 15→0 l. | « Plastique-140 » → 106 ms (écran), 14→0 l. |
| achats | `/analyse?onglet=production` | « PP » → 105 ms (écran), 0→0 l. | « Plastique » → 125 ms (écran), 9570→9570 l. | « Plastique-140 » → 107 ms (écran), 951→653 l. | « Plastique-140 » → 111 ms (écran), 1871→1237 l. |
| achats | `/reglages?onglet=postes` | « PP » → 106 ms (écran), 11→0 l. | « Plastique » → 105 ms (écran), 11→0 l. | « Plastique-140 » → 106 ms (écran), 15→0 l. | « Plastique-140 » → 104 ms (écran), 19→0 l. |
| achats | `/reglages?onglet=codes` | « PP » → 105 ms (écran), 0→0 l. | « Plastique » → 103 ms (écran), 0→0 l. | « Plastique-140 » → 105 ms (écran), 0→0 l. | « Plastique-140 » → 106 ms (écran), 0→0 l. |
| alimentation | `/stock?onglet=matieres` | « PP » → 105 ms (écran), 124→42 l. | « Plastique » → 106 ms (écran), 372→42 l. | « Plastique-140 » → 105 ms (écran), 128→1 l. | « Plastique-140 » → 106 ms (écran), 132→1 l. |
| alimentation | `/stock?onglet=lots` | « PP » → 104 ms (écran), 0→0 l. | « LOM260920-17 » → 276 ms (écran), 20160→30 l. | « LOT-2027-001 » → 106 ms (écran), 313→6 l. | « G-281013-061 » → 110 ms (écran), 525→2 l. |
| alimentation | `/stock?onglet=mouvements` | « PP » → 352 ms (serveur), 0→0 l. | « Plastique » → 1 773 ms (serveur), 500→500 l. | « Plastique-140 » → 573 ms (serveur), 500→500 l. | « Plastique-140 » → 711 ms (serveur), 500→500 l. |
| alimentation | `/stock?onglet=ordres` | « PP » → 105 ms (écran), 0→0 l. | « Plastique » → 182 ms (écran), 9570→9570 l. | « Plastique-140 » → 111 ms (écran), 951→653 l. | « Plastique-140 » → 117 ms (écran), 1871→1237 l. |
| alimentation | `/stock?onglet=a-valider` | « PP » → 116 ms (écran), 0→0 l. | « Plastique » → 105 ms (écran), 30→0 l. | « Plastique-140 » → 105 ms (écran), 2→0 l. | « Plastique-140 » → 106 ms (écran), 0→0 l. |
| alimentation | `/stock/matieres/1` | « PP » → 104 ms (écran), 147→65 l. | — | — | — |
| alimentation | `/tracabilite?matiere=1` | « PP » → 104 ms (écran), 0→0 l. | — | — | — |
| alimentation | `/sorties?onglet=valide` | « PP » → 104 ms (serveur), 0→0 l. | « Plastique » → 9 085 ms (serveur), 500→500 l. | « Plastique-140 » → 664 ms (serveur), 500→500 l. | « Plastique-140 » → 993 ms (serveur), 500→500 l. |
| alimentation | `/sorties?onglet=brouillon` | « PP » → 104 ms (serveur), 0→0 l. | « Plastique » → 357 ms (serveur), 30→30 l. | « Plastique-140 » → 106 ms (serveur), 1→0 l. | « Plastique-140 » → 106 ms (serveur), 0→0 l. |
| alimentation | `/sorties?onglet=annule` | « PP » → 111 ms (serveur), 0→0 l. | « Plastique » → 271 ms (serveur), 0→0 l. | « Plastique-140 » → 147 ms (serveur), 34→25 l. | « Plastique-140 » → 321 ms (serveur), 78→52 l. |
| alimentation | `/ordres/nouveau` | « PP » → 105 ms (serveur), 1→1 l. | « Plastique » → 10 315 ms (serveur), 501→501 l. | « Plastique-140 » → 524 ms (serveur), 501→501 l. | « Plastique-140 » → 1 099 ms (serveur), 501→501 l. |
| alimentation | `/production?onglet=plan` | « PP » → 104 ms (écran), 18→0 l. | « Plastique » → 104 ms (écran), 54→0 l. | « Plastique-140 » → 105 ms (écran), 22→0 l. | « Plastique-140 » → 106 ms (écran), 26→0 l. |
| alimentation | `/production?onglet=glissant` | « PP » → 105 ms (écran), 18→0 l. | « Plastique » → 106 ms (écran), 54→0 l. | « Plastique-140 » → 105 ms (écran), 22→0 l. | « Plastique-140 » → 106 ms (écran), 26→0 l. |
| alimentation | `/production?onglet=realise` | « PP » → 105 ms (écran), 18→0 l. | « Plastique » → 104 ms (écran), 54→0 l. | « Plastique-140 » → 105 ms (écran), 22→0 l. | « Plastique-140 » → 107 ms (écran), 26→0 l. |
| alimentation | `/production?onglet=besoins` | « PP » → 107 ms (écran), 83→29 l. | « Plastique » → 106 ms (écran), 267→36 l. | « Plastique-140 » → 105 ms (écran), 88→1 l. | « Plastique-140 » → 106 ms (écran), 92→1 l. |
| alimentation | `/production/besoins/1` | « PP » → 107 ms (écran), 87→33 l. | — | — | — |
| alimentation | `/operations?onglet=transfert` | « PP » → 113 ms (serveur), 0→0 l. | « Plastique » → 106 ms (serveur), 0→0 l. | « Plastique-140 » → 105 ms (serveur), 118→2 l. | « Plastique-140 » → 105 ms (serveur), 235→5 l. |
| alimentation | `/operations?onglet=retour_machine` | « PP » → 112 ms (serveur), 0→0 l. | « Plastique » → 106 ms (serveur), 0→0 l. | « Plastique-140 » → 104 ms (serveur), 192→0 l. | « Plastique-140 » → 104 ms (serveur), 362→0 l. |
| alimentation | `/operations/nouvelle?type=transfert` | « PP » → 111 ms (serveur), 0→0 l. | « Plastique » → 105 ms (serveur), 0→0 l. | « Plastique-140 » → 105 ms (serveur), 118→2 l. | « Plastique-140 » → 104 ms (serveur), 235→5 l. |
| alimentation | `/catalogue?onglet=matieres` | « PP » → 109 ms (écran), 124→42 l. | « Plastique » → 106 ms (écran), 372→42 l. | « Plastique-140 » → 105 ms (écran), 127→1 l. | « Plastique-140 » → 104 ms (écran), 128→1 l. |
| alimentation | `/matieres/1?onglet=classification` | « PP » → 105 ms (écran), 124→42 l. | — | — | — |
| alimentation | `/matieres/1?onglet=conditionnement` | « PP » → 109 ms (écran), 124→42 l. | — | — | — |
| alimentation | `/matieres/1?onglet=historique` | « PP » → 110 ms (écran), 124→42 l. | — | — | — |
| alimentation | `/qualites?onglet=qualites` | « PP » → 112 ms (écran), 18→15 l. | « Plastique » → 105 ms (écran), 54→54 l. | « Plastique-140 » → 105 ms (écran), 22→8 l. | « Plastique-140 » → 105 ms (écran), 26→8 l. |
| alimentation | `/qualites?onglet=nomenclature` | « PP » → 109 ms (écran), 319→75 l. | « Plastique » → 109 ms (écran), 957→198 l. | « Plastique-140 » → 105 ms (écran), 342→8 l. | « Plastique-140 » → 106 ms (écran), 366→8 l. |
| alimentation | `/qualites/1?onglet=recette` | « PP » → 110 ms (écran), 45→42 l. | « Plastique » → 106 ms (écran), 81→81 l. | « Plastique-140 » → 107 ms (écran), 49→35 l. | « Plastique-140 » → 105 ms (écran), 53→35 l. |
| alimentation | `/qualites/1?onglet=plan` | « PP » → 111 ms (écran), 18→15 l. | « Plastique » → 105 ms (écran), 54→54 l. | « Plastique-140 » → 104 ms (écran), 22→8 l. | « Plastique-140 » → 105 ms (écran), 26→8 l. |
| alimentation | `/qualites/1?onglet=versions` | « PP » → 114 ms (écran), 19→16 l. | « Plastique » → 106 ms (écran), 55→55 l. | « Plastique-140 » → 104 ms (écran), 23→9 l. | « Plastique-140 » → 105 ms (écran), 27→9 l. |
| alimentation | `/qualites/1?onglet=historique` | « PP » → 111 ms (écran), 18→15 l. | « Plastique » → 105 ms (écran), 54→54 l. | « Plastique-140 » → 104 ms (écran), 22→8 l. | « Plastique-140 » → 104 ms (écran), 26→8 l. |
| alimentation | `/metiers` | « PP » → 114 ms (écran), 4→0 l. | « Plastique » → 106 ms (écran), 4→0 l. | « Plastique-140 » → 105 ms (écran), 4→0 l. | « Plastique-140 » → 104 ms (écran), 4→0 l. |
| alimentation | `/metiers/2?onglet=fils` | « PP » → 112 ms (écran), 10→6 l. | — | « Plastique-140 » → 105 ms (écran), 16→12 l. | « Plastique-140 » → 105 ms (écran), 18→14 l. |
| alimentation | `/metiers/2?onglet=reglages` | « PP » → 111 ms (écran), 4→0 l. | — | « Plastique-140 » → 105 ms (écran), 4→0 l. | « Plastique-140 » → 105 ms (écran), 4→0 l. |
| alimentation | `/metiers/2?onglet=historique` | « PP » → 112 ms (écran), 4→0 l. | — | « Plastique-140 » → 105 ms (écran), 12→8 l. | « Plastique-140 » → 105 ms (écran), 22→18 l. |
| alimentation | `/atelier/chercher` | « PP » → 105 ms (serveur), 0→0 l. | « LOM260920-17 » → 1 031 ms (serveur), 0→0 l. | « LOT-2027-001 » → 318 ms (serveur), 0→0 l. | « G-281013-061 » → 318 ms (serveur), 0→0 l. |
| direction | `/atelier/chercher` | « PP » → 104 ms (serveur), 0→0 l. | « LOM260920-17 » → 1 070 ms (serveur), 0→0 l. | « LOT-2027-001 » → 312 ms (serveur), 0→0 l. | « G-281013-061 » → 320 ms (serveur), 0→0 l. |
| direction | `/stock/matieres/111` | — | « Plastique » → 106 ms (écran), 397→67 l. | — | — |
| direction | `/lots/291565` | — | « Plastique » → 260 ms (écran), 20161→2941 l. | — | — |
| direction | `/tracabilite?lot=291565` | — | « Plastique » → 171 ms (écran), 9571→9571 l. | — | — |
| direction | `/tracabilite?matiere=111` | — | « Plastique » → 171 ms (écran), 11010→11010 l. | — | — |
| direction | `/ordres/29319` | — | « Plastique » → 7 918 ms (serveur), 546→546 l. | — | — |
| direction | `/ordres/29319/retour` | — | « Plastique » → 7 607 ms (serveur), 546→546 l. | — | — |
| direction | `/production/besoins/111` | — | « Plastique » → 107 ms (écran), 267→36 l. | — | — |
| direction | `/commandes/29330?onglet=lignes` | — | « HASIRCI » → 1 317 ms (serveur), 507→307 l. | — | — |
| direction | `/commandes/29330?onglet=prix` | — | « HASIRCI » → 1 037 ms (serveur), 507→307 l. | — | — |
| direction | `/commandes/29330?onglet=expedition` | — | « HASIRCI » → 1 280 ms (serveur), 500→300 l. | — | — |
| direction | `/commandes/29330?onglet=receptions` | — | « HASIRCI » → 1 345 ms (serveur), 501→301 l. | — | — |
| direction | `/commandes/29330?onglet=approbation` | — | « HASIRCI » → 1 292 ms (serveur), 507→307 l. | — | — |
| direction | `/commandes/29330?onglet=pieces` | — | « HASIRCI » → 1 535 ms (serveur), 500→300 l. | — | — |
| direction | `/commandes/29330?onglet=historique` | — | « HASIRCI » → 1 304 ms (serveur), 500→300 l. | — | — |
| direction | `/receptions/29321?onglet=lignes` | — | « HASIRCI » → 646 ms (serveur), 31→31 l. | — | — |
| direction | `/receptions/29321?onglet=reclamations` | — | « HASIRCI » → 607 ms (serveur), 30→30 l. | — | — |
| direction | `/receptions/29321?onglet=pieces` | — | « HASIRCI » → 603 ms (serveur), 30→30 l. | — | — |
| direction | `/receptions/29321?onglet=historique` | — | « HASIRCI » → 686 ms (serveur), 30→30 l. | — | — |
| direction | `/dossiers/2990?onglet=familles` | — | « Plastique » → 107 ms (écran), 507→507 l. | — | — |
| direction | `/dossiers/2990?onglet=marchandises` | — | « Plastique » → 106 ms (écran), 507→507 l. | — | — |
| direction | `/dossiers/2990?onglet=frais` | — | « Plastique » → 106 ms (écran), 504→504 l. | — | — |
| direction | `/dossiers/2990?onglet=echeancier` | — | « Plastique » → 108 ms (écran), 507→507 l. | — | — |
| direction | `/dossiers/2990?onglet=pieces` | — | « Plastique » → 106 ms (écran), 500→500 l. | — | — |
| direction | `/dossiers/2990?onglet=facture` | — | « Plastique » → 106 ms (écran), 507→507 l. | — | — |
| direction | `/dossiers/2990?onglet=historique` | — | « Plastique » → 107 ms (écran), 500→500 l. | — | — |
| direction | `/inventaires/2912?onglet=lots` | — | « Plastique » → 105 ms (écran), 366→6 l. | — | — |
| direction | `/inventaires/2912?onglet=pieces` | — | « Plastique » → 106 ms (écran), 360→0 l. | — | — |
| direction | `/inventaires/2912?onglet=historique` | — | « Plastique » → 106 ms (écran), 360→0 l. | — | — |
| direction | `/matieres/111?onglet=classification` | — | « Plastique » → 105 ms (écran), 372→42 l. | — | — |
| direction | `/matieres/111?onglet=conditionnement` | — | « Plastique » → 106 ms (écran), 372→42 l. | — | — |
| direction | `/matieres/111?onglet=historique` | — | « Plastique » → 105 ms (écran), 372→42 l. | — | — |
| direction | `/matieres/111?onglet=achat` | — | « Plastique » → 105 ms (écran), 372→42 l. | — | — |
| direction | `/matieres/111?onglet=pieces` | — | « Plastique » → 105 ms (écran), 372→42 l. | — | — |
| direction | `/metiers/1?onglet=fils` | — | « Plastique » → 106 ms (écran), 10→6 l. | — | — |
| direction | `/metiers/1?onglet=reglages` | — | « Plastique » → 105 ms (écran), 4→0 l. | — | — |
| direction | `/metiers/1?onglet=historique` | — | « Plastique » → 105 ms (écran), 4→0 l. | — | — |
| achats | `/stock/matieres/111` | — | « Plastique » → 106 ms (écran), 397→67 l. | — | — |
| achats | `/lots/291565` | — | « Plastique » → 271 ms (écran), 20161→2941 l. | — | — |
| achats | `/tracabilite?lot=291565` | — | « Plastique » → 156 ms (écran), 9571→9571 l. | — | — |
| achats | `/tracabilite?matiere=111` | — | « Plastique » → 163 ms (écran), 11010→11010 l. | — | — |
| achats | `/ordres/29319` | — | « Plastique » → 7 890 ms (serveur), 546→546 l. | — | — |
| achats | `/production/besoins/111` | — | « Plastique » → 107 ms (écran), 267→36 l. | — | — |
| achats | `/commandes/29330?onglet=lignes` | — | « HASIRCI » → 1 110 ms (serveur), 507→307 l. | — | — |
| achats | `/commandes/29330?onglet=prix` | — | « HASIRCI » → 1 420 ms (serveur), 507→307 l. | — | — |
| achats | `/commandes/29330?onglet=expedition` | — | « HASIRCI » → 1 455 ms (serveur), 500→300 l. | — | — |
| achats | `/commandes/29330?onglet=receptions` | — | « HASIRCI » → 1 461 ms (serveur), 501→301 l. | — | — |
| achats | `/commandes/29330?onglet=approbation` | — | « HASIRCI » → 1 085 ms (serveur), 507→307 l. | — | — |
| achats | `/commandes/29330?onglet=pieces` | — | « HASIRCI » → 1 093 ms (serveur), 500→300 l. | — | — |
| achats | `/commandes/29330?onglet=historique` | — | « HASIRCI » → 1 081 ms (serveur), 500→300 l. | — | — |
| achats | `/receptions/29321?onglet=lignes` | — | « HASIRCI » → 606 ms (serveur), 31→31 l. | — | — |
| achats | `/receptions/29321?onglet=reclamations` | — | « HASIRCI » → 645 ms (serveur), 30→30 l. | — | — |
| achats | `/receptions/29321?onglet=pieces` | — | « HASIRCI » → 606 ms (serveur), 30→30 l. | — | — |
| achats | `/receptions/29321?onglet=historique` | — | « HASIRCI » → 606 ms (serveur), 30→30 l. | — | — |
| achats | `/dossiers/2990?onglet=familles` | — | « Plastique » → 107 ms (écran), 507→507 l. | — | — |
| achats | `/dossiers/2990?onglet=marchandises` | — | « Plastique » → 106 ms (écran), 507→507 l. | — | — |
| achats | `/dossiers/2990?onglet=frais` | — | « Plastique » → 106 ms (écran), 504→504 l. | — | — |
| achats | `/dossiers/2990?onglet=echeancier` | — | « Plastique » → 107 ms (écran), 507→507 l. | — | — |
| achats | `/dossiers/2990?onglet=pieces` | — | « Plastique » → 107 ms (écran), 500→500 l. | — | — |
| achats | `/dossiers/2990?onglet=facture` | — | « Plastique » → 106 ms (écran), 507→507 l. | — | — |
| achats | `/dossiers/2990?onglet=historique` | — | « Plastique » → 107 ms (écran), 500→500 l. | — | — |
| achats | `/inventaires/2912?onglet=lots` | — | « Plastique » → 105 ms (écran), 366→6 l. | — | — |
| achats | `/inventaires/2912?onglet=pieces` | — | « Plastique » → 105 ms (écran), 360→0 l. | — | — |
| achats | `/inventaires/2912?onglet=historique` | — | « Plastique » → 105 ms (écran), 360→0 l. | — | — |
| achats | `/matieres/111?onglet=classification` | — | « Plastique » → 105 ms (écran), 372→42 l. | — | — |
| achats | `/matieres/111?onglet=conditionnement` | — | « Plastique » → 105 ms (écran), 372→42 l. | — | — |
| achats | `/matieres/111?onglet=historique` | — | « Plastique » → 105 ms (écran), 372→42 l. | — | — |
| achats | `/matieres/111?onglet=achat` | — | « Plastique » → 105 ms (écran), 372→42 l. | — | — |
| achats | `/matieres/111?onglet=pieces` | — | « Plastique » → 105 ms (écran), 372→42 l. | — | — |
| achats | `/metiers/1?onglet=fils` | — | « Plastique » → 106 ms (écran), 10→6 l. | — | — |
| achats | `/metiers/1?onglet=reglages` | — | « Plastique » → 106 ms (écran), 4→0 l. | — | — |
| achats | `/metiers/1?onglet=historique` | — | « Plastique » → 106 ms (écran), 4→0 l. | — | — |
| alimentation | `/stock/matieres/111` | — | « Plastique » → 104 ms (écran), 393→63 l. | — | — |
| alimentation | `/lots/291565` | — | « Plastique » → 286 ms (écran), 20161→2941 l. | — | — |
| alimentation | `/tracabilite?lot=291565` | — | « Plastique » → 185 ms (écran), 9571→9571 l. | — | — |
| alimentation | `/tracabilite?matiere=111` | — | « Plastique » → 196 ms (écran), 11010→11010 l. | — | — |
| alimentation | `/ordres/29319` | — | « Plastique » → 9 233 ms (serveur), 546→546 l. | — | — |
| alimentation | `/ordres/29319/retour` | — | « Plastique » → 8 353 ms (serveur), 546→546 l. | — | — |
| alimentation | `/production/besoins/111` | — | « Plastique » → 108 ms (écran), 267→36 l. | — | — |
| alimentation | `/matieres/111?onglet=classification` | — | « Plastique » → 107 ms (écran), 372→42 l. | — | — |
| alimentation | `/matieres/111?onglet=conditionnement` | — | « Plastique » → 108 ms (écran), 372→42 l. | — | — |
| alimentation | `/matieres/111?onglet=historique` | — | « Plastique » → 106 ms (écran), 372→42 l. | — | — |
| alimentation | `/metiers/1?onglet=fils` | — | « Plastique » → 105 ms (écran), 10→6 l. | — | — |
| alimentation | `/metiers/1?onglet=reglages` | — | « Plastique » → 105 ms (écran), 4→0 l. | — | — |
| alimentation | `/metiers/1?onglet=historique` | — | « Plastique » → 104 ms (écran), 4→0 l. | — | — |
| alimentation | `/atelier/retour` | — | « Plastique » → 6 002 ms (serveur), 0→0 l. | « Plastique-140 » → 739 ms (serveur), 0→0 l. | « Plastique-140 » → 1 036 ms (serveur), 0→0 l. |
| direction | `/atelier/retour` | — | « Plastique » → 5 921 ms (serveur), 0→0 l. | « Plastique-140 » → 642 ms (serveur), 0→0 l. | « Plastique-140 » → 908 ms (serveur), 0→0 l. |
| direction | `/stock/matieres/124` | — | — | « Plastique-140 » → 105 ms (écran), 160→33 l. | « Plastique-140 » → 104 ms (écran), 165→34 l. |
| direction | `/lots/353` | — | — | « Plastique-140 » → 106 ms (écran), 314→13 l. | — |
| direction | `/tracabilite?lot=353` | — | — | « Plastique-140 » → 109 ms (écran), 952→654 l. | — |
| direction | `/tracabilite?matiere=124` | — | — | « Plastique-140 » → 112 ms (écran), 1621→1323 l. | « Plastique-140 » → 175 ms (écran), 3295→2661 l. |
| direction | `/ordres/1087` | — | — | « Plastique-140 » → 677 ms (serveur), 511→511 l. | — |
| direction | `/ordres/1087/retour` | — | — | « Plastique-140 » → 594 ms (serveur), 511→511 l. | — |
| direction | `/production/besoins/124` | — | — | « Plastique-140 » → 105 ms (écran), 95→8 l. | « Plastique-140 » → 105 ms (écran), 99→8 l. |
| direction | `/commandes/85?onglet=lignes` | — | — | « HASIRCI » → 112 ms (serveur), 4→2 l. | — |
| direction | `/commandes/85?onglet=prix` | — | — | « HASIRCI » → 105 ms (serveur), 4→2 l. | — |
| direction | `/commandes/85?onglet=expedition` | — | — | « HASIRCI » → 105 ms (serveur), 3→1 l. | — |
| direction | `/commandes/85?onglet=receptions` | — | — | « HASIRCI » → 104 ms (serveur), 3→1 l. | — |
| direction | `/commandes/85?onglet=approbation` | — | — | « HASIRCI » → 104 ms (serveur), 4→2 l. | — |
| direction | `/commandes/85?onglet=pieces` | — | — | « HASIRCI » → 104 ms (serveur), 3→1 l. | — |
| direction | `/commandes/85?onglet=historique` | — | — | « HASIRCI » → 105 ms (serveur), 3→1 l. | — |
| direction | `/receptions/95?onglet=lignes` | — | — | « HASIRCI » → 105 ms (serveur), 2→9 l. | — |
| direction | `/receptions/95?onglet=reclamations` | — | — | « HASIRCI » → 105 ms (serveur), 1→8 l. | — |
| direction | `/receptions/95?onglet=pieces` | — | — | « HASIRCI » → 105 ms (serveur), 1→8 l. | — |
| direction | `/receptions/95?onglet=historique` | — | — | « HASIRCI » → 105 ms (serveur), 1→8 l. | — |
| direction | `/reclamations/10?onglet=reponse` | — | — | « Plastique-140 » → 104 ms (serveur), 1→12 l. | — |
| direction | `/reclamations/10?onglet=pieces` | — | — | « Plastique-140 » → 104 ms (serveur), 1→12 l. | — |
| direction | `/reclamations/10?onglet=historique` | — | — | « Plastique-140 » → 104 ms (serveur), 1→12 l. | — |
| direction | `/importations?onglet=rattacher` | — | — | « Plastique-140 » → 103 ms (écran), 2→0 l. | « Plastique-140 » → 102 ms (écran), 4→0 l. |
| direction | `/dossiers/58?onglet=familles` | — | — | « Plastique-140 » → 103 ms (écran), 56→56 l. | — |
| direction | `/dossiers/58?onglet=marchandises` | — | — | « Plastique-140 » → 103 ms (écran), 56→56 l. | — |
| direction | `/dossiers/58?onglet=frais` | — | — | « Plastique-140 » → 103 ms (écran), 59→59 l. | — |
| direction | `/dossiers/58?onglet=echeancier` | — | — | « Plastique-140 » → 103 ms (écran), 61→61 l. | — |
| direction | `/dossiers/58?onglet=pieces` | — | — | « Plastique-140 » → 103 ms (écran), 55→55 l. | — |
| direction | `/dossiers/58?onglet=facture` | — | — | « Plastique-140 » → 102 ms (écran), 56→56 l. | — |
| direction | `/dossiers/58?onglet=historique` | — | — | « Plastique-140 » → 103 ms (écran), 55→55 l. | — |
| direction | `/inventaires/26?onglet=lots` | — | — | « Plastique-140 » → 105 ms (écran), 28→3 l. | — |
| direction | `/inventaires/26?onglet=pieces` | — | — | « Plastique-140 » → 105 ms (écran), 25→0 l. | — |
| direction | `/inventaires/26?onglet=historique` | — | — | « Plastique-140 » → 105 ms (écran), 25→0 l. | — |
| direction | `/operations/337` | — | — | « Plastique-140 » → 105 ms (serveur), 119→3 l. | — |
| direction | `/matieres/124?onglet=classification` | — | — | « Plastique-140 » → 105 ms (écran), 127→1 l. | « Plastique-140 » → 105 ms (écran), 128→1 l. |
| direction | `/matieres/124?onglet=conditionnement` | — | — | « Plastique-140 » → 105 ms (écran), 127→1 l. | « Plastique-140 » → 105 ms (écran), 128→1 l. |
| direction | `/matieres/124?onglet=historique` | — | — | « Plastique-140 » → 104 ms (écran), 127→1 l. | « Plastique-140 » → 105 ms (écran), 128→1 l. |
| direction | `/matieres/124?onglet=achat` | — | — | « Plastique-140 » → 104 ms (écran), 127→1 l. | « Plastique-140 » → 104 ms (écran), 128→1 l. |
| direction | `/matieres/124?onglet=pieces` | — | — | « Plastique-140 » → 105 ms (écran), 127→1 l. | « Plastique-140 » → 104 ms (écran), 128→1 l. |
| achats | `/stock/matieres/124` | — | — | « Plastique-140 » → 106 ms (écran), 160→33 l. | « Plastique-140 » → 106 ms (écran), 165→34 l. |
| achats | `/lots/353` | — | — | « Plastique-140 » → 105 ms (écran), 314→13 l. | — |
| achats | `/tracabilite?lot=353` | — | — | « Plastique-140 » → 110 ms (écran), 952→654 l. | — |
| achats | `/tracabilite?matiere=124` | — | — | « Plastique-140 » → 113 ms (écran), 1621→1323 l. | « Plastique-140 » → 181 ms (écran), 3295→2661 l. |
| achats | `/ordres/1087` | — | — | « Plastique-140 » → 619 ms (serveur), 511→511 l. | — |
| achats | `/production/besoins/124` | — | — | « Plastique-140 » → 105 ms (écran), 95→8 l. | « Plastique-140 » → 106 ms (écran), 99→8 l. |
| achats | `/commandes/85?onglet=lignes` | — | — | « HASIRCI » → 105 ms (serveur), 4→2 l. | — |
| achats | `/commandes/85?onglet=prix` | — | — | « HASIRCI » → 105 ms (serveur), 4→2 l. | — |
| achats | `/commandes/85?onglet=expedition` | — | — | « HASIRCI » → 105 ms (serveur), 3→1 l. | — |
| achats | `/commandes/85?onglet=receptions` | — | — | « HASIRCI » → 105 ms (serveur), 3→1 l. | — |
| achats | `/commandes/85?onglet=approbation` | — | — | « HASIRCI » → 104 ms (serveur), 4→2 l. | — |
| achats | `/commandes/85?onglet=pieces` | — | — | « HASIRCI » → 105 ms (serveur), 3→1 l. | — |
| achats | `/commandes/85?onglet=historique` | — | — | « HASIRCI » → 104 ms (serveur), 3→1 l. | — |
| achats | `/receptions/95?onglet=lignes` | — | — | « HASIRCI » → 107 ms (serveur), 2→9 l. | — |
| achats | `/receptions/95?onglet=reclamations` | — | — | « HASIRCI » → 105 ms (serveur), 1→8 l. | — |
| achats | `/receptions/95?onglet=pieces` | — | — | « HASIRCI » → 104 ms (serveur), 1→8 l. | — |
| achats | `/receptions/95?onglet=historique` | — | — | « HASIRCI » → 105 ms (serveur), 1→8 l. | — |
| achats | `/reclamations/10?onglet=reponse` | — | — | « Plastique-140 » → 105 ms (serveur), 1→12 l. | — |
| achats | `/reclamations/10?onglet=pieces` | — | — | « Plastique-140 » → 105 ms (serveur), 1→12 l. | — |
| achats | `/reclamations/10?onglet=historique` | — | — | « Plastique-140 » → 105 ms (serveur), 1→12 l. | — |
| achats | `/importations?onglet=rattacher` | — | — | « Plastique-140 » → 102 ms (écran), 2→0 l. | « Plastique-140 » → 104 ms (écran), 4→0 l. |
| achats | `/dossiers/58?onglet=familles` | — | — | « Plastique-140 » → 102 ms (écran), 56→56 l. | — |
| achats | `/dossiers/58?onglet=marchandises` | — | — | « Plastique-140 » → 103 ms (écran), 56→56 l. | — |
| achats | `/dossiers/58?onglet=frais` | — | — | « Plastique-140 » → 102 ms (écran), 59→59 l. | — |
| achats | `/dossiers/58?onglet=echeancier` | — | — | « Plastique-140 » → 103 ms (écran), 61→61 l. | — |
| achats | `/dossiers/58?onglet=pieces` | — | — | « Plastique-140 » → 103 ms (écran), 55→55 l. | — |
| achats | `/dossiers/58?onglet=facture` | — | — | « Plastique-140 » → 103 ms (écran), 56→56 l. | — |
| achats | `/dossiers/58?onglet=historique` | — | — | « Plastique-140 » → 102 ms (écran), 55→55 l. | — |
| achats | `/inventaires/26?onglet=lots` | — | — | « Plastique-140 » → 105 ms (écran), 28→3 l. | — |
| achats | `/inventaires/26?onglet=pieces` | — | — | « Plastique-140 » → 104 ms (écran), 25→0 l. | — |
| achats | `/inventaires/26?onglet=historique` | — | — | « Plastique-140 » → 105 ms (écran), 25→0 l. | — |
| achats | `/operations/337` | — | — | « Plastique-140 » → 106 ms (serveur), 119→3 l. | — |
| achats | `/matieres/124?onglet=classification` | — | — | « Plastique-140 » → 104 ms (écran), 127→1 l. | « Plastique-140 » → 106 ms (écran), 128→1 l. |
| achats | `/matieres/124?onglet=conditionnement` | — | — | « Plastique-140 » → 105 ms (écran), 127→1 l. | « Plastique-140 » → 106 ms (écran), 128→1 l. |
| achats | `/matieres/124?onglet=historique` | — | — | « Plastique-140 » → 105 ms (écran), 127→1 l. | « Plastique-140 » → 106 ms (écran), 128→1 l. |
| achats | `/matieres/124?onglet=achat` | — | — | « Plastique-140 » → 105 ms (écran), 127→1 l. | « Plastique-140 » → 106 ms (écran), 128→1 l. |
| achats | `/matieres/124?onglet=pieces` | — | — | « Plastique-140 » → 104 ms (écran), 127→1 l. | « Plastique-140 » → 105 ms (écran), 128→1 l. |
| alimentation | `/stock/matieres/124` | — | — | « Plastique-140 » → 104 ms (écran), 156→29 l. | « Plastique-140 » → 104 ms (écran), 161→30 l. |
| alimentation | `/lots/353` | — | — | « Plastique-140 » → 107 ms (écran), 314→13 l. | — |
| alimentation | `/tracabilite?lot=353` | — | — | « Plastique-140 » → 111 ms (écran), 952→654 l. | — |
| alimentation | `/tracabilite?matiere=124` | — | — | « Plastique-140 » → 112 ms (écran), 1621→1323 l. | « Plastique-140 » → 158 ms (écran), 3295→2661 l. |
| alimentation | `/ordres/1087` | — | — | « Plastique-140 » → 390 ms (serveur), 511→511 l. | — |
| alimentation | `/ordres/1087/retour` | — | — | « Plastique-140 » → 650 ms (serveur), 511→511 l. | — |
| alimentation | `/production/besoins/124` | — | — | « Plastique-140 » → 105 ms (écran), 95→8 l. | « Plastique-140 » → 106 ms (écran), 99→8 l. |
| alimentation | `/operations/337` | — | — | « Plastique-140 » → 104 ms (serveur), 119→3 l. | — |
| alimentation | `/matieres/124?onglet=classification` | — | — | « Plastique-140 » → 105 ms (écran), 127→1 l. | « Plastique-140 » → 105 ms (écran), 128→1 l. |
| alimentation | `/matieres/124?onglet=conditionnement` | — | — | « Plastique-140 » → 105 ms (écran), 127→1 l. | « Plastique-140 » → 103 ms (écran), 128→1 l. |
| alimentation | `/matieres/124?onglet=historique` | — | — | « Plastique-140 » → 105 ms (écran), 127→1 l. | « Plastique-140 » → 105 ms (écran), 128→1 l. |
| direction | `/lots/704` | — | — | — | « Plastique-140 » → 108 ms (écran), 526→12 l. |
| direction | `/tracabilite?lot=704` | — | — | — | « Plastique-140 » → 141 ms (écran), 1872→1238 l. |
| direction | `/ordres/2181` | — | — | — | « Plastique-140 » → 583 ms (serveur), 512→512 l. |
| direction | `/ordres/2181/retour` | — | — | — | « Plastique-140 » → 892 ms (serveur), 512→512 l. |
| direction | `/commandes/275?onglet=lignes` | — | — | — | « HASIRCI » → 105 ms (serveur), 57→9 l. |
| direction | `/commandes/275?onglet=prix` | — | — | — | « HASIRCI » → 105 ms (serveur), 57→9 l. |
| direction | `/commandes/275?onglet=expedition` | — | — | — | « HASIRCI » → 106 ms (serveur), 56→8 l. |
| direction | `/commandes/275?onglet=receptions` | — | — | — | « HASIRCI » → 105 ms (serveur), 56→8 l. |
| direction | `/commandes/275?onglet=approbation` | — | — | — | « HASIRCI » → 105 ms (serveur), 57→9 l. |
| direction | `/commandes/275?onglet=pieces` | — | — | — | « HASIRCI » → 105 ms (serveur), 56→8 l. |
| direction | `/commandes/275?onglet=historique` | — | — | — | « HASIRCI » → 104 ms (serveur), 56→8 l. |
| direction | `/receptions/274?onglet=lignes` | — | — | — | « HASIRCI » → 103 ms (serveur), 260→46 l. |
| direction | `/receptions/274?onglet=reclamations` | — | — | — | « HASIRCI » → 107 ms (serveur), 258→44 l. |
| direction | `/receptions/274?onglet=pieces` | — | — | — | « HASIRCI » → 108 ms (serveur), 258→44 l. |
| direction | `/receptions/274?onglet=historique` | — | — | — | « HASIRCI » → 107 ms (serveur), 258→44 l. |
| direction | `/reclamations/22?onglet=reponse` | — | — | — | « Plastique-140 » → 110 ms (serveur), 258→49 l. |
| direction | `/reclamations/22?onglet=pieces` | — | — | — | « Plastique-140 » → 105 ms (serveur), 258→49 l. |
| direction | `/reclamations/22?onglet=historique` | — | — | — | « Plastique-140 » → 106 ms (serveur), 258→49 l. |
| direction | `/dossiers/160?onglet=familles` | — | — | — | « Plastique-140 » → 102 ms (écran), 158→158 l. |
| direction | `/dossiers/160?onglet=marchandises` | — | — | — | « Plastique-140 » → 103 ms (écran), 158→158 l. |
| direction | `/dossiers/160?onglet=frais` | — | — | — | « Plastique-140 » → 105 ms (écran), 161→161 l. |
| direction | `/dossiers/160?onglet=echeancier` | — | — | — | « Plastique-140 » → 103 ms (écran), 165→165 l. |
| direction | `/dossiers/160?onglet=pieces` | — | — | — | « Plastique-140 » → 105 ms (écran), 156→156 l. |
| direction | `/dossiers/160?onglet=facture` | — | — | — | « Plastique-140 » → 103 ms (écran), 158→158 l. |
| direction | `/dossiers/160?onglet=historique` | — | — | — | « Plastique-140 » → 106 ms (écran), 156→156 l. |
| direction | `/inventaires/57?onglet=lots` | — | — | — | « Plastique-140 » → 105 ms (écran), 56→0 l. |
| direction | `/inventaires/57?onglet=pieces` | — | — | — | « Plastique-140 » → 106 ms (écran), 56→0 l. |
| direction | `/inventaires/57?onglet=historique` | — | — | — | « Plastique-140 » → 104 ms (écran), 56→0 l. |
| direction | `/operations/641` | — | — | — | « Plastique-140 » → 105 ms (serveur), 363→1 l. |
| achats | `/lots/704` | — | — | — | « Plastique-140 » → 109 ms (écran), 526→12 l. |
| achats | `/tracabilite?lot=704` | — | — | — | « Plastique-140 » → 135 ms (écran), 1872→1238 l. |
| achats | `/ordres/2181` | — | — | — | « Plastique-140 » → 847 ms (serveur), 512→512 l. |
| achats | `/commandes/275?onglet=lignes` | — | — | — | « HASIRCI » → 105 ms (serveur), 57→9 l. |
| achats | `/commandes/275?onglet=prix` | — | — | — | « HASIRCI » → 105 ms (serveur), 57→9 l. |
| achats | `/commandes/275?onglet=expedition` | — | — | — | « HASIRCI » → 106 ms (serveur), 56→8 l. |
| achats | `/commandes/275?onglet=receptions` | — | — | — | « HASIRCI » → 107 ms (serveur), 56→8 l. |
| achats | `/commandes/275?onglet=approbation` | — | — | — | « HASIRCI » → 105 ms (serveur), 57→9 l. |
| achats | `/commandes/275?onglet=pieces` | — | — | — | « HASIRCI » → 108 ms (serveur), 56→8 l. |
| achats | `/commandes/275?onglet=historique` | — | — | — | « HASIRCI » → 106 ms (serveur), 56→8 l. |
| achats | `/receptions/274?onglet=lignes` | — | — | — | « HASIRCI » → 147 ms (serveur), 260→46 l. |
| achats | `/receptions/274?onglet=reclamations` | — | — | — | « HASIRCI » → 109 ms (serveur), 258→44 l. |
| achats | `/receptions/274?onglet=pieces` | — | — | — | « HASIRCI » → 105 ms (serveur), 258→44 l. |
| achats | `/receptions/274?onglet=historique` | — | — | — | « HASIRCI » → 106 ms (serveur), 258→44 l. |
| achats | `/reclamations/22?onglet=reponse` | — | — | — | « Plastique-140 » → 106 ms (serveur), 258→49 l. |
| achats | `/reclamations/22?onglet=pieces` | — | — | — | « Plastique-140 » → 109 ms (serveur), 258→49 l. |
| achats | `/reclamations/22?onglet=historique` | — | — | — | « Plastique-140 » → 109 ms (serveur), 258→49 l. |
| achats | `/dossiers/160?onglet=familles` | — | — | — | « Plastique-140 » → 110 ms (écran), 158→158 l. |
| achats | `/dossiers/160?onglet=marchandises` | — | — | — | « Plastique-140 » → 104 ms (écran), 158→158 l. |
| achats | `/dossiers/160?onglet=frais` | — | — | — | « Plastique-140 » → 103 ms (écran), 161→161 l. |
| achats | `/dossiers/160?onglet=echeancier` | — | — | — | « Plastique-140 » → 104 ms (écran), 165→165 l. |
| achats | `/dossiers/160?onglet=pieces` | — | — | — | « Plastique-140 » → 103 ms (écran), 156→156 l. |
| achats | `/dossiers/160?onglet=facture` | — | — | — | « Plastique-140 » → 106 ms (écran), 158→158 l. |
| achats | `/dossiers/160?onglet=historique` | — | — | — | « Plastique-140 » → 105 ms (écran), 156→156 l. |
| achats | `/inventaires/57?onglet=lots` | — | — | — | « Plastique-140 » → 106 ms (écran), 56→0 l. |
| achats | `/inventaires/57?onglet=pieces` | — | — | — | « Plastique-140 » → 106 ms (écran), 56→0 l. |
| achats | `/inventaires/57?onglet=historique` | — | — | — | « Plastique-140 » → 106 ms (écran), 56→0 l. |
| achats | `/operations/641` | — | — | — | « Plastique-140 » → 104 ms (serveur), 363→1 l. |
| alimentation | `/lots/704` | — | — | — | « Plastique-140 » → 109 ms (écran), 526→12 l. |
| alimentation | `/tracabilite?lot=704` | — | — | — | « Plastique-140 » → 119 ms (écran), 1872→1238 l. |
| alimentation | `/ordres/2181` | — | — | — | « Plastique-140 » → 900 ms (serveur), 512→512 l. |
| alimentation | `/ordres/2181/retour` | — | — | — | « Plastique-140 » → 751 ms (serveur), 512→512 l. |
| alimentation | `/operations/641` | — | — | — | « Plastique-140 » → 106 ms (serveur), 363→1 l. |

Recherche globale (coque) :

- referentiels, direction : « HASIRCI » → ouverte, 4 ms, 0 résultat(s)
- referentiels, achats : « HASIRCI » → ouverte, 8 ms, 0 résultat(s)
- referentiels, alimentation : « HASIRCI » → ouverte, 8 ms, 0 résultat(s)
- x30, direction : « HASIRCI » → ouverte, 259 ms, 9 résultat(s)
- x30, achats : « HASIRCI » → ouverte, 257 ms, 9 résultat(s)
- x30, alimentation : « HASIRCI » → ouverte, 257 ms, 0 résultat(s)
- annee-1, direction : « HASIRCI » → ouverte, 257 ms, 8 résultat(s)
- annee-1, achats : « HASIRCI » → ouverte, 257 ms, 8 résultat(s)
- annee-1, alimentation : « HASIRCI » → ouverte, 258 ms, 0 résultat(s)
- annee-2, direction : « HASIRCI » → ouverte, 259 ms, 9 résultat(s)
- annee-2, achats : « HASIRCI » → ouverte, 260 ms, 9 résultat(s)
- annee-2, alimentation : « HASIRCI » → ouverte, 256 ms, 0 résultat(s)

## 6. Les plus grands tableaux rendus (lignes dans le DOM)

### referentiels

- `/qualites?onglet=nomenclature` : 319 lignes — 319 / 319 — pas de « charger la suite »
- `/qualites?onglet=nomenclature` : 319 lignes — 319 / 319 — pas de « charger la suite »
- `/qualites?onglet=nomenclature` : 319 lignes — 319 / 319 — pas de « charger la suite »
- `/administration?onglet=journal` : 157 lignes — 157 / 157 — pas de « charger la suite »
- `/stock?onglet=matieres` : 124 lignes — 124 / 124 — pas de « charger la suite »
- `/stock?onglet=matieres` : 124 lignes — 124 / 124 — pas de « charger la suite »
- `/stock?onglet=matieres` : 124 lignes — 124 / 124 — pas de « charger la suite »
- `/stock/matieres/1` : 124 lignes — 124 / 124 — pas de « charger la suite »
- `/stock/matieres/1` : 124 lignes — 124 / 124 — pas de « charger la suite »
- `/stock/matieres/1` : 124 lignes — 124 / 124 — pas de « charger la suite »
- `/matieres/nouvelle` : 124 lignes — 124 / 124 — pas de « charger la suite »
- `/matieres/nouvelle` : 124 lignes — 124 / 124 — pas de « charger la suite »
- `/matieres/1?onglet=pieces` : 124 lignes — 124 / 124 — pas de « charger la suite »
- `/matieres/1?onglet=pieces` : 124 lignes — 124 / 124 — pas de « charger la suite »
- `/matieres/1?onglet=historique` : 124 lignes — 124 / 124 — pas de « charger la suite »

### x30

- `/analyse?onglet=historique` : 43290 lignes — 43 290 / 43 290 — pas de « charger la suite »
- `/analyse?onglet=historique` : 43290 lignes — 43 290 / 43 290 — pas de « charger la suite »
- `/stock?onglet=lots` : 20160 lignes — 20 160 / 20 160 — pas de « charger la suite »
- `/stock?onglet=lots` : 20160 lignes — 20 160 / 20 160 — pas de « charger la suite »
- `/stock?onglet=lots` : 20160 lignes — 20 160 / 20 160 — pas de « charger la suite »
- `/lots/291565` : 20160 lignes — 20 160 / 20 160 — pas de « charger la suite »
- `/lots/291565` : 20160 lignes — 20 160 / 20 160 — pas de « charger la suite »
- `/lots/291565` : 20160 lignes — 20 160 / 20 160 — pas de « charger la suite »
- `/tracabilite?matiere=111` : 9570 lignes — 9 570 / 9 570 — pas de « charger la suite »
- `/tracabilite?matiere=111` : 9570 lignes — 9 570 / 9 570 — pas de « charger la suite »
- `/tracabilite?matiere=111` : 9570 lignes — 9 570 / 9 570 — pas de « charger la suite »
- `/tracabilite?lot=291565` : 9570 lignes — 9 570 / 9 570 — pas de « charger la suite »
- `/tracabilite?lot=291565` : 9570 lignes — 9 570 / 9 570 — pas de « charger la suite »
- `/tracabilite?lot=291565` : 9570 lignes — 9 570 / 9 570 — pas de « charger la suite »
- `/stock?onglet=ordres` : 9570 lignes — 9 570 / 9 570 — pas de « charger la suite »

### annee-1

- `/tracabilite?matiere=124` : 951 lignes — 951 / 951 — pas de « charger la suite »
- `/tracabilite?matiere=124` : 951 lignes — 951 / 951 — pas de « charger la suite »
- `/tracabilite?matiere=124` : 951 lignes — 951 / 951 — pas de « charger la suite »
- `/tracabilite?lot=353` : 951 lignes — 951 / 951 — pas de « charger la suite »
- `/tracabilite?lot=353` : 951 lignes — 951 / 951 — pas de « charger la suite »
- `/tracabilite?lot=353` : 951 lignes — 951 / 951 — pas de « charger la suite »
- `/stock?onglet=ordres` : 951 lignes — 951 / 951 — pas de « charger la suite »
- `/stock?onglet=ordres` : 951 lignes — 951 / 951 — pas de « charger la suite »
- `/stock?onglet=ordres` : 951 lignes — 951 / 951 — pas de « charger la suite »
- `/analyse?onglet=production` : 951 lignes — 951 / 951 — pas de « charger la suite »
- `/analyse?onglet=production` : 951 lignes — 951 / 951 — pas de « charger la suite »
- `/tracabilite?matiere=124` : 670 lignes — Mouvements suivis — pas de « charger la suite »
- `/tracabilite?matiere=124` : 670 lignes — Mouvements suivis — pas de « charger la suite »
- `/tracabilite?matiere=124` : 670 lignes — Mouvements suivis — pas de « charger la suite »
- `/stock?onglet=mouvements` : 500 lignes — 500 / 15 746 — 500 lignes chargées sur 15 746 Charger les 500 suivants

### annee-2

- `/tracabilite?matiere=124` : 1871 lignes — 1 871 / 1 871 — pas de « charger la suite »
- `/tracabilite?matiere=124` : 1871 lignes — 1 871 / 1 871 — pas de « charger la suite »
- `/tracabilite?matiere=124` : 1871 lignes — 1 871 / 1 871 — pas de « charger la suite »
- `/tracabilite?lot=704` : 1871 lignes — 1 871 / 1 871 — pas de « charger la suite »
- `/tracabilite?lot=704` : 1871 lignes — 1 871 / 1 871 — pas de « charger la suite »
- `/tracabilite?lot=704` : 1871 lignes — 1 871 / 1 871 — pas de « charger la suite »
- `/stock?onglet=ordres` : 1871 lignes — 1 871 / 1 871 — pas de « charger la suite »
- `/stock?onglet=ordres` : 1871 lignes — 1 871 / 1 871 — pas de « charger la suite »
- `/stock?onglet=ordres` : 1871 lignes — 1 871 / 1 871 — pas de « charger la suite »
- `/analyse?onglet=production` : 1871 lignes — 1 871 / 1 871 — pas de « charger la suite »
- `/analyse?onglet=production` : 1871 lignes — 1 871 / 1 871 — pas de « charger la suite »
- `/tracabilite?matiere=124` : 1424 lignes — Mouvements suivis — pas de « charger la suite »
- `/tracabilite?matiere=124` : 1424 lignes — Mouvements suivis — pas de « charger la suite »
- `/tracabilite?matiere=124` : 1424 lignes — Mouvements suivis — pas de « charger la suite »
- `/analyse?onglet=historique` : 572 lignes — 572 / 572 — pas de « charger la suite »

## 7. Chiffres d'écran contre recompte SQL

### x30 — 26 cas, 0 écart(s)

| Cas | Écran | SQL | Verdict |
|---|---|---|---|
| Valorisation : kg en magasin = Σ soldes | 21 586 959.00 | 21 586 959.00 | ok |
| Valorisation : matières en stock = matières à solde > 0 | 372.00 | 372.00 | ok |
| Stock par matière : Σ stock (kg) = valorisation (kg) | 21 586 959.00 | 21 586 959.00 | ok |
| Cockpit : valeur en magasins = valorisation (MAD) | 539 557 634.76 | 539 557 634.76 | ok |
| Mouvements : total | 313 140.00 | 313 140.00 | ok |
| Journal : total | 114 736.00 | 114 736.00 | ok |
| Réceptions validées : total | 9 600.00 | 9 600.00 | ok |
| Ordres validés : total | 9 570.00 | 9 570.00 | ok |
| Opérations : total | 0.00 | 0.00 | ok |
| Dossiers clos : total | 2 130.00 | 2 130.00 | ok |
| Commandes « brouillon » : compte de l'onglet | 0.00 | 0.00 | ok |
| Commandes « envoyee » : compte de l'onglet | 0.00 | 0.00 | ok |
| Commandes « confirmee » : compte de l'onglet | 1 740.00 | 1 740.00 | ok |
| Échéancier : factures non réglées = factures sans règlement | 9 480.00 | 9 480.00 | ok |
| Échéancier : total MAD = Σ des lignes | 1 045 604 762.40 | 1 045 604 762.40 | ok |
| Échéancier : échu = Σ des lignes échues | 993 190 488.86 | 993 190 488.86 | ok |
| Plan et réalisé 2025-11-30→2026-10-31 : Σ m² réalisés | 2 170 765.88 | 2 170 765.88 | ok |
| Plan et réalisé 2024-11-30→2025-10-31 : Σ m² réalisés | 2 258 903.21 | 2 258 903.21 | ok |
| Plan et réalisé 2023-11-30→2024-10-31 : Σ m² réalisés | 2 258 903.21 | 2 258 903.21 | ok |
| Plan et réalisé 2022-11-30→2023-10-31 : Σ m² réalisés | 2 258 903.21 | 2 258 903.21 | ok |
| Plan et réalisé 2021-11-30→2022-10-31 : Σ m² réalisés | 2 258 903.21 | 2 258 903.21 | ok |
| Plan et réalisé 2020-11-30→2021-10-31 : Σ m² réalisés | 2 258 903.21 | 2 258 903.21 | ok |
| Plan et réalisé 2019-11-30→2020-10-31 : Σ m² réalisés | 2 258 903.21 | 2 258 903.21 | ok |
| Plan et réalisé 2018-11-30→2019-10-31 : Σ m² réalisés | 2 258 903.21 | 2 258 903.21 | ok |
| Plan et réalisé 2017-11-30→2018-10-31 : Σ m² réalisés | 2 258 903.21 | 2 258 903.21 | ok |
| Plan et réalisé 2016-11-30→2017-10-31 : Σ m² réalisés | 2 258 903.21 | 2 258 903.21 | ok |

### annee-1 — 27 cas, 0 écart(s)

| Cas | Écran | SQL | Verdict |
|---|---|---|---|
| Valorisation : kg en magasin = Σ soldes | 883 469.80 | 883 469.80 | ok |
| Valorisation : matières en stock = matières à solde > 0 | 87.00 | 87.00 | ok |
| Stock par matière : Σ stock net (kg) = valorisation en magasin (kg) | 883 469.80 | 883 469.80 | ok |
| Stock par matière : Σ sur les métiers (kg) = valorisation métiers (kg) | 23 459.27 | 23 459.27 | ok |
| Cockpit : valeur en magasins = valorisation (MAD) | 27 861 363.20 | 27 861 363.20 | ok |
| Mouvements : total | 15 746.00 | 15 746.00 | ok |
| Journal : total | 4 955.00 | 4 955.00 | ok |
| Réceptions validées : total | 88.00 | 88.00 | ok |
| Ordres validés : total | 951.00 | 951.00 | ok |
| Opérations : total | 331.00 | 331.00 | ok |
| Dossiers clos : total | 54.00 | 54.00 | ok |
| Commandes « brouillon » : compte de l'onglet | 0.00 | 0.00 | ok |
| Commandes « envoyee » : compte de l'onglet | 3.00 | 3.00 | ok |
| Commandes « confirmee » : compte de l'onglet | 26.00 | 26.00 | ok |
| Échéancier : factures non réglées = factures (réception validée) sans règlement | 23.00 | 23.00 | ok |
| Échéancier : total MAD = Σ des lignes | 141 058.73 | 141 058.73 | ok |
| Échéancier : échu = Σ des lignes échues | 124 788.15 | 124 788.15 | ok |
| Plan et réalisé 2026-11-30→2027-10-31 : Σ m² réalisés | 169 147.00 | 169 147.00 | ok |
| Plan et réalisé 2025-11-30→2026-10-31 : Σ m² réalisés | 0.00 | 0.00 | ok |
| Plan et réalisé 2024-11-30→2025-10-31 : Σ m² réalisés | 0.00 | 0.00 | ok |
| Plan et réalisé 2023-11-30→2024-10-31 : Σ m² réalisés | 0.00 | 0.00 | ok |
| Plan et réalisé 2022-11-30→2023-10-31 : Σ m² réalisés | 0.00 | 0.00 | ok |
| Plan et réalisé 2021-11-30→2022-10-31 : Σ m² réalisés | 0.00 | 0.00 | ok |
| Plan et réalisé 2020-11-30→2021-10-31 : Σ m² réalisés | 0.00 | 0.00 | ok |
| Plan et réalisé 2019-11-30→2020-10-31 : Σ m² réalisés | 0.00 | 0.00 | ok |
| Plan et réalisé 2018-11-30→2019-10-31 : Σ m² réalisés | 0.00 | 0.00 | ok |
| Plan et réalisé 2017-11-30→2018-10-31 : Σ m² réalisés | 0.00 | 0.00 | ok |

### annee-2 — 27 cas, 0 écart(s)

| Cas | Écran | SQL | Verdict |
|---|---|---|---|
| Valorisation : kg en magasin = Σ soldes | 730 777.98 | 730 777.98 | ok |
| Valorisation : matières en stock = matières à solde > 0 | 91.00 | 91.00 | ok |
| Stock par matière : Σ stock net (kg) = valorisation en magasin (kg) | 730 777.98 | 730 777.98 | ok |
| Stock par matière : Σ sur les métiers (kg) = valorisation métiers (kg) | 34 327.66 | 34 327.66 | ok |
| Cockpit : valeur en magasins = valorisation (MAD) | 24 357 943.42 | 24 357 943.42 | ok |
| Mouvements : total | 29 950.00 | 29 950.00 | ok |
| Journal : total | 11 378.00 | 11 378.00 | ok |
| Réceptions validées : total | 258.00 | 258.00 | ok |
| Ordres validés : total | 1 871.00 | 1 871.00 | ok |
| Opérations : total | 634.00 | 634.00 | ok |
| Dossiers clos : total | 155.00 | 155.00 | ok |
| Commandes « brouillon » : compte de l'onglet | 0.00 | 0.00 | ok |
| Commandes « envoyee » : compte de l'onglet | 0.00 | 0.00 | ok |
| Commandes « confirmee » : compte de l'onglet | 56.00 | 56.00 | ok |
| Échéancier : factures non réglées = factures (réception validée) sans règlement | 65.00 | 65.00 | ok |
| Échéancier : total MAD = Σ des lignes | 2 485 886.41 | 2 485 886.41 | ok |
| Échéancier : échu = Σ des lignes échues | 188 046.27 | 188 046.27 | ok |
| Plan et réalisé 2027-11-30→2028-10-31 : Σ m² réalisés | 166 064.00 | 166 064.00 | ok |
| Plan et réalisé 2026-11-30→2027-10-31 : Σ m² réalisés | 169 147.00 | 169 147.00 | ok |
| Plan et réalisé 2025-11-30→2026-10-31 : Σ m² réalisés | 0.00 | 0.00 | ok |
| Plan et réalisé 2024-11-30→2025-10-31 : Σ m² réalisés | 0.00 | 0.00 | ok |
| Plan et réalisé 2023-11-30→2024-10-31 : Σ m² réalisés | 0.00 | 0.00 | ok |
| Plan et réalisé 2022-11-30→2023-10-31 : Σ m² réalisés | 0.00 | 0.00 | ok |
| Plan et réalisé 2021-11-30→2022-10-31 : Σ m² réalisés | 0.00 | 0.00 | ok |
| Plan et réalisé 2020-11-30→2021-10-31 : Σ m² réalisés | 0.00 | 0.00 | ok |
| Plan et réalisé 2019-11-30→2020-10-31 : Σ m² réalisés | 0.00 | 0.00 | ok |
| Plan et réalisé 2018-11-30→2019-10-31 : Σ m² réalisés | 0.00 | 0.00 | ok |


## Constats

### Phase A — mise au point (base « référentiels seuls » puis base ×30 de l'épreuve de charge)

Méthode : serveur jetable uvicorn (2 processus, écran construit, port > 8100) sur une **copie**
(`gestion_mp_pro_stress_ecran_ref_essai` = `pg_dump gestion_mp_pro` + `alembic upgrade head` ;
`gestion_mp_pro_stress_ecran_charge_x30_essai` = `charge.py remplir`, ×30), comptes d'essai
`stress-ecran-<rôle>` inscrits dans la copie puis désactivés, Chrome sans tête piloté par CDP.
Les référentiels de la copie ne sont pas touchés (aucune écriture métier : la tournée ne fait que
lire, chercher, exporter et imprimer).

**Base « référentiels seuls » (l'état livré, activité vide) : aucun écran lent, aucune erreur.**
307 écrans × onglets, 375 ms médiane (c'est le démarrage de l'écran construit : les appels `/api/`
font 10 à 100 ms), 120 exports et documents tous en 200 et < 70 ms, recherche à la frappe ~100 ms,
recherche globale 9 résultats pour « HASIRCI ». Les 69 remarques sont toutes de PRÉSENTATION,
déjà connues ou attendues :

- PRÉSENTATION (connu, « à trancher » dans AUDIT2) : au bureau 1 440 px, les tableaux à 12 mois
  (Production › plan, glissant, plan et réalisé, besoins ; fiche « Besoin d'une matière ») et les
  tableaux larges (Stock › par matière : 2 017 px pour 1 142 de cadre — les colonnes au-delà de
  « Commandé » sont hors cadre ; Analyse › opportunités 1 170, fournisseurs 1 228 ; Administration
  › journal 2 161, données brutes 3 049) débordent de leur cadre : la barre de défilement
  horizontale est invisible sur Mac, l'utilisateur ne sait pas qu'il manque des colonnes.
- INFORMATION : au téléphone (375 px), les écrans du **bureau** ouverts à l'alimentation
  (stock, sorties, production, catalogue, qualités, métiers, aide) ont tous un tableau plus large
  que l'écran ; l'**atelier** (ses 10 écrans), lui, tient parfaitement en 375 × 812, sans montant.
- Aucun montant chez l'alimentation (bureau comme atelier) ; aucune fenêtre avec défilement caché
  ni contenu écrasé ; pas de défilement horizontal de page.

**Base ×30 (10 ans d'historique recopiés, 313 140 mouvements, 9 600 OF, 9 630 réceptions,
2 700 dossiers, 50 520 lots dont 20 160 encore en stock).** C'est une base **plus dure que le
réel** (les lots des années recopiées gardent leur solde, 1 740 bons restent « confirmés ») : elle
sert à voir ce qui casse, pas à juger ; la phase B (base simulée « comme un humain ») tranche.
368 écrans, médiane 1,1 s, 71 écrans entre 1 et 3 s, 121 au-delà de 3 s, aucun bloqué (> 30 s),
aucune erreur 5xx, aucune erreur JavaScript, recompte SQL 26 cas / 0 écart (stock, valorisation,
cockpit, listes paginées, échéancier, réalisé sur 10 ans). Profil à froid / à chaud (serveur dédié,
1 processus, `scratchpad/stress_profil_routes.py`) :

| Route | à froid | à chaud | Taille | Cause lue dans le code |
|---|---|---|---|---|
| `/api/contexte` (premier appel d'une session) | 9,0 s | 22 ms | 2 Ko | charge le moteur (`donnees_moteur.charger`) ; le cache dérivé est vidé à **chaque ligne de journal**, donc à chaque connexion et à chaque écriture |
| `/api/cockpit` | 2,1 s | 9 ms | 7 Ko | idem (cache dérivé) |
| `/api/qualites` | 3,7 s | 40 ms | 54 Ko | idem |
| `/api/ordres/apercu?statut=valide` | 6,6 s | **5,8 s** | 2 Ko | `_agregats` relit **tous** les OF du filtre (9 570) par le moteur pour sommer net/revenu/prévu/sorti — appelé par Sorties, la fiche d'un OF, « Nouvelle sortie », le retour |
| `/api/receptions/pesees?limite=1` | 3,6 s | **3,6 s** | 1 Ko | `receptions_pesees.pesees` reconstruit **toutes** les pesées (11 070) avant de couper la page ; appelé à **chaque** ouverture de Réceptions (compte de l'onglet « Pesées ») et de ses fiches |
| `/api/ordres/consommation` | 3,4 s | 3,1 s | 10 Ko | tous les OF, non paginé (Stock › Ordres de fabrication, traçabilité, Analyse › Production) |
| `/api/ordres/ouverts` | 4,8 s | 4,5 s | 5 Ko | 5 000 OF « ouverts » (artefact ×30 : au réel quelques-uns) — atelier Envoyer/Ordres/Retour |
| `/api/ordres?statut=valide&q=…` | 2,5 s | 2,5 s | 1 Mo | la recherche serveur relit la page par le moteur |
| `/api/documents/bilan?mois=…` | 7,0 s | 6,3 s | 12 Ko | `bilan.calculer` relit tous les mouvements, toutes les fabrications et `consommations(s)` (tous les OF) |
| `/api/lots?non_nuls=true` | 1,6 s | 1,7 s | 20 Ko | 20 160 lots en stock (artefact ×30) ; l'écran les rend tous (DOM : 20 160 lignes) |
| `/api/echeancier` | 1,2 s | 1,2 s | **8,9 Mo** | 9 480 factures non réglées (artefact ×30), toutes rendues (DOM : 9 480 lignes) |
| `/api/prix/historique` | 0,8 s | 0,8 s | **18 Mo** | 43 290 prix payés, tous rendus (DOM : 43 290 lignes) |
| `/api/stock`, `/api/brouillons`, `/api/metiers` | 0,26 s / 0,4 s / 0,24 s | idem | — | tiennent |

Exports et documents à ×30 (direction) : `export/mouvements` 43,6 s (27,6 Mo, en flux : connu,
V4/PAGINATION), `export/receptions/pesees` 11,1 s, `export/journal` 8,8 s, `export/prix` 5,6 s,
`export/echeancier` 4,3 s, `export/lots` 4,0 s, `export/revient` 3,9 s, `export/ordres` 3,3 s ;
le **bilan du mois** (document A4) 6,8 s ; tous les autres < 2,1 s. Tous en 200, sans trace.
`export/commandes/{id}/bon` d'un bon soldé → 409 (refus attendu : plus rien à envoyer).

Classement provisoire (à confirmer en phase B sur la base simulée, où le nombre d'OF validés
sur 10 ans sera du même ordre, ~10 000, mais pas les lots en stock ni les bons ouverts) :

- PROBABLE (structurel, croît avec l'historique, indépendant de l'artefact ×30) :
  `/ordres/apercu` (O(N) OF validés), `/receptions/pesees?limite=1` (O(N) pesées à chaque
  ouverture de Réceptions), `/ordres/consommation` et les trois onglets qui rendent tous les OF
  (Stock › OF, traçabilité, Analyse › Production), **Prix payés** (tous les prix de 10 ans dans le
  DOM, 18 Mo), **bilan du mois** (relit 10 ans pour un mois), premier écran après connexion
  (cache dérivé à reconstruire, 9 s à ×30).
- ARTEFACT ×30 (à revoir en phase B) : `/ordres/ouverts`, `/lots?non_nuls`, échéancier,
  `/commandes/ouverts`, cockpit onglets « alertes »/« économies » (`/brouillons` 3,6 s sous
  charge, 0,4 s seul).
- PRÉSENTATION (comme sur la base vide) : tableaux plus larges que le cadre, dont « Dossiers
  ouverts » (22 fois : colonnes « Coût hors TVA » et suivantes hors cadre à 1 440 px).

Aucune correction en phase A : rien de CERTAIN sur une base qui n'est pas celle de l'usine, et
la règle est de réfléchir avant de corriger. Les candidats à une correction certaine (essai
avant/après, chiffres inchangés) sont le compte des pesées par agrégat SQL et les agrégats de
`/ordres/apercu` ; ils seront décidés sur les chiffres de la phase B.

### Phase B — année 0 de la simulation (`annee-0.dump`, horloge figée au 14/10/2027)

Décision de Mohamed (relayée le 15/10) : le stress test se limite à **3 ans**. Base `annee-0`
restaurée dans `gestion_mp_pro_stress_ecran_a0_essai` (+ `alembic upgrade head`, déjà à 0008) :
15 746 mouvements, 340 lots, 986 OF (951 validés), 89 réceptions, 80 bons, 54 dossiers,
88 factures, 331 opérations, 25 inventaires, 128 matières (les 4 ajoutées finissent par
« (stress) » ; les 124 de Mohamed intactes).

**Tenue : 378 écrans, aucune erreur, aucun écran > 3 s, 15 écrans entre 1 et 1,5 s**, médiane
415 ms au bureau (≈ démarrage de l'écran) et 560 ms à l'atelier. Les 15 écrans « lents » sont
tous ceux qui lisent **la liste entière des OF** : Sorties › Validés (`/ordres/apercu` 0,7 s), la
fiche d'un OF et son retour (idem), « Nouvelle sortie » (`/ordres/ouverts` sans statut, 1,1 s),
atelier Envoyer / Ordres / Retour (`/ordres/ouverts` 0,8 s). Profil en mémoire
(`scratchpad/stress_profil_ordres.py`, cache chaud) : `ouverts(tous)` 290 ms, `apercu(valide)`
340 ms, `lister(page)` 198 ms, `consommations(s)` 38 ms — le coût est le chargement ORM des
986 OF avec leurs lignes et qualités (17 000 objets) puis `lire_un` par OF ; il est **linéaire
au nombre d'OF depuis l'origine** (pas de borne de période), le serveur à 2 processus le rend
à 2–3× (sérialisation, cache par processus). Les blocages, eux, ne coûtent rien hors brouillon.

Exports et documents : 130, tous en 200 ; le plus long `export/mouvements` 2,2 s (15 746
lignes, 1,2 Mo), tout le reste < 1 s ; bilan du mois 0,3 s, étiquettes, bon, feuille de comptage
< 0,1 s. Recherche à la frappe : 100–400 ms partout ; recherche globale 8 résultats pour
« HASIRCI » (0 pour l'alimentation : les fournisseurs lui sont fermés, voulu).

Chiffres contre SQL : **recompte de l'écran 27 cas / 0 écart** (valorisation = Σ soldes ; stock par
matière = valorisation, magasins et métiers ; cockpit = valorisation ; totaux des listes
paginées = `count(*)` ; onglets des commandes ; échéancier (total, échu, factures des réceptions
validées non réglées) ; plan et réalisé Σ m² jusqu'au jour de référence, pour les dix fenêtres
d'un an). **Vérification indépendante V1** (`verification_chiffres.py --serveur`, 13 dates) :
114 981 vérifications, 36 familles, **4 écarts**, tous dans « Échéancier » : frais 30, 33, 34, 35
réglés le 01/01/2027 « attendus dans reglees, vus [] ». Cause lue : `calcul/suivi.py`
`REGLEES_AU_PLUS = 300` — la vue « Réglées » ne garde que les 300 règlements les plus récents, et
l'année 0 en compte déjà 304 ; **rien à l'écran ne dit que la liste est tronquée** (année 2 :
889 réglées, donc 589 invisibles). Classé **PRÉSENTATION / QUESTION MÉTIER** : garder un plafond
(et le dire : « 300 derniers règlements sur 889 »), ou paginer cette vue comme les autres listes.

Deux faux positifs de mon pilote, corrigés (pas des défauts de PRO) : les appels que la page
**annule elle-même** quand une fiche s'ouvre par-dessus sa liste (`/api/receptions?statut=validee`
puis la même requête avec `limite=1`, `/api/operations?type=ouverture`) étaient comptés « en vol »
ou « échec » ; ils sont maintenant « annulé », hors temps et hors fautes. Remarque d'INFORMATION :
ouvrir une fiche de réception ou d'opération déclenche et annule une lecture de liste (coût
serveur perdu, sans effet visible).

Présentation (inchangé depuis la base vide) : mêmes tableaux plus larges que leur cadre à
1 440 px ; rien d'écrasé ni de défilement caché dans les fenêtres ; aucun montant chez
l'alimentation.

### Phase B — deux ans (`annee-1.dump`, horloge figée au 14/10/2028) : la tendance

Base `gestion_mp_pro_stress_ecran_a1_essai` : 29 950 mouvements, 691 lots, 1 949 OF (1 871
validés), 258 réceptions, 270 bons, 156 dossiers, 634 opérations, 132 matières. **378 écrans,
aucune erreur, aucun écran > 3 s, 36 écrans entre 1 et 2,2 s** (contre 15 à un an), médiane
inchangée (420 ms bureau, 685 ms atelier). Recompte SQL 27 cas / 0 écart. Ce qui grandit, d'une
année à l'autre (temps d'affichage, bureau direction, à froid) :

| Écran | 1 an | 2 ans | Appel qui pèse |
|---|---|---|---|
| Sorties › Validés | 0,9 s | 1,2–1,4 s | `/ordres/apercu?statut=valide` 0,55 → 0,86–1,0 s |
| Fiche d'un OF, retour, Nouvelle sortie | 0,9–1,5 s | 1,1–2,2 s | `/ordres/apercu` 0,7 → 1,8 s (alimentation) ; `/ordres/ouverts` 1,1 → 1,2 s |
| Atelier Envoyer / Ordres / Retour | 0,8–1,3 s | 1,3–1,9 s | `/ordres/ouverts` 0,8 → 0,9–1,4 s |
| Stock › Ordres de fabrication, traçabilité | 0,7 s | 1,1–1,2 s | `/ordres/consommation` 0,25 → 0,5–0,6 s ; 1 872 lignes rendues dans le DOM |
| Cockpit / Ma journée (premier écran) | 1,2 s | 1,8–1,9 s | `/api/contexte` ou `/api/cockpit` à froid 0,5 → 0,8 s |
| Recherche à la frappe dans Sorties | 0,5 s | 0,9–1,0 s | la page relue par le moteur |
| `export/mouvements` | 2,2 s (1,2 Mo) | 4,1 s (2,4 Mo) | export en flux, 29 950 lignes |

Tout le reste est stable (< 0,8 s). À trois ans, par extrapolation linéaire : aperçu des OF
≈ 2–2,7 s, `/ordres/ouverts` ≈ 2 s, `export/mouvements` ≈ 6 s. Rien d'autre ne dépassera 1 s.

**Correction CERTAINE (commit « Sorties : l'aperçu des ordres… »)** : `services/ordres/liste.py`
`_agregats` chargeait **tous** les OF du filtre avec leurs lignes et qualités puis les lisait un à
un par le moteur (`lire_un`) pour sommer net, revenu, prévu et sorti — linéaire au nombre d'OF
depuis l'origine, à chaque ouverture de Sorties, d'une fiche d'OF, de « Nouvelle sortie » et
d'un retour. Les OF validés et annulés sont maintenant sommés depuis le journal lu une fois pour
tous (`consommations(s)`, `retours_par_ordre`) ; les brouillons (et un OF numéroté sans journal)
passent par le moteur comme avant. Preuves : essai
`test_ordres_pagination::test_l_apercu_ne_lit_pas_les_ordres_valides_un_a_un` (échoue avant :
`lire_un` appelé pour les 3 validés ; passe après), `test_agregats_du_moteur` inchangé ;
comparaison avant/après sur la base à deux ans (`scratchpad/stress_apercu_egalite.py`, 7 filtres :
tous, validés, brouillons, annulés, validés + mot, période, métier) : **chiffres identiques** ;
en mémoire `apercu(valide)` **670 ms → 155 ms** à deux ans (348 → ~80 ms à un an). Aucune
décision de Mohamed touchée (mêmes indicateurs, même sens). `make verifier` : voir § final.

Non corrigé, décrit (PROBABLE, structurel) : `/ordres/ouverts` **sans statut** — l'atelier
« Ordres » et « Nouvelle sortie » demandent la liste entière des OF (plafond 5 000) alors que l'un
n'affiche que les plus récents (« charger les suivants ») et l'autre ne veut que la date du dernier
OF ; `/ordres/consommation` et les trois onglets qui rendent tous les OF dans le DOM (Stock ›
Ordres de fabrication, traçabilité, Analyse › Production) ; la recherche serveur de Sorties qui
relit la page par le moteur. Ce sont des changements de contrat ou d'écran (borner à une période
ou aux N derniers, paginer), à décider par Mohamed : à trois ans ils restent sous 3 s.
