# Demo "Hello World" Agent-Centric — kit di preparazione

Questo kit prepara da zero l'ambiente per la demo del **Capitolo 6 — Il nostro Hello World**
del documento [Dal paradigma Copilot-Centric al paradigma Agent-Centric](<../docs/it/Dal paradigma Copilot-Centric al paradigma Agent-Centric.docx>):
una soluzione enterprise per la prenotazione delle sale riunioni, costruita da GitHub Copilot
in VS Code attraverso le fasi Discovery → Architecture → Security → Delivery planning →
Implementazione → Deployment.

> Il kit **non** contiene la soluzione delle sale riunioni: quella la costruisce l'harness
> durante la demo. Il kit contiene l'**harness**: skill, workflow, istruzioni e il file
> system in cui ogni fase deposita il proprio artefatto.

## 1. La risposta breve: quali skill, da dove

| Fase (cap. 6) | Ruolo | Skill | Fonte | Perché questa |
|---|---|---|---|---|
| 6.1 Discovery | Business Analyst | `requirements-discovery` + `grilling` | **Aziendale** + Community | `grilling` (Pocock) è un'ottima tecnica di intervista generica; la skill aziendale aggiunge la checklist (sedi, Teams, Outlook, mobile, lingue, GDPR) e il contratto YAML. |
| 6.2 Architecture | Enterprise Architect | strumenti Azure MCP `cloudarchitect`, `wellarchitectedframework`, `get_azure_bestpractices`, `pricing` + `domain-modeling` | **Microsoft** + Community | Microsoft conosce i servizi Azure e il Well-Architected Framework; `domain-modeling` (Pocock) registra le decisioni come ADR. |
| 6.3 Security | Security Architect | `security-baseline` + `entra-app-registration` | **Aziendale** + Microsoft | La baseline (naming, tag, regioni EU, retention) è conoscenza dell'organizzazione; Microsoft fornisce il know-how su Entra ID. |
| 6.4 Delivery planning | Delivery Manager | `/to-spec`, `/to-tickets` | Community | Producono spec con user story e ticket con dipendenze direttamente nel tracker. |
| 6.5 Coding agent | Software Engineer | `/implement` (+ `tdd`, `code-review`) oppure Copilot coding agent | Community + GitHub | In locale o in cloud sui ticket `ready-for-agent`. |
| 6.6 Deployment | DevOps Engineer | `azure-prepare` → `azure-validate` → `azure-deploy`, `appinsights-instrumentation`, `azure-compliance` | **Microsoft** | `azure.yaml`, Bicep, pipeline, deploy con `azd`, verifica post-rilascio. |
| — | (meta) | `discover-azure-skills` | Microsoft | Cerca nel catalogo Microsoft le skill Azure adatte a un compito. |

Il **workflow** che collega le fasi è l'agente `solution-orchestrator`: le skill sono i ruoli,
l'agente è il processo, i file in `docs/` sono la memoria della sessione.

### "Le skill di discovery Microsoft" — attenzione al nome

- `discover-azure-skills` **non** raccoglie requisiti: è una *meta-skill* che scopre e
  consiglia altre skill Azure da installare. Ottima da mostrare in demo, ma per la fase 6.1
  non basta.
- `azure-app-onboard` e gli agenti `azure-project-plan` → `azure-project-scaffold` →
  `azure-project-integrate` (estensione GitHub Copilot for Azure) fanno discovery, ma
  **orientata alla tecnologia** (stack, servizi, budget) e portano avanti un loro processo
  end-to-end. Sono un'ottima alternativa "tutto Microsoft", ma non fanno le domande di
  business del cap. 6.1 e salterebbero i nostri gate: per questo l'orchestratore non li usa.

### Devo creare io una skill per prenotare le sale riunioni?

**No.** Prenotare una sala è una **funzionalità dell'applicazione** che l'harness deve costruire,
non una competenza dell'harness. Secondo la regola del cap. 3 è un'operazione piccola e
deterministica: nell'app diventerà un'API (`POST /bookings`) e, se in futuro un agente dovrà
prenotare sale, uno **strumento MCP** o una function — non una skill.

Le skill da scrivere sono quelle che codificano **come lavora la tua organizzazione** (cap. 4.3).
In questo kit ce ne sono solo due, volutamente:

- `requirements-discovery` — le domande che il tuo team fa sempre + il formato YAML atteso;
- `security-baseline` — la baseline di sicurezza aziendale (file di esempio da personalizzare
  in `template/.github/skills/security-baseline/references/org-security-baseline.md`).

## 2. Prerequisiti

| Strumento | Serve per | Verifica |
|---|---|---|
| VS Code + GitHub Copilot (agent mode) | tutto | già funzionante |
| Node.js 18+ (`npx`) | installare le skill con il CLI `skills` | `npx --version` |
| Estensione **GitHub Copilot for Azure** | skill Microsoft e strumenti Azure MCP | `ls ~/.agents/skills` mostra `azure-prepare`, `azure-deploy`, … |
| `git` | repository della demo | `git --version` |
| GitHub CLI `gh` | fase 4 (ticket su GitHub Issues) | `gh auth status` |
| Azure CLI `az` + Azure Developer CLI `azd` | fase 6 | `az account show`, `azd version` |
| Subscription Azure con permessi di creazione risorse | fase 6 | |
| Repository GitHub con Copilot coding agent abilitato | fase 5, opzione cloud | |

## 3. Preparazione (una volta, ~5 minuti)

```bash
cd demo-agent-centric
./bootstrap.sh ~/git_repos/smart-meeting-rooms
```

Lo script:

1. copia [template/](./template) nella nuova cartella e inizializza git;
2. installa a livello progetto in `.agents/skills/` le skill della community di
   [Matt Pocock](https://github.com/mattpocock/skills): `setup-matt-pocock-skills`, `grilling`,
   `grill-me`, `domain-modeling`, `to-spec`, `to-tickets`, `implement`, `tdd`, `code-review`;
3. per le skill Microsoft ([microsoft/azure-skills](https://github.com/microsoft/azure-skills))
   usa quelle già installate a livello utente dall'estensione e installa nel progetto solo
   quelle mancanti (tipicamente `discover-azure-skills`);
4. registra tutto in `skills-lock.json` e fa il commit iniziale.

Poi:

```bash
cd ~/git_repos/smart-meeting-rooms
gh repo create smart-meeting-rooms --private --source . --push   # consigliato
code .
```

In Copilot Chat esegui una volta **`/setup-matt-pocock-skills`** e scegli il tracker:
**GitHub** se hai creato il repo (necessario per l'opzione cloud della fase 5), altrimenti
**Local markdown** (i ticket finiscono in `.scratch/`).

Il workspace risultante:

```text
smart-meeting-rooms/
├── AGENTS.md                         # regole sempre attive + mappa degli artefatti
├── docs/STATUS.md                    # stato delle fasi (memoria della sessione)
├── skills-lock.json                  # versioni delle skill installate
├── .github/
│   ├── agents/solution-orchestrator.agent.md   # il workflow
│   ├── prompts/hello-world.prompt.md           # /hello-world avvia la demo
│   └── skills/                                 # skill AZIENDALI
│       ├── requirements-discovery/
│       └── security-baseline/
└── .agents/skills/                   # skill COMMUNITY (+ Microsoft mancanti)
```

## 4. Copione della demo

| # | Cosa fai | Cosa mostri al pubblico | La tua responsabilità (cap. "Cosa dobbiamo fare noi") |
|---|---|---|---|
| 0 | Mostri in Explorer `.github/skills/` e `.agents/skills/`, poi digiti `/` in Copilot Chat | Le tre famiglie di skill: aziendali, community, Microsoft | Scegliere ambiente e perimetro |
| 0b | *(opzionale)* "Quali skill Azure mi servono per una web app con Entra ID e Azure SQL?" | `discover-azure-skills` interroga il catalogo Microsoft | |
| 1 | `/hello-world` | L'orchestratore **non** risponde: avvia `requirements-discovery`, domande a round con risposta raccomandata | Rispondere con conoscenza del business: 500 utenti, Milano e Roma, Teams, Outlook, IT/EN |
| 1✓ | Approvi | `docs/01-requirements/requirements.yaml`, `STATUS.md` aggiornato, commit | |
| 2 | Lasci proseguire | Architettura con motivazioni e costi, ADR in `docs/adr/` | Approvare o contestare le scelte |
| 3 | Lasci proseguire | `security-review.md`: tabella controlli SEC-01…SEC-12, rischi residui | Accettare i rischi residui |
| 4 | Digiti `/to-spec`, poi `/to-tickets` | Spec con user story e ticket con dipendenze su GitHub Issues | Definire cosa significa "finito" |
| 5 | Locale: `/implement #<ticket>` — Cloud: assegni i ticket a **Copilot** su GitHub | Codice, test, PR | Controllare le evidenze (test, review) |
| 6 | Lasci proseguire, approvi subscription/regione/costo | `azure.yaml`, `infra/*.bicep`, pipeline, `azd up`, URL pubblicato | Autorizzare il rilascio |

Consigli pratici:

- **Prova generale**: esegui l'intera demo il giorno prima. Le fasi 5 e 6 possono richiedere
  decine di minuti: in diretta conviene mostrare dal vivo le fasi 1-4 e per 5-6 riprendere
  da un branch già pronto, avviando solo un ticket e `azd provision` dal vivo.
- **Ripartire da una fase**: l'orchestratore legge `docs/STATUS.md` e riprende dalla prima
  fase non approvata, anche in una nuova chat.
- **Modello**: seleziona un modello recente nel picker; il messaggio del cap. 5 si dimostra
  bene ripetendo la fase 1 con un modello diverso e confrontando i `requirements.yaml`.
- **Pulizia**: al termine `azd down --purge` elimina le risorse Azure create.

## 5. Se qualcosa non va

| Sintomo | Causa probabile | Soluzione |
|---|---|---|
| Le skill non compaiono digitando `/` | workspace aperto sulla cartella sbagliata | apri in VS Code la radice `smart-meeting-rooms/` |
| Una skill appare due volte | installata sia come plugin sia con `npx skills` | tienine una sola delle due installazioni |
| `/to-spec` chiede di eseguire `/setup-matt-pocock-skills` | tracker non configurato | esegui `/setup-matt-pocock-skills` |
| `gh issue create --label …` fallisce | le label `ready-for-agent`, `needs-triage`… non esistono nel repo | creale con `gh label create ready-for-agent` (ecc.) |
| L'architettura non cita stime di costo | strumenti Azure MCP non attivi | verifica l'estensione GitHub Copilot for Azure e gli strumenti abilitati nel picker |
| Mancano le skill community (es. hai escluso `.agents/` dal repo) | ripristino da `skills-lock.json` necessario | `npx skills@latest experimental_install` |
