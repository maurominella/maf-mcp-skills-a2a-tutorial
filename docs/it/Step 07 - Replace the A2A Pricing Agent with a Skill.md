<a id="passaggio-7"></a>

# Passaggio 7 — Sostituire l'agente A2A di pricing con uno skill

Come evidenziato nel passaggio precedente, l'implementazione A2A funziona, ma aggiunge:

- un secondo agente distribuito;
- un altro ciclo di ragionamento basato su LLM;
- un round trip A2A HTTP/JSON-RPC;
- serializzazione e deserializzazione;
- un ulteriore confine per ciclo di vita, integrità, autenticazione e nuovi tentativi.

I criteri di preventivazione sono abbastanza deterministici da poter essere trasferiti in una skill.<br/>
Tale skill indicherà all'agente principale di chiamare direttamente `campaign_quote`, di fatto eliminando l'agente A2A dall'architettura.

Questo non elimina l'uso dell'LLM. L'LLM principale continua a:

- riconoscere la richiesta di preventivo;
- richiedere la skill di preventivazione;
- interpretarne i criteri;
- estrarre settore e impression;
- calcolare i volumi di impression ±20%;
- richiedere le tre chiamate al tool MCP;
- formattare la risposta finale.

Elimina però il secondo agente basato su LLM e il passaggio attraverso il
servizio A2A.

## 7.1 Creare la skill di preventivazione

Creiamo una nuova cartella per il nuovo skill, con all'interno il file SKILL.md:

```text
skills/campaign-quotation-policy/SKILL.md
```

```markdown
---
name: campaign-quotation-policy
description: >-
  Use for campaign prices, quotations, cost estimates, budget scenarios, or
  advertising briefs that specify a sector and a target number of impressions.
---

# Campaign quotation policy

Create a policy-compliant campaign quotation from authoritative pricing data.

## Required tool

Use `campaign_quote` for every scenario and every monetary value. Never
calculate, infer, or modify CPM rates or campaign prices directly.

## Required inputs

- Advertising sector
- Requested number of impressions

If either input is missing, ask the user for it before requesting a quote.
Reject zero or negative impression volumes.

## Procedure

1. Extract the sector and requested impressions from the user's request.
2. Calculate only the impression volumes for these scenarios:
   - lean: 20% fewer impressions than requested;
   - requested: the original number of impressions;
   - extended: 20% more impressions than requested.
3. Round scenario impressions to whole numbers.
4. Call `campaign_quote` once for each scenario.
5. Use the CPM and total price returned by the tool without alteration.
6. If the tool reports `used_default_rate=true`, state clearly that the sector
   was priced with the default CPM.
7. Do not describe the result as an approved commercial offer.

## Output format

Return:

1. A one-sentence summary
2. A table with scenario, impressions, CPM, and total price
3. Any default-rate warning
4. A note that the figures are indicative quotations
```

La skill fa riferimento a `campaign_quote`, ma non registra il tool. Il tool
deve comunque essere reso disponibile attraverso la connessione MCP
dell'agente principale.

## 7.2 Fornire all'agente principale accesso diretto a `campaign_quote`

Estendiamo `allowed_tools` aggiungendo il tool `campaign_quote`:

```python
campaign_mcp = MCPStreamableHTTPTool(
    name="agent_campaign_mcp",
    url="http://127.0.0.1:8000/mcp",
    allowed_tools={
        "all_campaigns",
        "campaign_metrics",
        "compute_roi",
        "campaign_quote",
    },
    approval_mode="never_require",
    load_prompts=False,
)
```

Entrambe le cartelle delle skill vengono individuate automaticamente perché il provider punta alla cartella padre comune, quindi questa parte resta invariata:

```python
skills_provider = SkillsProvider.from_paths(
    Path(__file__).parent / "skills",
    disable_load_skill_approval=True,
)
```

Rimuoviamo il proxy A2A e il relativo tool:

```python
    maf_agent = Agent(
        client=openai_client,
        name="CampaignAnalyst",
        description="Analyzes advertising campaign performance.",
        instructions=(
            "You are an analyst at AdvertSphere Broadcasting. "
            "Always answer in English, concisely and professionally."
        ),            
        tools=[campaign_mcp],
        context_providers=[skills_provider],
    )

    async with maf_agent:
        response = await maf_agent.run(
            "Create a quote for a Pets campaign with 10,000,000 impressions."
        )
        print(response.text)
```

### Eseguiamo il nuovo test, che evidenzia il fatto che è stato utilizzato il fattore moltiplicativo (CPM) di default in quanto la categoria **Pets** non esiste:
---
Here is an indicative quotation for a Pets campaign at 10,000,000 impressions.

| Scenario | Impressions | CPM | Total price |
|---|---:|---:|---:|
| Lean | 8,000,000 | €15.00 | €120,000.00 |
| Requested | 10,000,000 | €15.00 | €150,000.00 |
| Extended | 12,000,000 | €15.00 | €180,000.00 |

Default-rate warning: the Pets sector was priced with the default CPM.

These figures are indicative quotations, not an approved commercial offer.

---

Il percorso di esecuzione ottimizzato è:

```text
Utente
  ↓
LLM dell'agente principale
  ↓ richiede load_skill("campaign-quotation-policy")
MAF carica il file SKILL.md locale
  ↓
L'LLM dell'agente principale applica i criteri ±20%
  ↓ richiede campaign_quote tre volte
MAF richiama direttamente il server MCP
  ↓
L'LLM dell'agente principale formatta la risposta finale
  ↓
Utente
```

L'agente A2A di pricing non è più necessario:

```text
Prima:
Agente principale
  └── Agente A2A di pricing
        └── Tool MCP campaign_quote

Dopo:
Agente principale
  ├── Skill campaign-quotation-policy
  └── Tool MCP campaign_quote
```

---

