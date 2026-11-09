# Smart Meeting Rooms

Demo "Hello World" del paradigma **Agent-Centric**: una soluzione enterprise per la
prenotazione delle sale riunioni costruita da GitHub Copilot attraverso un processo
a fasi guidato da skill.

- Processo e regole: [AGENTS.md](AGENTS.md)
- Stato di avanzamento: [docs/STATUS.md](docs/STATUS.md)
- Avvio: in Copilot Chat digita `/hello-world`

## Harness

| Componente | Dove |
|---|---|
| Workflow (orchestratore) | `.github/agents/solution-orchestrator.agent.md` |
| Skill aziendali | `.github/skills/` |
| Skill della community (Matt Pocock) | `.agents/skills/` (installate con `npx skills`, vedi `skills-lock.json`) |
| Skill Microsoft (Azure) | estensione GitHub Copilot for Azure (`~/.agents/skills/`) o `.agents/skills/` |

Per ripristinare le skill della community dopo un clone:

```bash
npx skills@latest experimental_install
```
