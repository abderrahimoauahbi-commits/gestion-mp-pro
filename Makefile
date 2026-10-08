# Gestion MP PRO — commandes du dépôt (ARCHITECTURE § 3 et § 15, README).
# Les cibles dont l'outil n'est pas encore livré le disent et s'arrêtent (lot indiqué).

SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := aide

PYTHON ?= python3.12
BACK := backend
BIN := $(BACK)/.venv/bin
ECOUTE ?= 127.0.0.1
PORT ?= 8050

# $(call exige,<chemin>,<lot>) : s'arrête proprement si l'outil n'existe pas encore.
define exige
	@test -e $(1) || { echo "$(1) n'existe pas encore : cette cible arrive avec le lot $(2)."; exit 2; }
endef

.PHONY: aide installer verifier verifier-rapide verifier-serveur verifier-ecran verifier-outils \
	essais matrice types parite comparer miroir construire docker demarrer verrouiller

aide: ## Liste des cibles
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | sed -E 's/:.*## /\t/' | expand -t 20

installer: ## Environnement Python (backend/.venv), dépendances figées, écran, crochet pre-commit
	test -x $(BIN)/python || $(PYTHON) -m venv $(BACK)/.venv
	$(BIN)/python -m pip install -q --upgrade pip
	$(BIN)/python -m pip install -q -r $(BACK)/requirements-dev.lock
	$(BIN)/python -m pip install -q --no-deps -e $(BACK)
	if [ -f frontend/package.json ]; then npm --prefix frontend ci; fi
	if [ -e .git ]; then $(BIN)/pre-commit install; fi

verifier: verifier-serveur verifier-ecran verifier-outils ## Tout : serveur, écran, outils (définition de « fini »)

verifier-rapide: ## La partie rapide (crochet pre-commit) : ruff, format, mypy
	cd $(BACK) && .venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/mypy

verifier-serveur: verifier-rapide ## ruff, ruff format, mypy strict (services, calcul), pytest, alembic check
	cd $(BACK) && .venv/bin/pytest
	if [ -f $(BACK)/alembic.ini ]; then cd $(BACK) && .venv/bin/alembic check; fi

verifier-ecran: ## prettier, eslint, tsc, vitest (npm run verifier)
	if [ -f frontend/package.json ]; then npm --prefix frontend run verifier; \
	else echo "Écran absent : vérification de l'écran sautée."; fi

verifier-outils: ## Appels de l'écran contre l'OpenAPI ; preuves héritées citées
	if [ -f outils/routes_ecran.py ]; then $(BIN)/python outils/routes_ecran.py; fi
	if [ -f outils/verifier_heritage.py ]; then $(BIN)/python outils/verifier_heritage.py; fi

essais: ## pytest complet : les essais qui demandent un vrai serveur échouent au lieu d'être sautés
	cd $(BACK) && GESTIONMPPRO_ESSAIS_COMPLETS=1 .venv/bin/pytest

matrice: ## Régénère tests/matrice_droits.csv depuis les routes (jamais à la main)
	$(call exige,$(BACK)/gestion_mp_pro/securite.py,S2)
	cd $(BACK) && .venv/bin/python -m gestion_mp_pro.securite matrice > tests/matrice_droits.csv

types: ## openapi.json → frontend/src/lib/types.gen.ts
	$(call exige,scripts/generer_types.sh,E0/E2)
	scripts/generer_types.sh

parite: ## Parité de calcul avec Gestion MP sur l'année d'essai
	$(call exige,$(BACK)/essais/parite_gestion_mp.py,R2)
	$(BIN)/python $(BACK)/essais/parite_gestion_mp.py

comparer: ## Comparaison chiffre par chiffre Gestion MP (8030) / PRO (8050)
	$(call exige,outils/comparer_avec_gestion_mp.py,C1)
	$(BIN)/python outils/comparer_avec_gestion_mp.py --gestion-mp http://localhost:8030 \
		--pro http://localhost:$(PORT)

miroir: ## Rafraîchit la base PRO, miroir de Gestion MP (lecture seule de la source)
	$(call exige,$(BACK)/gestion_mp_pro/reprise/__main__.py,R1)
	cd $(BACK) && .venv/bin/python -m gestion_mp_pro.reprise --mode tout --remplacer-activite

construire: ## Construit l'écran (frontend/dist)
	$(call exige,frontend/package.json,E0)
	npm --prefix frontend ci && npm --prefix frontend run build

docker: ## Construit l'image et l'essaie avec Docker Compose
	$(call exige,deploiement/docker-compose.yml,X1)
	docker compose -f deploiement/docker-compose.yml build

demarrer: ## Serveur de développement sur 127.0.0.1:8050 (rechargement automatique)
	cd $(BACK) && .venv/bin/uvicorn gestion_mp_pro.main:app --host $(ECOUTE) --port $(PORT) \
		--reload --no-access-log

verrouiller: ## Refige les versions (requirements.lock, requirements-dev.lock) avec uv
	test -x $(BIN)/uv || $(BIN)/python -m pip install -q uv
	cd $(BACK) && .venv/bin/uv pip compile pyproject.toml -p .venv/bin/python -o requirements.lock -q
	cd $(BACK) && .venv/bin/uv pip compile pyproject.toml --extra dev -p .venv/bin/python \
		-o requirements-dev.lock -q
