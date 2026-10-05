# Da un agente MAF a una soluzione completa basata sulle skill

Gli AI skill sono stati [annunciati da Antrhopic](https://claude.com/blog/skills) a ottobre 2025 e si sono diffusi molto rapidamente. Ora il punto chiave -e per nulla scontato- è capire dove ha senso posizionarli, perché le funzionalità che si portano dietro in realtà esistevano anche prima, senza gli skill. Quindi si potrebbero considerare un'alternativa al system prompt, o ai tool, e in certe casi addirittura ha senso valutarli come un modo per ottimizzare sistemi multiagentici costruiti intorno ad A2A.
Quindi, per comprendere come gestire queste possibili sovrapposizioni, e imparare però anche come utilizzarli nel concreto, ho predisposto questo tutorial, rivolto a sviluppatori e solution architect, che parte da un agente minimale basato su Microsoft Agent Framework (MAF) e arriva a una soluzione completa basata sugli skill, passando attraverso Function Calling, Tools, server MCP e A2A.

Lo scenario segue un analista di AdvertSphere Broadcasting, un'azienda fittizia che vende spazi pubblicitari per un network televisivo.

Attraverso sette passaggi incrementali, che troviamo descritti e implementati in questo repo pubblico su GitHub, costruiremo una soluzione completa, partendo da scratch, e che fornirà all'analista di questa azienda
- l'accesso a dati autorevoli sulle campagne, 
- la revisione uniforme del portafoglio, 
- e un servizio di creazione preventivi.

Nell'ultima parte del tutorial faremo prima l'implementazione seguendo un approccio multiagentico basato su [A2A, annunciato da Google sei mesi prima degli skill](https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/); questo approccio resta validissimo anche oggi, ma grazie agli skill abbiamo ora l'opportunità di valutare in certi casi una possibile ottimizzazione, di fatto "trasportando" le capacità dell'agente A2A all'interno di uno skill, e sfruttando come LLM quello dell'agente orchestratore. 

Relativamente al tutorial, potete procedere nell'ordine dei punti se volete arrivare ad implementare la soluzione E2E. Oppure se lo usate come un riferimento architetturale, utilizzate il sommario per raggiungere direttamente il pattern o il confronto che vi interessa.

Quindi adesso partiamo direttamente con l'implementazione del primo punto, ovvero la creazione di un agente minimale con Agent Framework.

## Sommario

- [Prerequisiti](#prerequisiti)
- [Passaggio 1 — Creare un agente MAF minimale](#passaggio-1)
- [Passaggio 2 — Aggiungere tool funzione locali](#passaggio-2)
- [Passaggio 3 — Spostare i tool in un server MCP](#passaggio-3)
- [Passaggio 4 — Osservare un'orchestrazione incoerente](#passaggio-4)
- [Passaggio 5 — Aggiungere la skill `campaign-performance-review`](#passaggio-5)
- [Passaggio 6 — Aggiungere un agente A2A di pricing basato su LLM](#passaggio-6)
- [Passaggio 7 — Sostituire l'agente A2A di pricing con una skill](#passaggio-7)
- [Confrontare le versioni A2A e basata sulle skill](#confronto)
- [Conclusioni](#conclusioni)

<a id="prerequisiti"></a>

## Prerequisiti

Questo tutorial presuppone:

- Python 3.13 o versione successiva;
- `agent-framework==1.19.0`;
- `fastmcp==3.4.7`;
- `a2a-sdk==1.1.5`;
- `uvicorn==0.54.0`;
- una distribuzione Azure OpenAI configurata tramite le variabili di ambiente
  esistenti;
- una sessione Azure CLI autenticata.

Gli esempi utilizzano le variabili seguenti:

```text
AZURE_OPENAI_ENDPOINT
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME
```

La struttura di progetto suggerita è:

```text
labs/solutions/
├── agent_campaign_mcp.py
├── campaign_data.py
├── campaign_agent.py
├── pricing_a2a_agent.py
└── skills/
    ├── campaign-performance-review/
    │   └── SKILL.md
    └── campaign-quotation-policy/
        └── SKILL.md
```

I nomi esatti dei file non sono importanti. Ciò che conta è il modo in cui le
responsabilità si spostano nel corso dei sette passaggi.

---

<a id="passaggio-1"></a>

## Passaggio 1 — Creare un agente MAF minimale

Inizia con un agente che dispone soltanto di:

- un nome;
- istruzioni;
- un client LLM.

Non dispone di tool, connessioni MCP, skill o agenti A2A.

```python
import asyncio
import os

from agent_framework import Agent
from agent_framework.openai import OpenAIChatClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()


async def main() -> None:
    openai_client = OpenAIChatClient(
        model=os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"],
        credential=DefaultAzureCredential(exclude_environment_credential=True),
    )

    maf_agent = Agent(
        client=openai_client,
        name="CampaignAnalyst",
        description="Analyzes advertising campaign performance.",
        instructions=(
            "You are an analyst at AdvertSphere Broadcasting. "
            "Always answer in English, concisely and professionally."
        ),
    )

    answer = await maf_agent.run(
        "Review campaign CMP-004 and calculate its ROI."
    )
    print(answer.text)


if __name__ == "__main__":
    asyncio.run(main())
```

L'esempio viene eseguito senza errori. Tuttavia, l'agente può spiegare il ROI in generale, ma non può recuperare dati autorevoli sulle campagne. Ci attendiamo quindi una risposta del tipo *I can help calculate ROI for CMP-004, but I don’t have the campaign's performance data in this chat*.<br/>
In questa fase, l'architettura è:

```text
Utente
  ↓
Agente MAF
  ↓
LLM
```

---

<a id="passaggio-2"></a>

## Passaggio 2 — Aggiungere tool funzione locali

Aggiungiamo tre funzioni deterministiche allo stesso file sorgente:

- `all_campaigns`;
- `campaign_metrics`;
- `compute_roi`.

In questo caso, i due metodi `all_campaigns` e `campaign_metrics` sono funzioni implementate nel file `asb_campaign.py` a puro scopo dimostrativo per consentire l'esecuzione dell'esercizio. In una situazione reale, queste funzioni dovrebbero attingere al dataset reale delle campagne.<br/>
Questo il codice da aggiungere all'inizio del modulo, subito dopo l'istruzione `load_dotenv()`:

```python
from typing import Annotated
from pydantic import Field
from asb_campaign import get_campaign, list_campaigns


def all_campaigns() -> list:
    """List the id, client, and sector of every campaign."""
    return list_campaigns()

def campaign_metrics(
    campaign_id: Annotated[
        str,
        Field(description="Campaign identifier, for example CMP-004"),
    ],
) -> dict:
    """Return the authoritative metrics for one campaign."""
    campaign = get_campaign(campaign_id)
    if campaign is None:
        return {"error": f"Campaign {campaign_id} was not found."}
    return campaign

def compute_roi(
    revenue_eur: Annotated[
        float,
        Field(description="Campaign revenue in EUR"),
    ],
    budget_eur: Annotated[
        float,
        Field(description="Campaign budget in EUR"),
    ],
) -> dict:
    """Calculate ROI as a percentage from revenue and budget."""
    if budget_eur <= 0:
        return {"error": "budget_eur must be greater than zero"}

    roi_pct = (revenue_eur - budget_eur) / budget_eur * 100
    return {"roi_pct": round(roi_pct, 1)}
```

L'Agent Framework può registrare i nomi di queste funzioni durante la creazione dell'agente, associandole attraverso un array al parametro `tools` della classe `agent`:

```python
maf_agent = Agent(
    client=openai_client,
    name="CampaignAnalyst",
    description="Analyzes advertising campaign performance.",
    instructions=(
        "You are an analyst at AdvertSphere Broadcasting. "
        "Always answer in English, concisely and professionally."
    ),
    tools=[all_campaigns, campaign_metrics, compute_roi],
)
```

L'LLM riceve ora gli schemi generati dalle funzioni, dalle annotazioni e dalle
docstring. Può richiedere una chiamata a un tool, mentre MAF esegue
effettivamente la funzione.

```text
Utente
  ↓
L'LLM richiede campaign_metrics
  ↓
MAF esegue la funzione Python
  ↓
MAF restituisce il risultato del tool all'LLM
  ↓
L'LLM produce la risposta
```

Questa progettazione è appropriata finché le funzionalità appartengono alla
stessa applicazione e non devono essere condivise.

---

<a id="passaggio-3"></a>

## Passaggio 3 — Spostare i tool in un server MCP

Spostiamo ora le tre funzioni in un server MCP separato denominato
`agent_campaign_mcp`.

Crea `agent_campaign_mcp.py`:

```python
import logging
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from asb_campaign import get_campaign, list_campaigns

logger = logging.getLogger(__name__)
mcp = FastMCP("AdvertSphere Campaign MCP")


@mcp.tool
def all_campaigns() -> list:
    """List the id, client, and sector of every campaign."""
    logger.info("All campaigns requested")
    return list_campaigns()


@mcp.tool
def campaign_metrics(
    campaign_id: Annotated[
        str,
        Field(description="Campaign identifier, for example CMP-004"),
    ],
) -> dict:
    """Return the authoritative metrics for one campaign."""
    logger.info("Campaign metrics requested for %s", campaign_id)
    campaign = get_campaign(campaign_id)
    if campaign is None:
        return {"error": f"Campaign {campaign_id} was not found."}
    return campaign


@mcp.tool
def compute_roi(
    revenue_eur: Annotated[
        float,
        Field(description="Campaign revenue in EUR"),
    ],
    budget_eur: Annotated[
        float,
        Field(description="Campaign budget in EUR"),
    ],
) -> dict:
    """Calculate ROI as a percentage from revenue and budget."""
    if budget_eur <= 0:
        return {"error": "budget_eur must be greater than zero"}

    roi_pct = (revenue_eur - budget_eur) / budget_eur * 100
    return {"roi_pct": round(roi_pct, 1)}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    mcp.run(transport="http", host="127.0.0.1", port=8000)
```

Avviamo il server MCP:

```bash
.venv/bin/python labs/solutions/agent_campaign_mcp.py
```
```text
[10/05/26 14:50:05] INFO     Starting MCP server 'AdvertSphere Campaign MCP' with transport 'http' on              transport.py:361
                             http://127.0.0.1:8000/mcp                                                                             
INFO:     Started server process [100965]
INFO:     Waiting for application startup.
INFO:mcp.server.streamable_http_manager:StreamableHTTP session manager started
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

Lato agente, all'interno di `async def main()`:
- aggiungiamo il riferimento al server MCP utilizzando `MCPStreamableHTTPTool`
- sostituiamo i tre tool locali dell'agente principale con una connessione MCP
- wrappiamo l'esecuzione dell'agente in una operazione asincrona

```python
async def main() -> None:
    from agent_framework import Agent, MCPStreamableHTTPTool
    campaign_mcp = MCPStreamableHTTPTool(
        name="agent_campaign_mcp",
        url="http://127.0.0.1:8000/mcp",
        allowed_tools={
            "all_campaigns",
            "campaign_metrics",
            "compute_roi",
        },
        approval_mode="never_require",
        load_prompts=False,  # When True, also load MCP prompt resources, not only tools.
    )
    
    openai_client = OpenAIChatClient(
        model=os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"],
        credential=DefaultAzureCredential(exclude_environment_credential=True),
    )

    maf_agent = Agent(
        client=openai_client,
        name="CampaignAnalyst",
        description="Analyzes advertising campaign performance.",
        instructions=(
            "You are an analyst at AdvertSphere Broadcasting. "
            "Always answer in English, concisely and professionally."
        ),
        tools=[campaign_mcp],
    )

    async with maf_agent:
        answer = await maf_agent.run(
            "Between CMP-004 and CMP-005, which campaign has the better ROI?"
        )
    print(answer.text)
    return answer.text
```

Notiamo che `tools=[campaign_mcp]` non nasconde i singoli tool all'LLM. Durante
l'individuazione MCP, MAF ottiene i nomi, le descrizioni e gli schemi di input
esposti dal server. Il modello continua a vedere le tre funzionalità
richiamabili:

```text
all_campaigns()
campaign_metrics(campaign_id)
compute_roi(revenue_eur, budget_eur)
```

Sono cambiate soltanto l'implementazione e la posizione di esecuzione:

```text
Tool locali:
LLM → MAF → funzione Python

Tool MCP:
LLM → MAF → richiesta MCP → server MCP → funzione Python
```

---

<a id="passaggio-4"></a>

## Passaggio 4 — Osservare un'orchestrazione incoerente

Le domande atomiche vengono in genere gestite bene perché gli schemi dei tool
rendono evidente l'operazione richiesta:

```text
Qual è il ROI di CMP-004?
```

Il percorso previsto è semplice:

```text
campaign_metrics("CMP-004")
→ compute_roi(revenue_eur, budget_eur)
→ risposta
```

Usa ora una domanda più ampia:

```text
Esamina l'intero portafoglio di campagne e consiglia quale campagna dovrebbe
ricevere un budget aggiuntivo nel prossimo trimestre.
```

L'agente dispone delle funzionalità necessarie per rispondere, ma non gli è
stata fornita una procedura di revisione standard. Tra esecuzioni ripetute o
modelli diversi, potrebbe:

- classificare le campagne soltanto in base al ROI;
- considerare i ricavi ma ignorare le conversioni;
- esaminare soltanto un sottoinsieme delle campagne;
- calcolare autonomamente alcuni valori di ROI anziché usare `compute_roi`;
- omettere i limiti relativi alla qualità dei dati;
- produrre una tabella in un'esecuzione e testo discorsivo in un'altra;
- consigliare una campagna senza spiegare il compromesso tra redditività e
  scala.

Questo non è un problema di MCP. MCP espone correttamente le funzionalità.
L'elemento mancante è una procedura di dominio riutilizzabile.

Esegui più volte lo stesso prompt ed esamina `response.messages`:

```python
prompt = (
    "Review the entire campaign portfolio and recommend which campaign "
    "should receive additional budget next quarter."
)

async with agent:
    for run_number in range(1, 4):
        response = await agent.run(prompt)
        print(f"\n--- Run {run_number} ---")
        print(response.text)

        for message in response.messages:
            print(message)
```

Non affermare che il comportamento debba necessariamente essere incoerente a
ogni esecuzione. Misura invece se la risposta soddisfa con regolarità criteri
espliciti:

| Criterio | Risultato previsto senza una skill? |
|---|---|
| Viene esaminata ogni campagna | Non garantito |
| Ogni ROI usa `compute_roi` | Non garantito |
| Vengono considerate sia la redditività sia la scala | Non garantito |
| Vengono dichiarati i limiti dei dati | Non garantito |
| Viene usata la stessa struttura di output | Non garantito |

---

<a id="passaggio-5"></a>

## Passaggio 5 — Aggiungere lo skill `campaign-performance-review`

Crea:

```text
skills/campaign-performance-review/SKILL.md
```

con il contenuto seguente:

```markdown
---
name: campaign-performance-review
description: >-
  Da usare per revisioni di campagne, analisi di portafoglio, classifiche,
  raccomandazioni di investimento e confronti relativi a redditività, scala,
  efficienza o qualità dei dati.
---

# Revisione delle prestazioni delle campagne

Applica un metodo coerente e basato su evidenze per valutare le prestazioni
delle campagne. Basa ogni conclusione sui dati recuperati delle campagne e
rendi espliciti i compromessi.

## Tool necessari

- Usa `all_campaigns` per identificare le campagne nel portafoglio.
- Usa `campaign_metrics` per recuperare budget, impression, conversioni e
  ricavi di una campagna.
- Usa `compute_roi` per calcolare il ROI dai valori recuperati di ricavi e
  budget.

Non inventare risultati mancanti dei tool e non sostituire `compute_roi` con un
calcolo manuale del ROI. Se un tool necessario non è disponibile o non
funziona, identifica le informazioni mancanti e limita di conseguenza
l'analisi.

## Procedura

1. Per un'analisi dell'intero portafoglio, chiama `all_campaigns`; per una
   revisione mirata, inizia dagli identificatori di campagna forniti
   dall'utente.
2. Chiama `campaign_metrics` per ogni campagna inclusa nell'analisi.
3. Chiama `compute_roi` per ogni campagna i cui ricavi e budget sono validi.
4. Valuta ogni campagna in base a:
   - redditività: ROI;
   - scala: ricavi e conversioni;
   - efficienza: conversioni rispetto al budget;
   - qualità dei dati: valori mancanti o non validi.
5. Non dichiarare una campagna "migliore" basandoti soltanto sul ROI, a meno
   che l'utente richieda esplicitamente un confronto basato solo sul ROI.
6. Se ROI e scala indicano vincitori diversi, spiega il compromesso.
7. Se i dati necessari sono mancanti o non validi, identifica le metriche
   interessate e non classificare la campagna in base a tali metriche.

## Formato di output

Per una revisione del portafoglio o una raccomandazione di investimento,
restituisci:

1. Sintesi esecutiva
2. Tabella delle metriche
3. Compromessi
4. Raccomandazione
5. Limiti dei dati

Per un confronto mirato, fornisci una tabella concisa delle metriche, spiega i
compromessi pertinenti e rispondi direttamente alla domanda dell'utente.
```

Registra un `SkillsProvider`:

```python
async def main() -> None:
    from pathlib import Path

    from agent_framework import SkillsProvider

    skills_provider = SkillsProvider.from_paths(
        Path(__file__).parent / "skills",
        disable_load_skill_approval=True,
    )

    from agent_framework import Agent, MCPStreamableHTTPTool
    campaign_mcp = MCPStreamableHTTPTool(
        name="agent_campaign_mcp",
        url="http://127.0.0.1:8000/mcp",
        allowed_tools={
            "all_campaigns",
            "campaign_metrics",
            "compute_roi",
        },
        approval_mode="never_require",
        load_prompts=False,  # When True, also load MCP prompt resources, not only tools.
    )
    
    openai_client = OpenAIChatClient(
        model=os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"],
        credential=DefaultAzureCredential(exclude_environment_credential=True),
    )

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
            "Review the entire campaign portfolio and recommend which campaign "
            "should receive additional budget next quarter."
        )
        print(response.text)

    return response.text

```

La skill segue la divulgazione progressiva:

1. MAF pubblicizza soltanto `name` e `description`.
2. L'LLM determina che la skill è pertinente.
3. L'LLM richiede `load_skill("campaign-performance-review")`.
4. MAF carica e restituisce il corpo completo di `SKILL.md`.
5. L'LLM interpreta la procedura e richiede le chiamate ai tool MCP.
6. MAF esegue tali chiamate e restituisce i risultati.
7. L'LLM produce la risposta standardizzata.

La skill non registra i tool. Nomina e orchestra tool che devono essere già
disponibili tramite `Agent(tools=[...])`.

Ripetiamo il prompt del Passaggio 4 e valuta gli stessi criteri. Il miglioramento
previsto non consiste nell'acquisizione improvvisa di nuovi dati o calcoli da
parte dell'agente. Il vantaggio è che le funzionalità esistenti vengono usate
attraverso un flusso di lavoro coerente e riutilizzabile.

Tipica riposta, molto più standard e aderente al formato richiesto:
```markdown
## Executive summary

After reviewing the full portfolio, **CMP-004 (VoloBlu, Travel)** should receive additional budget next quarter. It delivers the strongest combination of **profitability, scale, and conversion volume** across the portfolio.

While **CMP-003 (FreschErba)** has the lowest budget and strong efficiency, it is smaller in absolute revenue impact. **CMP-004** is the best candidate for incremental investment because it leads on **ROI, revenue, and conversions**.

## Metrics table

| Campaign | Client | Sector | Budget (€) | Revenue (€) | Conversions | ROI | Revenue / Budget | Notes |
|---|---|---:|---:|---:|---:|---:|---:|---|
| CMP-001 | AutoMilano | Automotive | 120,000 | 210,000 | 1,260 | 75.0% | 1.75x | Solid all-rounder |
| CMP-002 | BancaVerde | Finance | 90,000 | 132,000 | 612 | 46.7% | 1.47x | Moderate performance |
| CMP-003 | FreschErba | FMCG | 60,000 | 96,000 | 1,700 | 60.0% | 1.60x | Very efficient, smaller scale |
| CMP-004 | VoloBlu | Travel | 150,000 | 351,000 | 2,208 | 134.0% | 2.34x | Best overall performer |
| CMP-005 | TeleCasa | Telco | 80,000 | 72,000 | 387 | -10.0% | 0.90x | Underperforming |

## Trade-offs

- **CMP-004** is the clear leader on **ROI** and also has the highest **revenue** and **conversions**, so it scales well and is profitable.
- **CMP-003** is more efficient relative to budget, but its **absolute return is lower** than CMP-004, so it is better suited for controlled testing than major budget expansion.
- **CMP-001** is respectable but trails CMP-004 on both profitability and scale.
- **CMP-005** is losing money and should not receive additional budget without a major strategy change.

## Recommendation

**Allocate additional budget to CMP-004 (VoloBlu).**

If budget is available for a secondary bet, **CMP-003** is the next-best candidate for a smaller incremental increase because of its strong efficiency, but **CMP-004 should be the primary recipient**.

## Data limitations

- The review is based on the metrics provided by the portfolio tools.
- No breakdown was available by audience, channel, or creative variant beyond the campaign-level channellabel.
- No margin or lifetime value data was provided, so this recommendation is based on **revenue and ROI**,not net profit.
```


---

<a id="passaggio-6"></a>

## Passaggio 6 — Aggiungere un agente A2A di pricing basato su LLM

L'applicazione deve ora creare il preventivo di una nuova campagna
pubblicitaria a partire da un brief come:

```text
Crea un preventivo per una campagna Travel con 9.200.000 impression.
```

Il calcolo atomico del prezzo appartiene al server MCP. Inizialmente, tuttavia,
i criteri aziendali verranno implementati da un agente A2A dedicato.

### 6.1 Aggiungere `campaign_quote` al server MCP

Aggiungi il tool seguente a `agent_campaign_mcp.py`:

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

Mantieni questo tool atomico. Calcola esattamente uno scenario e non contiene
i criteri di preventivazione di livello superiore.

### 6.2 Definire i criteri di preventivazione

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

I criteri sono intenzionalmente più complessi dello schema del tool MCP. In
questo modo l'agente A2A è responsabile di una procedura reale, anziché limitarsi
a inoltrare due argomenti.

### 6.3 Creare l'agente A2A di pricing

Crea `pricing_a2a_agent.py`:

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
            url="http://127.0.0.1:9999/",
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
    uvicorn.run(app, host="127.0.0.1", port=9999)
```

Questo agente è effettivamente basato su LLM:

1. il suo LLM interpreta la richiesta in linguaggio naturale;
2. estrae settore e impression;
3. applica i criteri dei tre scenari;
4. richiede tre chiamate al tool MCP con accesso limitato;
5. formatta la risposta.

Avvialo dopo aver avviato il server MCP:

```bash
.venv/bin/python labs/solutions/pricing_a2a_agent.py
```

### 6.4 Esporre l'agente A2A come tool

In questa fase l'agente principale non deve vedere direttamente
`campaign_quote`. Limita la sua connessione MCP ai tre tool originali per le
prestazioni:

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

Crea un proxy A2A e convertilo in un tool MAF:

```python
from agent_framework.a2a import A2AAgent

remote_pricing_agent = A2AAgent(
    name="PricingAgent",
    description="Creates policy-compliant campaign quotation scenarios.",
    url="http://127.0.0.1:9999",
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

Registra sia la connessione MCP per le prestazioni sia il tool A2A:

```python
agent = Agent(
    client=client,
    name="CampaignAnalyst",
    description="Analyzes campaigns and coordinates campaign services.",
    instructions=(
        "You are an analyst at AdvertSphere Broadcasting. "
        "Always answer in English, concisely and professionally."
    ),
    tools=[campaign_mcp, pricing_tool],
    context_providers=[skills_provider],
)

async with remote_pricing_agent, agent:
    answer = await agent.run(
        "Create a quote for a Travel campaign with 9,200,000 impressions."
    )

print(answer.text)
```

Il percorso di esecuzione è:

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

Questa architettura è giustificata quando l'agente di pricing rappresenta un
vero confine autonomo: un servizio di proprietà separata, un processo di
approvazione indipendente, una negoziazione con stato o un'attività di lunga
durata.

Per questo tutorial, tuttavia, i suoi criteri possono essere applicati anche
dall'agente principale. Il Passaggio 7 esamina questa ottimizzazione.

---

<a id="passaggio-7"></a>

## Passaggio 7 — Sostituire l'agente A2A di pricing con una skill

L'implementazione A2A funziona, ma aggiunge:

- un secondo agente distribuito;
- un altro ciclo di ragionamento basato su LLM;
- un round trip A2A HTTP/JSON-RPC;
- serializzazione e deserializzazione;
- un ulteriore confine per ciclo di vita, integrità, autenticazione e nuovi
  tentativi.

I criteri di preventivazione sono abbastanza deterministici da poter essere
trasferiti in una skill. L'agente principale può quindi chiamare direttamente
`campaign_quote`.

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

### 7.1 Creare la skill di preventivazione

Crea:

```text
skills/campaign-quotation-policy/SKILL.md
```

```markdown
---
name: campaign-quotation-policy
description: >-
  Da usare per prezzi di campagne, preventivi, stime dei costi, scenari di
  budget o brief pubblicitari che specificano un settore e un numero obiettivo
  di impression.
---

# Criteri di preventivazione delle campagne

Crea un preventivo di campagna conforme ai criteri usando dati di pricing
autorevoli.

## Tool necessario

Usa `campaign_quote` per ogni scenario e ogni valore monetario. Non calcolare,
dedurre o modificare mai direttamente le tariffe CPM o i prezzi delle campagne.

## Input necessari

- Settore pubblicitario
- Numero di impression richiesto

Se uno dei due input manca, chiedilo all'utente prima di richiedere un
preventivo. Rifiuta volumi di impression pari a zero o negativi.

## Procedura

1. Estrai il settore e le impression richieste dalla richiesta dell'utente.
2. Calcola soltanto i volumi di impression per questi scenari:
   - ridotto: 20% di impression in meno rispetto a quanto richiesto;
   - richiesto: il numero originale di impression;
   - esteso: 20% di impression in più rispetto a quanto richiesto.
3. Arrotonda le impression degli scenari a numeri interi.
4. Chiama `campaign_quote` una volta per ogni scenario.
5. Usa il CPM e il prezzo totale restituiti dal tool senza modificarli.
6. Se il tool segnala `used_default_rate=true`, dichiara chiaramente che per il
   settore è stato usato il CPM predefinito.
7. Non descrivere il risultato come un'offerta commerciale approvata.

## Formato di output

Restituisci:

1. Una sintesi di una frase
2. Una tabella con scenario, impression, CPM e prezzo totale
3. Un eventuale avviso sulla tariffa predefinita
4. Una nota che specifichi che i valori sono preventivi indicativi
```

La skill fa riferimento a `campaign_quote`, ma non registra il tool. Il tool
deve comunque essere reso disponibile attraverso la connessione MCP
dell'agente principale.

### 7.2 Fornire all'agente principale accesso diretto a `campaign_quote`

Estendi `allowed_tools`:

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

Entrambe le cartelle delle skill vengono individuate automaticamente perché il
provider punta alla cartella padre comune:

```python
skills_provider = SkillsProvider.from_paths(
    Path(__file__).parent / "skills",
    disable_load_skill_approval=True,
)
```

Rimuovi il proxy A2A e il relativo tool:

```python
agent = Agent(
    client=client,
    name="CampaignAnalyst",
    description="Analyzes campaigns and creates policy-compliant quotations.",
    instructions=(
        "You are an analyst at AdvertSphere Broadcasting. "
        "Always answer in English, concisely and professionally."
    ),
    tools=[campaign_mcp],
    context_providers=[skills_provider],
)

async with agent:
    answer = await agent.run(
        "Create a quote for a Travel campaign with 9,200,000 impressions."
    )

print(answer.text)
```

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

<a id="confronto"></a>

## Confrontare le versioni A2A e basata sulle skill

Usa lo stesso input per entrambe le versioni:

```text
Crea un preventivo per una campagna Travel con 9.200.000 impression.
```

I volumi previsti per gli scenari sono:

| Scenario | Impression |
|---|---:|
| Ridotto | 7.360.000 |
| Richiesto | 9.200.000 |
| Esteso | 11.040.000 |

Per il settore Travel con un CPM di 16 EUR, il tool deterministico dovrebbe
restituire:

| Scenario | Impression | CPM | Totale |
|---|---:|---:|---:|
| Ridotto | 7.360.000 | 16 EUR | 117.760 EUR |
| Richiesto | 9.200.000 | 16 EUR | 147.200 EUR |
| Esteso | 11.040.000 | 16 EUR | 176.640 EUR |

Strumenta entrambe le versioni e raccogli:

- latenza end-to-end;
- numero di chiamate LLM dell'agente principale;
- numero di chiamate LLM dell'agente di pricing;
- numero di richieste A2A;
- numero di chiamate ai tool MCP;
- token di input e output;
- rispetto di tutti i requisiti dei criteri.

Un confronto indicativo è:

| Dimensione | Agente A2A di pricing | Skill + tool MCP diretto |
|---|---:|---:|
| LLM principale | Necessario | Necessario |
| Secondo LLM | Necessario | Non necessario |
| Richiesta HTTP A2A | Necessaria | Non necessaria |
| Chiamate MCP | Tre | Tre |
| Posizione dei criteri | Istruzioni dell'agente di pricing | `SKILL.md` |
| Servizio di pricing separato | Necessario | Non necessario |
| Caricamento progressivo della skill | No | Sì |

Il numero esatto di chiamate LLM dipende dal modello e dal comportamento del
runtime. Un tipico flusso basato sulle skill aggiunge un turno LLM per
`load_skill`, ma evita l'intero ciclo di ragionamento dell'agente remoto di
pricing.

Il miglioramento di latenza previsto deriva dall'eliminazione di:

1. chiamate di inferenza LLM dell'agente remoto;
2. round trip A2A HTTP/JSON-RPC;
3. serializzazione e deserializzazione A2A;
4. ciclo di vita del servizio aggiuntivo.

L'inferenza LLM risparmiata nel secondo agente è normalmente più significativa
delle sole operazioni HTTP locali e di serializzazione JSON.

---

<a id="conclusioni"></a>

## Cosa dimostra questo tutorial

### Un tool è sufficiente per un'operazione atomica

`campaign_quote(sector, impressions)` è autoesplicativo e deterministico. Il
modello può spesso richiamarlo correttamente senza una skill.

### Una skill è utile quando aggiunge criteri

La skill di preventivazione è utile perché aggiunge un comportamento che non è
presente nello schema del tool:

- tre scenari;
- la regola ±20%;
- la gestione degli input necessari;
- gli avvisi sulla tariffa predefinita;
- i requisiti di output;
- le restrizioni sulla modifica dei prezzi autorevoli.

Se la skill dicesse soltanto "estrai due parametri e chiama `campaign_quote`",
aggiungerebbe poco valore e potrebbe introdurre soltanto un ulteriore turno
LLM.

### MCP e skill risolvono problemi diversi

MCP espone le operazioni. Le skill definiscono come orchestrare tali operazioni.

```text
Tool MCP:
Che cosa può fare il sistema?

Skill:
Quando e secondo quale procedura deve farlo?
```

### A2A rimane appropriato per una vera autonomia

Non sostituire un agente A2A con una skill quando l'agente remoto ha una
responsabilità indipendente significativa, ad esempio:

- negoziazione con stato;
- proprietà o confini di sicurezza separati;
- approvazioni indipendenti;
- attività di lunga durata;
- avanzamento asincrono;
- accesso a sistemi privati non disponibili all'agente principale;
- coordinamento autonomo con altri agenti.

In questi casi, i costi aggiuntivi di rete e LLM sono il prezzo di un vero
confine architetturale.

### Regola decisionale finale

Usa:

- un **tool** per una funzionalità atomica;
- **MCP** quando tale funzionalità deve essere condivisa in remoto;
- una **skill** per flussi di lavoro e criteri riutilizzabili;
- **A2A** per delegare a un agente realmente autonomo.
