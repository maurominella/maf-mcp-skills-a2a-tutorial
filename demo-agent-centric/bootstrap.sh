#!/usr/bin/env bash
# Crea da zero il workspace della demo "Hello World" Agent-Centric (cap. 6).
# Uso: ./bootstrap.sh [cartella-destinazione]
set -euo pipefail

KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${1:-$HOME/git_repos/smart-meeting-rooms}"

COMMUNITY_SKILLS=(
  setup-matt-pocock-skills  # configura tracker, label e docs (una volta per repo)
  grilling                  # intervista a round (usata dalla Discovery)
  grill-me                  # /grill-me: alias manuale di grilling
  domain-modeling           # ADR e glossario (Architecture)
  to-spec                   # /to-spec: spec nel tracker (Delivery planning)
  to-tickets                # /to-tickets: ticket con dipendenze (Delivery planning)
  implement                 # /implement: implementazione di un ticket
  tdd                       # test-first, usata da implement
  code-review               # review, usata da implement
)

MICROSOFT_SKILLS=(
  discover-azure-skills        # meta-skill: scopre altre skill Azure
  entra-app-registration       # Security: design autenticazione
  azure-prepare                # Deployment: azure.yaml, Bicep, pipeline
  azure-validate               # Deployment: preflight
  azure-deploy                 # Deployment: azd up
  appinsights-instrumentation  # Deployment: telemetria
  azure-compliance             # Post-deploy: verifica risorse
)

info() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m[!] %s\033[0m\n' "$*"; }

info "Verifica prerequisiti"
for cmd in git npx; do
  command -v "$cmd" >/dev/null || { echo "Manca '$cmd': installalo e rilancia."; exit 1; }
done
for cmd in gh az azd; do
  command -v "$cmd" >/dev/null || warn "'$cmd' non trovato: servirà per le fasi 4-6 (vedi README del kit)."
done

if [[ -e "$TARGET" && -n "$(ls -A "$TARGET" 2>/dev/null)" ]]; then
  echo "La cartella '$TARGET' esiste e non è vuota: scegli un'altra destinazione."
  exit 1
fi

info "Creo il workspace in $TARGET"
mkdir -p "$TARGET"
cp -r "$KIT_DIR/template/." "$TARGET/"
cd "$TARGET"
git init -q -b main
git config --local user.email "${GIT_USER_EMAIL:-mauro.minella@microsoft.com}"
git config --local user.name "${GIT_USER_NAME:-Mauro Minella}"

info "Installo le skill della community (mattpocock/skills) in .agents/skills/"
npx -y skills@latest add mattpocock/skills -a github-copilot -y --copy \
  $(printf -- '-s %s ' "${COMMUNITY_SKILLS[@]}")

info "Controllo le skill Microsoft (microsoft/azure-skills)"
missing=()
for s in "${MICROSOFT_SKILLS[@]}"; do
  if [[ -f "$HOME/.agents/skills/$s/SKILL.md" || -f "$HOME/.copilot/skills/$s/SKILL.md" ]]; then
    echo "  ✓ $s già installata a livello utente (es. estensione GitHub Copilot for Azure)"
  else
    missing+=("$s")
  fi
done
if ((${#missing[@]})); then
  echo "  Installo a livello progetto: ${missing[*]}"
  npx -y skills@latest add microsoft/azure-skills -a github-copilot -y --copy \
    $(printf -- '-s %s ' "${missing[@]}")
fi

info "Commit iniziale dell'harness"
git add -A
if git config user.email >/dev/null && git config user.name >/dev/null; then
  git commit -q -m "chore: harness Agent-Centric (agente, skill, istruzioni)"
  git --no-pager log --oneline -1
else
  warn "Identità git non configurata: file in stage ma commit saltato (git config user.name/user.email)."
fi

cat <<EOF

Workspace pronto. Prossimi passi:
  1. code "$TARGET"
  2. (consigliato) gh repo create smart-meeting-rooms --private --source . --push
     (serve il commit iniziale: se è stato saltato, eseguilo prima)
  3. In Copilot Chat: /setup-matt-pocock-skills   (sceglie il tracker dei ticket)
  4. In Copilot Chat: /hello-world                 (avvia la demo)
EOF
