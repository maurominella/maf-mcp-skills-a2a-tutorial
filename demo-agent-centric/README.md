# Harness Agent-Centric — kit per un approccio standard

Questo kit applica i principi del documento
[Dal paradigma Copilot-Centric al paradigma Agent-Centric](<../docs/it/Dal paradigma Copilot-Centric al paradigma Agent-Centric.docx>)
in un **approccio standard, uguale per ogni progetto**: si prepara l'harness una volta,
poi per ogni nuova soluzione l'utente fornisce **solo l'obiettivo** e il sistema lo guida
attraverso tutte le fasi necessarie.

> Il kit non contiene nessuna applicazione e nessun riferimento a un caso d'uso.
> L'esempio delle sale riunioni del Capitolo 6 è solo il topic scelto per la demo
> (sezione 4): con lo stesso kit si costruisce qualsiasi altra soluzione.
>
> Per presentare il kit ai clienti: [STORYTELLING.md](./STORYTELLING.md) (in inglese).

## 1. L'approccio standard

### Chi decide che cosa

| Momento | Chi | Quante volte | Che cosa |
|---|---|---|---|
| **Preparare l'harness** | l'organizzazione | una volta, poi si migliora nel tempo | *come* si lavora: fasi, approvazioni, skill, standard aziendali |
| **Avviare un progetto** | l'utente | a ogni progetto | solo *che cosa* costruire: una frase con l'obiettivo |
| **Eseguire il processo** | l'harness | a ogni progetto | le domande giuste, gli artefatti, il codice, il deploy |
| **Decidere** | l'utente | a ogni fase | risposte di business, approvazioni, accettazione dei rischi |

Le fasi quindi non le indica l'utente a ogni progetto e nemmeno le inventa l'agente:
sono la **metodologia dell'organizzazione**, scritta una volta nell'orchestratore.
Le domande specifiche del progetto, invece, le ricava l'harness dal dominio.

### Fasi, ruoli e skill

| Fase | Ruolo | Skill | Fonte | Artefatto |
|---|---|---|---|---|
| 1 Discovery | Business Analyst | `requirements-discovery` + `grilling` | **Aziendale** + Community | `docs/01-requirements/requirements.yaml` |
| 2 Architecture | Enterprise Architect | strumenti Azure MCP (`cloudarchitect`, `wellarchitectedframework`, `get_azure_bestpractices`, `pricing`) + `domain-modeling` | **Microsoft** + Community | `docs/02-architecture/architecture.md`, `docs/adr/` |
| 3 Security | Security Architect | `security-baseline` + `entra-app-registration` | **Aziendale** + Microsoft | `docs/03-security/security-review.md` |
| 4 Delivery planning | Delivery Manager | `/to-spec`, `/to-tickets` | Community | spec + ticket nel tracker |
| 5 Implementazione | Software Engineer | `/implement` (+ `tdd`, `code-review`) oppure Copilot coding agent | Community + GitHub | codice e test |
| 6 Deployment | DevOps Engineer | `azure-prepare` → `azure-validate` → `azure-deploy`, `appinsights-instrumentation`, `azure-compliance` | **Microsoft** | `azure.yaml`, `infra/`, pipeline |

Il **processo** che collega le fasi è l'agente `solution-orchestrator`: le skill sono i
ruoli, l'agente è il workflow, i file in `docs/` sono la memoria della sessione.

### Cosa è già pronto e cosa scrive l'organizzazione

| Fonte | Cosa fornisce | Esempi nel kit |
|---|---|---|
| **Microsoft** ([microsoft/azure-skills](https://github.com/microsoft/azure-skills), estensione GitHub Copilot for Azure) | competenza sui servizi Azure: architettura, autenticazione, IaC, deploy, verifica | `azure-prepare`, `azure-deploy`, `entra-app-registration`, strumenti Azure MCP |
| **Community** ([mattpocock/skills](https://github.com/mattpocock/skills)) | tecniche di ingegneria del software indipendenti dalla tecnologia | `grilling`, `to-spec`, `to-tickets`, `tdd`, `code-review` |
| **Organizzazione** (`template/.github/`) | ciò che nessuna skill pubblica conosce: il processo e gli standard interni | `solution-orchestrator`, `requirements-discovery`, `security-baseline` |

Le skill pronte sono **generiche**: non sanno nulla del progetto. Anche le skill aziendali
sono generiche rispetto al progetto, ma specifiche dell'organizzazione:
- `requirements-discovery` definisce le **aree** che ogni discovery deve coprire
  (attori, volumi, integrazioni, canali, compliance…) e il formato dell'output; le domande
  concrete le formula l'agente in base al dominio;
- `security-baseline` contiene la baseline di sicurezza. Il file
  [org-security-baseline.md](./template/.github/skills/security-baseline/references/org-security-baseline.md)
  è un **esempio** da sostituire con quella reale.

Esistono orchestratori già pronti (GitHub Spec Kit, `azure-app-onboard`, il flusso di
Pocock), ma ciascuno copre solo una parte delle fasi. Per questo l'orchestratore è nostro
e **sottile**: non reimplementa nulla, mette in sequenza skill pronte e aggiunge i gate di
approvazione.

### E le funzionalità dell'applicazione?

Non diventano skill. Ciò che l'applicazione deve fare (prenotare, approvare, calcolare…) è
il **prodotto** che l'harness costruisce, non una competenza dell'harness. Se un giorno
un agente dovrà usare quelle funzionalità, diventeranno strumenti MCP o function.

Una nuova skill aziendale ha senso quando emerge una **procedura ripetitiva** che le skill
esistenti non coprono: l'orchestratore le annota in `docs/STATUS.md` come candidate.

## 2. Prerequisiti (una volta per macchina)

| Strumento | Serve per | Verifica |
|---|---|---|
| VS Code + GitHub Copilot (agent mode) | tutto | già funzionante |
| Estensione **GitHub Copilot for Azure** | skill Microsoft e strumenti Azure MCP | `ls ~/.agents/skills` mostra `azure-prepare`, `azure-deploy`, … |
| Node.js 18+ (`npx`) | installare le skill con il CLI `skills` | `npx --version` |
| `git` | repository del progetto | `git --version` |
| GitHub CLI `gh`, autenticato | creare il repo, ticket su GitHub Issues | `gh auth status` |
| Azure CLI `az` + Azure Developer CLI `azd` | fase 6 | `az account show`, `azd version` |
| Subscription Azure con permessi di creazione risorse | fase 6 | |
| Copilot coding agent abilitato sul repo | fase 5, opzione cloud | |

## 3. Preparazione di un nuovo progetto (ogni volta)

Sono sempre gli stessi cinque passi, qualunque sia il progetto. Il passo 5 è l'unico in
cui compare il topic.

| # | Dove | Comando | Cosa fa |
|---|---|---|---|
| 1 | terminale, in questa cartella | `./bootstrap.sh <nome-progetto>` | crea `~/git_repos/<nome-progetto>`, copia [template/](./template), fa `git init` con la tua identità, scarica le skill community e le Microsoft mancanti, registra tutto in `skills-lock.json`, fa il commit iniziale |
| 2 | terminale, nella cartella del progetto | `gh repo create <nome-progetto> --private --source . --push` | crea il repo su GitHub, lo collega come `origin` e fa il primo push (da eseguire **una sola volta**) |
| 3 | nuova finestra VS Code sul progetto (`code ~/git_repos/<nome-progetto>`), Copilot Chat | `/setup-matt-pocock-skills` | legge il repo e, dopo la tua conferma, scrive `docs/agents/` (tracker = GitHub, etichette, docs di dominio), aggiunge la sezione `## Agent skills` ad `AGENTS.md` e crea le etichette mancanti su GitHub |
| 4 | terminale del progetto | `git add . && git commit -m "docs: configurazione skill" && git push` | salva su GitHub la configurazione, necessaria anche al Copilot coding agent nel cloud |
| 5 | Copilot Chat del progetto | `/nuovo-progetto <cosa vuoi costruire>` | avvia l'orchestratore |

Il workspace di un progetto appena preparato:

```text
<nome-progetto>/
├── AGENTS.md                         # regole sempre attive + mappa degli artefatti
├── docs/
│   ├── STATUS.md                     # stato delle fasi (memoria della sessione)
│   └── agents/                       # scritta al passo 3
├── skills-lock.json                  # versioni delle skill installate
├── .github/
│   ├── agents/solution-orchestrator.agent.md   # il processo
│   ├── prompts/nuovo-progetto.prompt.md        # /nuovo-progetto
│   └── skills/                                 # skill AZIENDALI
│       ├── requirements-discovery/
│       └── security-baseline/
└── .agents/skills/                   # skill COMMUNITY (+ Microsoft mancanti)
```

## 4. La demo del workshop: un solo input inventato

Prima del workshop prepari il progetto con i passi 1-4 (es. `./bootstrap.sh smart-meeting-rooms`).
Davanti ai clienti l'unica cosa che inventi è il topic:

```text
/nuovo-progetto Voglio una soluzione enterprise per prenotare sale riunioni
```

Da lì in poi si osserva l'harness applicare le fasi illustrate nella parte teorica:

| Fase | Cosa mostrare | Cosa fai tu, come "cliente" |
|---|---|---|
| Avvio | l'orchestratore **non** risponde con una soluzione: presenta il processo | — |
| 1 Discovery | le domande emergono dal dominio (calendari, collaborazione, sedi, lingue…) senza che nessuno le abbia scritte; poi `requirements.yaml` | rispondi come un business owner; approvi |
| 2 Architecture | servizi Azure scelti e motivati dai requisiti, costi, ADR | approvi o contesti |
| 3 Security | controlli della baseline aziendale, rischi residui | accetti i rischi |
| 4 Delivery | `/to-spec`, `/to-tickets`: issue su GitHub con dipendenze | definisci "finito" |
| 5 Implementazione | `/implement` o ticket assegnati a Copilot nel cloud | controlli test e review |
| 6 Deployment | `azure.yaml`, Bicep, `azd up`, URL pubblicato | autorizzi il rilascio |

Il messaggio per i clienti: *"Le fasi sono il nostro processo standard, deciso una volta
dall'organizzazione. All'harness ho dato solo un obiettivo: le domande, l'architettura,
i controlli di sicurezza e il backlog sono emersi dal dominio, usando competenze di skill
già pronte."* Il giorno dopo, con lo stesso kit, si può partire da un topic completamente
diverso.

Consigli pratici:

- **Prova generale** il giorno prima, con lo stesso topic.
- Le fasi 5 e 6 possono richiedere decine di minuti: dal vivo conviene mostrare le
  fasi 1-4 e riprendere 5-6 da un progetto preparato prima.
- **Ripartire da una fase**: l'orchestratore legge `docs/STATUS.md` e riprende dalla
  prima fase non approvata, anche in una nuova chat.
- **Pulizia**: `azd down --purge` elimina le risorse Azure create.

## 5. Se qualcosa non va

| Sintomo | Causa probabile | Soluzione |
|---|---|---|
| I comandi `/nuovo-progetto`, `/to-spec`… non compaiono | VS Code è aperto su un'altra cartella | apri la radice del progetto come workspace |
| `/to-spec` chiede di eseguire `/setup-matt-pocock-skills` | passo 3 non eseguito | esegui il passo 3 |
| `gh repo create` dice "Name already exists" | il repo è già stato creato | non rilanciarlo: usa `git push` |
| L'architettura non cita stime di costo | strumenti Azure MCP non attivi | verifica l'estensione GitHub Copilot for Azure e gli strumenti abilitati nel picker |
| Mancano le skill community | cartella `.agents/` assente o esclusa | `npx skills@latest experimental_install` |
