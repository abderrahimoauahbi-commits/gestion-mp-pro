# Lot NOMS — un nom court et unique pour chaque schéma de l'OpenAPI

Branche `lot-NOMS`. `make verifier` vert (2586 essais serveur, 696 essais d'écran).

## Ce qui a changé
Treize classes portaient le même nom dans plusieurs domaines ; FastAPI les nommait
`gestion_mp_pro__api__<domaine>__schemas__<Nom>`, et l'arrivée d'un homonyme renommait un type déjà
cité par l'écran (cas de `ConsommationOrdre`, 3b7054f). Renommage des classes seulement (champs,
routes, corps et réponses inchangés) :

| Ancien nom dans l'OpenAPI | Nouveau nom |
|---|---|
| `…__importations__schemas__Annulation` | `AnnulationDossier` |
| `…__receptions__schemas__Annulation` | `AnnulationReception` |
| `…__operations__schemas__Annulation` | `AnnulationOperation` |
| `…__importations__schemas__Cloture` | `ClotureDossier` |
| `…__reclamations__schemas__Cloture` | `ClotureReclamation` |
| `…__importations__schemas__Reouverture` | `ReouvertureDossier` |
| `…__reclamations__schemas__Reouverture` | `ReouvertureReclamation` |
| `…__commandes__schemas__LigneVersion` | `LigneVersionBon` |
| `…__qualites__schemas__LigneVersion` | `LigneVersionRecette` |
| `…__exploitation__schemas__Restauration` | `RestaurationSauvegarde` |
| `…__qualites__schemas__Restauration` | `RestaurationVersionRecette` |
| `…__importations__schemas_fiche__ValeurDevise` | `ValeurDeviseDossier` |
| `…__operations__schemas__ValeurDevise` | `ValeurDeviseOperation` |

## À savoir
- `tests/test_noms_openapi.py` échoue si un nom de schéma contient `__`, ou si deux classes exposées
  (modèles Pydantic, énumérations, dataclasses rendues par une route, de proche en proche :
  paramètres, corps, dépendances, réponses déclarées) portent le même nom. Une classe nouvelle prend
  donc un nom propre à son domaine (`<Geste><Document>`).
- Les dataclasses des services `Annulation`, `LigneVersion`, `ValeurDevise` (services/
  receptions_lecture, commandes_fiche, importations/modele, operations/lecture) ne sont pas exposées :
  laissées telles quelles ; si l'une devient un `response_model`, l'essai demandera de la renommer.
- `frontend/src/lib/types.gen.ts` de main n'avait pas été régénéré après D8 : il comprend maintenant
  les routes 7, 209, 212–229, 233, 235 (bilan, cockpit, contrôles, échéancier, pièces, signalements,
  performance des fournisseurs…). Les formes provisoires des écrans (F3 `SignalementFiche`,
  F4 `Paiement`, F7 `catalogue/performance.ts`) peuvent passer à `Schema<'…'>`.
- Aucun écran fusionné ne citait les anciens noms longs : rien à adapter dans `pages/` ni `lib/`.
