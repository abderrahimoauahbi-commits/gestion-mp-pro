# Gestion MP PRO — image unique : l'écran React est compilé, puis servi par l'API Python.
# Construction : docker compose -f deploiement/docker-compose.yml build  (ou « make docker »).

# 1) L'écran (frontend) compilé avec Node. « npm run build » = types (tsc) puis « vite build ».
FROM node:22-alpine AS ecran
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# 2) Le serveur (Python 3.12) sur une Debian figée (bookworm) : les outils ne changent pas d'une
# construction à l'autre.
FROM python:3.12-slim-bookworm
ARG DEBIAN_FRONTEND=noninteractive
# pg_dump / pg_restore / psql DE LA MÊME VERSION que la base (PostgreSQL 16) : le dépôt Debian
# fournit la 15, qui refuse de sauvegarder un serveur 16 → dépôt officiel PostgreSQL (PGDG).
# curl : la sonde HEALTHCHECK. tzdata : pour que zoneinfo trouve « Africa/Casablanca »
# (GESTIONMPPRO_FUSEAU ; le fuseau n'est jamais posé sur le processus, ARCHITECTURE C16).
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl gnupg tzdata \
    && install -d /usr/share/postgresql-common/pgdg \
    && curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc \
       | gpg --dearmor -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.gpg \
    && echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.gpg] https://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" \
       > /etc/apt/sources.list.d/pgdg.list \
    && apt-get update && apt-get install -y --no-install-recommends postgresql-client-16 \
    && apt-get purge -y gnupg && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

# Compte non privilégié, identifiant fixe : le dossier de copie externe monté sur /copie lui est
# donné d'avance (chown 10001:10001, voir docs/EXPLOITATION.md — lot X3).
RUN groupadd --system --gid 10001 gestionmppro \
    && useradd --system --uid 10001 --gid 10001 --create-home gestionmppro

WORKDIR /app/backend
# Les versions éprouvées par les essais (requirements.lock), pas « la dernière parue ».
COPY backend/pyproject.toml backend/requirements.lock ./
COPY backend/gestion_mp_pro/ gestion_mp_pro/
RUN pip install --no-cache-dir -c requirements.lock .
COPY --from=ecran /frontend/dist /app/frontend/dist

# Version servie par /api/sante : le commit passé à la construction, sinon « 0.1.0 (projet) »
# (api/systeme/routes.version_servie lit RACINE/VERSION = /app/VERSION).
ARG VERSION=""
RUN if [ -n "$VERSION" ]; then printf '%s\n' "$VERSION" > /app/VERSION; fi

ENV GESTIONMPPRO_ECRAN=/app/frontend/dist \
    GESTIONMPPRO_SAUVEGARDES=/sauvegardes \
    GESTIONMPPRO_PIECES=/pieces \
    GESTIONMPPRO_PG_BIN=/usr/lib/postgresql/16/bin
# Sauvegardes (empreintes de mots de passe) et pièces jointes : dossiers au seul compte, fermés.
# Montés par Compose sur des volumes ; créés ici pour une image lancée sans volume.
RUN mkdir -p /sauvegardes /pieces \
    && chown gestionmppro:gestionmppro /sauvegardes /pieces \
    && chmod 700 /sauvegardes /pieces
USER gestionmppro
EXPOSE 8050

# Sain = 200 (toujours rendu par /api/sante, même schéma en retard ou sauvegarde en défaut :
# l'alerte est dans la réponse et le bandeau de l'écran). Base injoignable → non-200 →
# conteneur « unhealthy ». /api/sante ne lit aucune table métier.
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s \
    CMD curl -fs -o /dev/null --max-time 4 "http://127.0.0.1:${GESTIONMPPRO_PORT:-8050}/api/sante" || exit 1

# Migration au démarrage : faite DANS l'application (main._mettre_le_schema_a_jour, sous le verrou
# consultatif MIGRATION ; schéma en retard → l'API répond 503). Deux processus : un seul porte les
# tâches de fond (verrou consultatif TACHES). --no-access-log : le journal « une ligne par
# requête » est celui de journalisation.trace. --proxy-headers : Caddy (port non publié) donne
# l'adresse réelle du poste (journal lisible, blocage des essais par poste).
CMD ["sh", "-c", "exec uvicorn gestion_mp_pro.main:app --host 0.0.0.0 --port ${GESTIONMPPRO_PORT:-8050} --workers ${GESTIONMPPRO_PROCESSUS:-2} --no-access-log --proxy-headers --forwarded-allow-ips '*'"]
