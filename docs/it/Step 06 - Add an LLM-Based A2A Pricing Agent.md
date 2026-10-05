<a id="passaggio-6"></a>

# Passaggio 6 — Aggiungere un agente A2A di pricing basato su LLM

L'applicazione deve ora creare il preventivo di una nuova campagna
pubblicitaria a partire da un brief come:

```text
Crea un preventivo per una campagna Travel con 9.200.000 impression.
```

Il calcolo atomico del prezzo appartiene al server MCP. Inizialmente, tuttavia,
i criteri aziendali verranno implementati da un agente A2A dedicato.

## 6.1 Aggiungere `campaign_quote` al server MCP

Aggiungiamo la funzione `campaign_quote` come tool all'interno del file `agent_campaign_mcp.py` che già contiene i tool usati in precedenza:

```python
CPM_BY_SECTOR = {
    "automotive": 18.0,
    "finance": 22.0,
    "fmcg": 12.0,
    "travel": 16.0,
    "telco": 14.0,
}
DEFAULT_CPM = 15.0


@mcp.tool
def campaign_quote(
    sector: Annotated[
        str,
        Field(description="Advertising sector, for example Travel or Finance"),
    ],
    impressions: Annotated[
        int,
        Field(description="Requested number of advertising impressions"),
    ],
) -> dict:
    """Return the authoritative price for one campaign scenario."""
    if impressions <= 0:
        return {"error": "impressions must be greater than zero"}

    normalized_sector = sector.strip().lower()
    cpm_eur = CPM_BY_SECTOR.get(normalized_sector, DEFAULT_CPM)
    used_default_rate = normalized_sector not in CPM_BY_SECTOR
    total_eur = impressions / 1000 * cpm_eur

    return {
        "sector": sector,
        "impressions": impressions,
        "cpm_eur": cpm_eur,
        "total_eur": round(total_eur, 2),
        "used_default_rate": used_default_rate,
    }
```

Mantieniamo volutamente "atomico" questo tool, che calcola esattamente uno scenario e **non** contiene
i criteri di preventivazione di livello superiore, che definiamo nel punto qui sotto. 

## 6.2 Definire i criteri di preventivazione

Il servizio di pricing deve applicare i criteri seguenti:

1. Estrarre settore e impression dalla richiesta.
2. Rifiutare impression mancanti o non positive.
3. Produrre tre scenari:
   - ridotto: 20% di impression in meno;
   - richiesto: le impression richieste;
   - esteso: 20% di impression in più.
4. Usare `campaign_quote` per ogni valore monetario.
5. Non calcolare né modificare mai direttamente il CPM.
6. Avvisare quando viene usata la tariffa predefinita del settore.
7. Presentare i tre scenari in una tabella di confronto.

I criteri sono intenzionalmente più complessi dello schema del tool MCP. In questo modo l'agente A2A è responsabile di una procedura reale, anziché limitarsi a inoltrare i due argomenti (*sector* e *impressions*).<br/>
L'agente è responsabile per estrarre i due argomenti dalla domanda ricevuta; per questo motivo, tale agente deve disporre di un LLM, cosa che in linea teorica non è necessaria per un agente di tipo A2A, o per un hosted agent. Se per esempio avessimo richiesto che la domanda arrivi già codificata, o formalizzata in una forma facilmente interpretabile come regular expressions, avremmo potuto evitare la presenza dell'LLM.<br/>
Tuttavia, **in un agente l'LLM è quasi sempre presente**, ed è il motivo per cui anche in questa implementazione lo abbiamo espressamente previsto. **Ciò permetterà nel passo successivo di apprezzare in maniera rappresentativa il `trasporto` di un agente A2A all'interno di uno skill**.

## 6.3 Creare l'agente A2A di pricing

Creiamo `pricing_a2a_agent.py` con il seguente codice. Notiamo che inseriamo nelle istruzioni di questo agente le policy avanzate che guidano il suo funzionamento, descritte sopra come "Criteri di Preventivazione":

```python
import os
from contextlib import asynccontextmanager

import uvicorn
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
)
from agent_framework import Agent, MCPStreamableHTTPTool
from agent_framework.a2a import A2AExecutor
from agent_framework.openai import OpenAIChatClient
from azure.identity import AzureCliCredential
from dotenv import load_dotenv
from starlette.applications import Starlette

load_dotenv()

pricing_mcp = MCPStreamableHTTPTool(
    name="campaign_pricing_mcp",
    url="http://127.0.0.1:8000/mcp",
    allowed_tools={"campaign_quote"},
    approval_mode="never_require",
    load_prompts=False,
)

pricing_agent = Agent(
    client=OpenAIChatClient(
        model=os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"],
        credential=AzureCliCredential(),
    ),
    name="PricingAgent",
    description="Creates policy-compliant advertising campaign quotations.",
    instructions=(
        "Extract the sector and requested impressions from the user's request. "
        "Reject missing or non-positive impressions. Create three scenarios: "
        "lean with 20 percent fewer impressions, requested with the original "
        "volume, and extended with 20 percent more impressions. Use the "
        "campaign_quote tool for every scenario and every monetary value. "
        "Never calculate or alter CPM values yourself. Warn if a default "
        "sector rate is used. Return a comparison table."
    ),
    tools=[pricing_mcp],
)

pricing_skill = AgentSkill(
    id="campaign-quotation",
    name="Campaign quotation",
    description=(
        "Creates lean, requested, and extended campaign quotation scenarios."
    ),
    tags=["pricing", "advertising", "quotation"],
    examples=[
        "Create a quote for a Travel campaign with 9,200,000 impressions."
    ],
)

agent_card = AgentCard(
    name="AdvertSphere Pricing Agent",
    description="A policy-aware advertising pricing agent.",
    version="1.0.0",
    default_input_modes=["text"],
    default_output_modes=["text"],
    capabilities=AgentCapabilities(),
    skills=[pricing_skill],
    supported_interfaces=[
        AgentInterface(
            url="http://127.0.0.1:9000/",
            protocol_binding="JSONRPC",
        )
    ],
)

handler = DefaultRequestHandler(
    agent_executor=A2AExecutor(pricing_agent),
    task_store=InMemoryTaskStore(),
    agent_card=agent_card,
)


@asynccontextmanager
async def lifespan(app: Starlette):
    async with pricing_agent:
        yield


app = Starlette(
    routes=[
        *create_agent_card_routes(agent_card),
        *create_jsonrpc_routes(handler, rpc_url="/"),
    ],
    lifespan=lifespan,
)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=9000)
```

Come anticipato prima, questo agente è basato su LLM in quanto:

1. il suo LLM interpreta la richiesta in linguaggio naturale;
2. estrae settore e impression;
3. applica i criteri dei tre scenari;
4. richiede tre chiamate al tool MCP con accesso limitato;
5. formatta la risposta.

Dopo aver avviato il server MCP, mettiamo in esecuzione anche l'agente A2A:
```bash
.venv/bin/python labs/solutions/pricing_a2a_agent.py
```
A questo punto, Uvicorn lo espone tramite interfaccia HTTP, e la sua specifica [ASGI (Asynchronous Server Gateway Interface)](https://uvicorn.dev/concepts/asgi/) invoca automaticamente l'oggetto `pricing_agent` passandogli l'input dell'utente ed eventuali informazioni di autenticazione -non presenti in questo tutorial-.<br/>
L'agente usa MAF per esporsi in formato A2A, mettendo a disposizione due percorsi di routing: la home directory (/) per l'invocazione dell'agente e la Agent Card per la sua eventuale visualizzazione sul percorso `/.well-known/agent-card.json`:
```json
{
  "name": "AdvertSphere Pricing Agent",
  "description": "A policy-aware advertising pricing agent.",
  "supportedInterfaces": [
    {
      "url": "http://127.0.0.1:9000/",
      "protocolBinding": "JSONRPC"
    }
  ],
  "version": "1.0.0",
  "capabilities": {

  },
  "defaultInputModes": [
    "text"
  ],
  "defaultOutputModes": [
    "text"
  ],
  "skills": [
    {
      "id": "campaign-quotation",
      "name": "Campaign quotation",
      "description": "Creates lean, requested, and extended campaign quotation scenarios.",
      "tags": [
        "pricing",
        "advertising",
        "quotation"
      ],
      "examples": [
        "Create a quote for a Travel campaign with 9,200,000 impressions."
      ]
    }
  ],
  "preferredTransport": "JSONRPC",
  "protocolVersion": "0.3",
  "url": "http://127.0.0.1:9000/"
}
```



## 6.4 Esporre l'agente A2A come tool

In questa fase l'agente principale -non l'agente A2A- non deve vedere direttamente `campaign_quote`. Quindi il server MCP continua ad esporgli i tre tool definiti originariamente:

```python
campaign_mcp = MCPStreamableHTTPTool(
    name="agent_campaign_mcp",
    url="http://127.0.0.1:8000/mcp",
    allowed_tools={
        "all_campaigns",
        "campaign_metrics",
        "compute_roi",
    },
    approval_mode="never_require",
    load_prompts=False,
)
```

Sempre sull'agente principale -per esempio, appena prima di `async def main() -> None:`- creiamo ora un **proxy A2A** che poi convertiamo subito in un tool MAF:

```python
from agent_framework.a2a import A2AAgent

remote_pricing_agent = A2AAgent(
    name="PricingAgent",
    description="Creates policy-compliant campaign quotation scenarios.",
    url="http://127.0.0.1:9000",
)

pricing_tool = remote_pricing_agent.as_tool(
    name="get_campaign_quote",
    description=(
        "Delegate campaign quotation requests to the authoritative remote "
        "pricing agent."
    ),
    arg_name="request",
    arg_description=(
        "A natural-language quotation request containing a sector and a "
        "requested number of impressions."
    ),
)
```

Ora che il tool è disponibile, aggiungiamo -alla connessione MCP già presente- la registrazione verso il ***tool A2A***:

```python
    maf_agent = Agent(
        client=openai_client,
        name="CampaignAnalyst",
        description="Analyzes advertising campaign performance.",
        instructions=(
            "You are an analyst at AdvertSphere Broadcasting. "
            "Always answer in English, concisely and professionally."
        ),            
        tools=[campaign_mcp, pricing_tool],
        context_providers=[skills_provider],
    )

    async with maf_agent:
        response = await maf_agent.run(
            "Create a quote for a Travel campaign with 9,200,000 impressions."
        )
        print(response.text)
```

### Questo è il risultato che otteniamo, in linea con le istruzioni dell'agente A2A:

---
Here is the quote for the Travel campaign:

| Scenario | Impressions | CPM (EUR) | Total (EUR) |
|---|---:|---:|---:|
| Lean | 7,360,000 | 16.00 | 117,760.00 |
| Requested | 9,200,000 | 16.00 | 147,200.00 |
| Extended | 11,040,000 | 16.00 | 176,640.00 |

Requested quote: **EUR 147,200.00**.

---

Notiamo che il percorso di esecuzione è:

```text
Utente
  ↓
LLM dell'agente principale
  ↓ richiede get_campaign_quote
MAF richiama il proxy A2A
  ↓ HTTP/JSON-RPC
LLM dell'agente di pricing
  ↓ applica i criteri ±20%
Tool MCP campaign_quote, chiamato tre volte
  ↓
L'LLM dell'agente di pricing formatta la risposta delegata
  ↓ HTTP/JSON-RPC
L'LLM dell'agente principale integra il risultato
  ↓
Utente
```

In altri termini, la risposta a questa domanda richiede 4 chiamate all'LLM + 1 chiamata HTTP ad A2A al tool MCP:
- 1 chiamata LLM che indica di invocare il tool A2A
- 1 chiamata HTTP verso A2A (con serializzazione + de-serializzazione dei parametri)
- 1 chiamata LLM all'interno dell'agente A2A, che riceve l'indicazione di invocare il pricing_tool MCP
- 1 chiamata al pricing_tool MCP
- 1 chiamata all'LLM dall'interno dell'agente A2A per passargli la risposta del pricing_tool MCP
- 1 chiamata all'LLM da parte dell'agente principale, che gli passa la risposta dell'agente A2A per fargli generare la risposta finale.

Questa architettura è giustificata quando l'agente di pricing rappresenta un vero confine autonomo: un servizio di proprietà separata, un processo di approvazione indipendente, una negoziazione con stato o un'attività di lunga durata.

Se invece queste esigenze non sussistono, è possibile applicare una ottimizzazione che riduce il numero di passaggi di invocazione, di fatto "concentrando" le attività dell'agente A2A in un nuovo skill caricato dall'agente principale. <br/><br/>

Il prossimo passaggio esamina questa ottimizzazione.

---

