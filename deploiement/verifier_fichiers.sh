#!/usr/bin/env bash
# Gestion MP PRO — vérifie les fichiers de déploiement SANS Docker (lot X1).
#
# Ce que ce script NE PEUT PAS faire sur un poste sans Docker : construire l'image,
# « docker compose up » sur une machine propre, essayer le service systemd. Ces trois points
# restent À FAIRE sur une machine Linux avec Docker (critères de LOTS X1). Voir docs/lots/X1.md.
#
# Ce qu'il contrôle ici : présence des fichiers, YAML valide, ports (8050 interne, 80/443
# publiés), aucun secret en dur, HEALTHCHECK sur /api/sante, compte non privilégié,
# uvicorn --no-access-log et 2 processus, « tls internal », la CSP NON écrasée par Caddy, et la
# cohérence des variables GESTIONMPPRO_* avec config.py.
#
# Usage : deploiement/verifier_fichiers.sh   (depuis la racine du dépôt ou ailleurs).
set -o pipefail

DEP="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RACINE="$(cd "$DEP/.." && pwd)"
CONFIG="$RACINE/backend/gestion_mp_pro/config.py"
COMPOSE="$DEP/docker-compose.yml"
DOCKERFILE="$DEP/Dockerfile"
CADDY="$DEP/Caddyfile"
ENVEX="$DEP/exemple.env"
SERVICE="$DEP/gestion-mp-pro.service"
IGNORE="$RACINE/.dockerignore"

ok=0
ko=0
passe() { printf '  ok   %s\n' "$1"; ok=$((ok + 1)); }
rate() { printf '  KO   %s\n' "$1"; ko=$((ko + 1)); }
note() { printf '  --   %s\n' "$1"; }

# Un python capable d'« import yaml » (venv du backend de préférence), sinon vide.
py_yaml() {
  for p in "$RACINE/backend/.venv/bin/python" python3 python; do
    if command -v "$p" >/dev/null 2>&1 && "$p" -c 'import yaml' >/dev/null 2>&1; then
      echo "$p"
      return 0
    fi
  done
  return 1
}
PYY="$(py_yaml || true)"
# Un python quelconque (stdlib seulement) pour lire config.py par AST.
PY="$(command -v python3 || command -v python || true)"

echo "== 1. Présence des fichiers =="
for f in "$DOCKERFILE" "$COMPOSE" "$CADDY" "$ENVEX" "$SERVICE" "$IGNORE" "$DEP/verifier_fichiers.sh"; do
  if [ -f "$f" ]; then passe "présent : ${f#"$RACINE"/}"; else rate "absent : ${f#"$RACINE"/}"; fi
done

echo "== 2. docker-compose.yml : YAML valide et structure =="
if [ -n "$PYY" ]; then
  if "$PYY" - "$COMPOSE" <<'PYEOF'
import sys, yaml
d = yaml.safe_load(open(sys.argv[1], encoding="utf-8"))
svc = d.get("services", {})
vol = d.get("volumes", {})
manque = [s for s in ("base", "application", "https") if s not in svc]
manque += ["volume " + v for v in ("donnees", "sauvegardes", "pieces", "caddy", "caddy-config") if v not in vol]
# 80/443 publiés par https, et l'application ne publie PAS de port.
ports = svc.get("https", {}).get("ports", [])
ports = " ".join(str(p) for p in ports)
if "80" not in ports or "443" not in ports:
    manque.append("https ne publie pas 80/443")
if svc.get("application", {}).get("ports"):
    manque.append("application publie un port (8050 doit rester interne)")
if manque:
    print("ECHEC: " + "; ".join(manque)); sys.exit(1)
print("OK")
PYEOF
  then passe "YAML valide ; services base/application/https ; volumes ; 80/443 publiés ; 8050 interne"
  else rate "docker-compose.yml : structure ou ports incorrects (voir ci-dessus)"
  fi
else
  note "pyyaml introuvable (fais « make installer ») : contrôle YAML textuel de repli"
  grep -q "	" "$COMPOSE" && rate "docker-compose.yml contient une tabulation (interdit en YAML)" \
    || passe "docker-compose.yml sans tabulation"
  for s in "base:" "application:" "https:"; do
    grep -qE "^  $s" "$COMPOSE" && passe "service $s" || rate "service manquant : $s"
  done
fi

echo "== 3. Ports =="
grep -q 'EXPOSE 8050' "$DOCKERFILE" && passe "Dockerfile EXPOSE 8050" || rate "Dockerfile sans EXPOSE 8050"
grep -q 'reverse_proxy application:8050' "$CADDY" && passe "Caddy relaie application:8050" \
  || rate "Caddy ne relaie pas application:8050"
grep -Eq '"80:80", *"443:443"|80:80|443:443' "$COMPOSE" && passe "Compose publie 80/443" \
  || rate "Compose ne publie pas 80/443"

echo "== 4. Aucun secret en dur =="
# exemple.env : les champs de mot de passe sont VIDES.
if grep -Eq '^GESTIONMPPRO_MOT_DE_PASSE_BASE=.+' "$ENVEX"; then rate "exemple.env : mot de passe de base rempli"; else passe "exemple.env : mot de passe de base vide"; fi
if grep -Eq '^GESTIONMPPRO_SMTP_MOT_DE_PASSE=.+' "$ENVEX"; then rate "exemple.env : mot de passe SMTP rempli"; else passe "exemple.env : mot de passe SMTP vide"; fi
# compose : le mot de passe vient d'une variable, jamais écrit en clair.
if grep -Eq 'POSTGRES_PASSWORD: *\$\{GESTIONMPPRO_MOT_DE_PASSE_BASE' "$COMPOSE"; then passe "Compose : mot de passe de base par variable"; else rate "Compose : mot de passe de base pas par variable"; fi
# aucun mot de passe littéral (hors ${...} et champs vides) dans les fichiers livrés.
if grep -RniE '(password|mot_de_passe)[":= ]+[^$ "{).]+' "$COMPOSE" "$SERVICE" "$CADDY" | grep -viE '\$\{|POSTGRES_PASSWORD: *\$|# |empreinte|contiennent' >/dev/null; then
  rate "un mot de passe littéral apparaît peut-être (à vérifier)"
  grep -RniE '(password|mot_de_passe)[":= ]+[^$ "{).]+' "$COMPOSE" "$SERVICE" "$CADDY" | grep -viE '\$\{|POSTGRES_PASSWORD: *\$|# |empreinte|contiennent' | sed 's/^/       /'
else
  passe "aucun mot de passe littéral dans compose/service/Caddy"
fi

echo "== 5. Application (Dockerfile) =="
grep -Eq '^USER gestionmppro' "$DOCKERFILE" && passe "compte non privilégié (USER gestionmppro)" || rate "pas de USER non privilégié"
grep -q 'useradd .*--uid 10001' "$DOCKERFILE" && passe "uid/gid 10001 (copie externe : chown 10001)" || rate "uid 10001 absent"
grep -q 'HEALTHCHECK' "$DOCKERFILE" && passe "HEALTHCHECK présent" || rate "HEALTHCHECK absent"
grep -q '/api/sante' "$DOCKERFILE" && passe "HEALTHCHECK sur /api/sante" || rate "HEALTHCHECK pas sur /api/sante"
grep -q -- '--no-access-log' "$DOCKERFILE" && passe "uvicorn --no-access-log (S0)" || rate "--no-access-log absent"
grep -Eq -- '--workers .*PROCESSUS:-2|--workers 2' "$DOCKERFILE" && passe "deux processus (--workers)" || rate "deux processus absents"
grep -q -- '--host 0.0.0.0' "$DOCKERFILE" && passe "écoute 0.0.0.0 (Caddy l'atteint)" || rate "n'écoute pas 0.0.0.0"
grep -q 'postgresql-client-16' "$DOCKERFILE" && passe "outils PostgreSQL 16 dans l'image" || rate "postgresql-client-16 absent"
grep -q 'postgresql+psycopg://' "$COMPOSE" && passe "pilote psycopg dans GESTIONMPPRO_BASE" || rate "pilote psycopg absent de GESTIONMPPRO_BASE"

echo "== 6. systemd =="
grep -q -- '--no-access-log' "$SERVICE" && passe "service : --no-access-log" || rate "service : --no-access-log absent"
grep -Eq -- '--workers 2' "$SERVICE" && passe "service : deux processus" || rate "service : deux processus absents"
grep -q 'EnvironmentFile=/etc/gestion-mp-pro.env' "$SERVICE" && passe "service : réglages par EnvironmentFile" || rate "service : EnvironmentFile absent"

echo "== 7. Caddy : HTTPS et CSP de l'application préservée =="
grep -q 'tls internal' "$CADDY" && passe "Caddy : tls internal (nom interne)" || rate "Caddy : tls internal absent"
# La CSP ne doit PAS être posée par Caddy : on ignore les lignes de commentaire (# …).
if grep -v '^[[:space:]]*#' "$CADDY" | grep -qi 'content-security-policy'; then
  rate "Caddy POSE une Content-Security-Policy (interdit : elle écraserait celle de l'application)"
else
  passe "Caddy ne pose pas de Content-Security-Policy (laissée à l'application)"
fi

echo "== 8. Variables GESTIONMPPRO_* cohérentes avec config.py =="
if [ -n "$PY" ] && [ -f "$CONFIG" ]; then
  CHAMPS="$("$PY" - "$CONFIG" <<'PYEOF'
import ast, sys
tree = ast.parse(open(sys.argv[1], encoding="utf-8").read())
noms = set()
for node in ast.walk(tree):
    if isinstance(node, ast.ClassDef) and node.name == "Reglages":
        for b in node.body:
            if isinstance(b, ast.AnnAssign) and isinstance(b.target, ast.Name):
                noms.add(b.target.id.upper())
print(" ".join(sorted(noms)))
PYEOF
)"
  # Variables propres au déploiement, absentes de config.py à dessein :
  #  NOM (nom public → ADRESSE), MOT_DE_PASSE_BASE (base/URL), VERSION (écrite dans /app/VERSION).
  HORS="NOM MOT_DE_PASSE_BASE VERSION"
  VALIDES="$CHAMPS $HORS"
  REFS="$(grep -ohE 'GESTIONMPPRO_[A-Z_]+' "$COMPOSE" "$ENVEX" "$SERVICE" | sed 's/GESTIONMPPRO_//' | sort -u)"
  inconnu=0
  for r in $REFS; do
    if ! printf '%s\n' $VALIDES | grep -qx "$r"; then
      rate "variable inconnue de config.py : GESTIONMPPRO_$r"
      inconnu=$((inconnu + 1))
    fi
  done
  [ "$inconnu" -eq 0 ] && passe "toutes les variables GESTIONMPPRO_* référencées existent (config.py + NOM/MOT_DE_PASSE_BASE/VERSION)"
else
  note "config.py ou python introuvable : cohérence des variables non vérifiée"
fi

echo
echo "== Bilan : $ok ok, $ko KO =="
echo "Rappel : image construite, « docker compose up » sur machine propre et service systemd"
echo "restent À FAIRE sur une machine Linux avec Docker (critères LOTS X1)."
[ "$ko" -eq 0 ]
