<a id="step-6"></a>

# Step 6 — Add an LLM-backed A2A pricing agent

The next requirement is to generate a quotation for a new advertising campaign
from a brief like this:

```text
Create a quote for a Travel campaign with 9,200,000 impressions.
```

The MCP server will remain responsible for the individual pricing calculation,
while a dedicated A2A agent will initially handle the broader business rules.

## 6.1 Introduce `campaign_quote` in the MCP server

Define this additional tool in `agent_campaign_mcp.py`:

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

The tool should remain atomic: it prices one scenario only and contains none
of the higher-level quotation logic.

## 6.2 Specify the quotation rules

The pricing service is expected to follow these rules:

1. Read the sector and impression count from the request.
2. Do not accept an absent impression count or a value that is not positive.
3. Generate three alternatives:
   - lean: 20% below the requested impressions;
   - requested: the original impression count;
   - extended: 20% above the requested impressions.
4. Obtain every monetary amount through `campaign_quote`.
5. Do not independently compute or alter the CPM.
6. Indicate whenever the fallback sector rate is applied.
7. Show all three alternatives in a comparison table.

These rules deliberately go beyond what the MCP tool schema describes. The A2A
agent therefore performs an actual procedure instead of simply passing along
the two parameters, *sector* and *impressions*.

Because the agent must identify those values within a natural-language
request, it relies on an LLM. In principle, not every A2A or hosted agent
requires one: it could be left out if requests were already structured, or if
regular expressions could parse them dependably. In real-world applications,
however, **an LLM is present in nearly every agent**. Using one here makes the
next step a realistic example of transferring an A2A agent's behavior into a
skill.

## 6.3 Implement the A2A pricing agent

Create `pricing_a2a_agent.py` and place the quotation rules described above in
the agent instructions:

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

This is a true LLM-powered agent because:

1. the model understands the request written in natural language;
2. it identifies the sector and number of impressions;
3. it follows the policy for the three scenarios;
4. it initiates three invocations of the restricted MCP tool;
5. it prepares the resulting answer.

Once the MCP server is running, launch the agent:

```bash
.venv/bin/python labs/pricing_a2a_agent.py
```

Uvicorn makes the agent available over HTTP. Through its
[ASGI (Asynchronous Server Gateway Interface)](https://uvicorn.dev/concepts/asgi/)
integration, `pricing_agent` receives the user's input and any authentication
details, although authentication is not used in this tutorial. MAF publishes
two endpoints for the agent: `/` handles invocations, while
`/.well-known/agent-card.json` serves the Agent Card:

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

## 6.4 Make the A2A agent available as a tool

At this point, `campaign_quote` must not be directly accessible to the main
agent. Keep its MCP connection limited to the original three performance
tools:

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

Set up an A2A proxy, then expose that proxy as a MAF tool:

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

Register the new A2A tool together with the MCP connection already in use:

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

The generated response follows the instructions assigned to the A2A agent:

---
The quotation for the Travel campaign is shown below:

| Scenario | Impressions | CPM (EUR) | Total (EUR) |
|---|---:|---:|---:|
| Lean | 7,360,000 | 16.00 | 117,760.00 |
| Requested | 9,200,000 | 16.00 | 147,200.00 |
| Extended | 11,040,000 | 16.00 | 176,640.00 |

The requested scenario totals **EUR 147,200.00**.

---

The request now travels through this execution path:

```text
User
  ↓
Main agent LLM
  ↓ requests get_campaign_quote
MAF invokes the A2A proxy
  ↓ HTTP/JSON-RPC
Pricing agent LLM
  ↓ applies the ±20% policy
campaign_quote MCP tool, called three times
  ↓
Pricing agent LLM formats the delegated answer
  ↓ HTTP/JSON-RPC
Main agent LLM integrates the result
  ↓
User
```

Overall, producing the answer requires four LLM calls, one HTTP request to the
A2A service, and one interaction with the MCP tool:

- the main agent first calls its LLM to choose the A2A tool;
- an HTTP request reaches A2A, with parameters serialized and then deserialized;
- the A2A agent calls its own LLM to select the MCP pricing tool;
- the MCP pricing interaction performs the necessary calls for each scenario;
- the A2A agent uses another LLM call to format the pricing result;
- finally, the main agent calls its LLM again to convert the A2A result into
  the response shown to the user.

This design makes sense when the pricing agent forms a genuinely independent
boundary, such as a service managed by another owner, a separate approval
workflow, a stateful negotiation process, or a task that runs for a long time.

When none of those conditions applies, the call chain can be simplified by
turning the A2A agent's behavior into a skill that the main agent loads. That
optimization is the subject of Step 7.

---
