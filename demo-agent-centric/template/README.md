# Nuovo progetto Agent-Centric

Questo repository è stato preparato con l'harness Agent-Centric dell'organizzazione.
La soluzione verrà costruita da GitHub Copilot attraverso un processo a fasi guidato
da skill.

- Processo e regole: [AGENTS.md](AGENTS.md)
- Stato di avanzamento: [docs/STATUS.md](docs/STATUS.md)
- Avvio: in Copilot Chat digita `/nuovo-progetto <cosa vuoi costruire>`

## Harness

| Componente | Dove |
|---|---|
| Processo (orchestratore) | `.github/agents/solution-orchestrator.agent.md` |
| Skill aziendali | `.github/skills/` |
| Skill della community (Matt Pocock) | `.agents/skills/` (vedi `skills-lock.json`) |
| Skill Microsoft (Azure) | estensione GitHub Copilot for Azure (`~/.agents/skills/`) o `.agents/skills/` |
| Configurazione tracker, etichette, docs di dominio | `docs/agents/` (scritta da `/setup-matt-pocock-skills`) |

Per ripristinare le skill da `skills-lock.json`:

```bash
npx skills@latest experimental_install
```
