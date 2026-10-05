<a id="step-6"></a>

# Step 6 — Add an LLM-backed A2A pricing agent

The application now needs to quote a new advertising campaign from a brief such
as:

```text
Create a quote for a Travel campaign with 9,200,000 impressions.
```

The atomic pricing calculation belongs in the MCP server. The initial business
policy, however, will be implemented by a dedicated A2A agent.

## 6.1 Add `campaign_quote` to the MCP server

Add the following tool to `agent_campaign_mcp.py`:

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

Keep this tool atomic. It calculates exactly one scenario and does not contain
the higher-level quotation policy.

## 6.2 Define the quotation policy

The pricing service must apply the following policy:

1. Extract sector and impressions from the request.
2. Reject missing or non-positive impressions.
3. Produce three scenarios:
   - lean: 20% fewer impressions;
   - requested: the requested impressions;
   - extended: 20% more impressions.
4. Use `campaign_quote` for every monetary value.
5. Never calculate or modify the CPM directly.
6. Warn when the default sector rate is used.
7. Present the three scenarios in a comparison table.

The policy is intentionally more complex than the MCP tool schema. This makes
the A2A agent responsible for a real procedure, rather than merely forwarding
the two arguments (*sector* and *impressions*).

The agent is responsible for extracting those arguments from the request, so
it needs an LLM. An LLM is not theoretically required for every A2A or hosted
agent: if the request arrived in an already encoded form, or in a form that
could be interpreted reliably with regular expressions, it could be omitted.
In practice, however, **agents nearly always include an LLM**. Including it
here makes the next step a representative demonstration of moving an A2A
agent's behavior into a skill.

## 6.3 Create the A2A pricing agent

Create `pricing_a2a_agent.py`. Its instructions contain the advanced quotation
policy defined above:

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

This agent is genuinely LLM-backed:

1. its LLM interprets the natural-language request;
2. it extracts sector and impressions;
3. it applies the three-scenario policy;
4. it requests three calls to the restricted MCP tool;
5. it formats the response.

Start it after starting the MCP server:

```bash
.venv/bin/python labs/solutions/pricing_a2a_agent.py
```

Uvicorn exposes the agent through HTTP, while its
[ASGI (Asynchronous Server Gateway Interface)](https://uvicorn.dev/concepts/asgi/)
integration invokes `pricing_agent` with the user's input and any
authentication information, which this tutorial does not use. MAF exposes the
agent through two routes: `/` for invocation and
`/.well-known/agent-card.json` for the Agent Card:

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

## 6.4 Expose the A2A agent as a tool

The main agent must not see `campaign_quote` directly during this stage.
Restrict its MCP connection to the original three performance tools:

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

Create an A2A proxy and convert it to a MAF tool:

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

Now register the A2A tool alongside the existing MCP connection:

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

The result is consistent with the A2A agent's instructions:

---
Here is the quote for the Travel campaign:

| Scenario | Impressions | CPM (EUR) | Total (EUR) |
|---|---:|---:|---:|
| Lean | 7,360,000 | 16.00 | 117,760.00 |
| Requested | 9,200,000 | 16.00 | 147,200.00 |
| Extended | 11,040,000 | 16.00 | 176,640.00 |

Requested quote: **EUR 147,200.00**.

---

The runtime path is:

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

In other words, answering this request involves four LLM calls plus one HTTP
call to the A2A service and one MCP tool interaction:

- one main-agent LLM call that selects the A2A tool;
- one HTTP call to A2A, including parameter serialization and deserialization;
- one LLM call inside the A2A agent that selects the MCP pricing tool;
- one MCP pricing tool interaction, comprising the required scenario calls;
- one LLM call inside the A2A agent that formats the pricing tool response;
- one final main-agent LLM call that turns the A2A response into the user-facing answer.

This architecture is justified when the pricing agent represents a real
autonomous boundary: a separately owned service, an independent approval
process, a stateful negotiation, or a long-running task.

If those requirements do not apply, the invocation chain can be shortened by
moving the A2A agent's behavior into a skill loaded by the main agent. Step 7
explores that optimization.

---

