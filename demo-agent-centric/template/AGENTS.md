# Istruzioni per gli agenti

Questo progetto viene costruito con il processo **Agent-Centric** dell'organizzazione: la soluzione non nasce da una singola risposta, ma da un processo a fasi in cui ogni fase è guidata da una skill (un ruolo professionale) e produce un artefatto in un file che diventa l'input della fase successiva.

## Processo

Il processo è definito dall'agente [solution-orchestrator](.github/agents/solution-orchestrator.agent.md) e si avvia con `/nuovo-progetto <obiettivo>`.
Lo stato di avanzamento vive in [docs/STATUS.md](docs/STATUS.md): leggilo sempre prima di iniziare e aggiornalo alla fine di ogni fase.

| Fase | Artefatto (input della fase successiva) |
|---|---|
| 1. Discovery | `docs/01-requirements/requirements.yaml` |
| 2. Architecture | `docs/02-architecture/architecture.md` + `docs/adr/` |
| 3. Security | `docs/03-security/security-review.md` |
| 4. Delivery planning | spec + ticket nel tracker configurato in `docs/agents/issue-tracker.md` |
| 5. Implementazione | codice e test |
| 6. Deployment | `azure.yaml`, `infra/`, `.github/workflows/` |

## Regole

- Non saltare fasi: ogni fase legge l'artefatto della fase precedente.
- Le decisioni ad alto impatto (architettura, sicurezza, costi, rilascio) richiedono l'approvazione esplicita dell'utente prima di procedere.
- Non inventare requisiti di business: se un dato manca, chiedilo.
- La piattaforma di destinazione standard dell'organizzazione è **Microsoft Azure**.
- Non scrivere mai segreti nel codice o nei file versionati: usa Key Vault e managed identity.
- Rispetta la baseline aziendale in `.github/skills/security-baseline/`.
