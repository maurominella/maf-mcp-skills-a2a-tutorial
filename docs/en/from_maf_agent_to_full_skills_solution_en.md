# Evolving a MAF Agent into a Complete Skills-Based Solution

After [Anthropic announced AI skills](https://claude.com/blog/skills) in
October 2025, adoption grew extremely quickly. The important—and not
necessarily straightforward—question is where skills are the right choice,
since their underlying capabilities were available before the concept of
skills emerged. Depending on the scenario, a skill may complement or replace
parts of a system prompt, overlap with tools, or even streamline an A2A-based
multi-agent architecture.

This tutorial helps developers and solution architects understand these
overlaps while learning to implement skills in a practical setting. Beginning
with a minimal Microsoft Agent Framework (MAF) agent, it gradually introduces
function calling, tools, an MCP server, and A2A to arrive at a complete
skills-based solution.

The example centers on an analyst working for AdvertSphere Broadcasting, an
imaginary company that markets advertising inventory for a television
network.

The public GitHub repository implements seven progressive stages. By following
them, you will create a solution from the ground up that provides the analyst
with:

- authoritative advertising campaign information;
- repeatable portfolio assessments;
- a service for generating campaign quotations.

In the last part, the solution is first built as a multi-agent system using
[A2A, which Google introduced six months before skills](https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/).
That design is still fully valid. Skills, however, make it possible to assess
an optimization for suitable cases: transferring the A2A agent's behavior to
a skill and relying on the orchestrating agent's LLM instead.

For a complete implementation, work through the steps sequentially. When using
the tutorial only as an architectural reference, the table of contents can
take you directly to a particular pattern or comparison.

The next sections cover navigation, prerequisites, and environment
preparation, followed by the first implementation task: building a minimal
Agent Framework agent.

## Table of contents

- [Prerequisites](#prerequisites)
- [Step 1 — Build a minimal MAF agent](#step-1)
- [Step 2 — Introduce local function tools](#step-2)
- [Step 3 — Transfer the tools to an MCP server](#step-3)
- [Step 4 — Examine orchestration inconsistencies](#step-4)
- [Step 5 — Introduce the `campaign-performance-review` skill](#step-5)
- [Step 6 — Introduce an LLM-powered A2A pricing agent](#step-6)
- [Step 7 — Substitute a skill for the A2A pricing agent](#step-7)
- [Comparison of the A2A and skill-based approaches](#comparison)
- [Conclusions](#conclusions)

<a id="prerequisites"></a>

## Prerequisites

Before starting, ensure the following are available:

- Python 3.13 or later;
- `agent-framework==1.19.0`;
- `fastmcp==3.4.7`;
- `a2a-sdk==1.1.5`;
- `uvicorn==0.54.0`;
- an Azure OpenAI deployment configured through the existing environment
  variables;
- an authenticated Azure CLI session.

The examples rely on these environment variables:

```text
AZURE_OPENAI_ENDPOINT
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME
```

The recommended project structure is:

```text
labs/
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

The precise filenames are secondary; the important point is how each of the
seven stages redistributes responsibilities.

---

<a id="step-1"></a>

## Step 1 — Build a minimal MAF agent

Begin with an agent configured with just:

- its name;
- a set of instructions;
- an LLM client.

At this point there are no tools, skills, MCP connections, or A2A agents.

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

The code executes successfully, but the agent can only discuss ROI in general
terms because it cannot access authoritative campaign information. A likely
response is therefore: *I can help calculate ROI for CMP-004, but the
campaign's performance data is not available in this conversation*.

The initial architecture looks like this:

```text
User
  ↓
MAF agent
  ↓
LLM
```

---

<a id="step-2"></a>

## Step 2 — Introduce local function tools

Define three deterministic functions in the same module:

- `all_campaigns`;
- `campaign_metrics`;
- `compute_roi`.

For this exercise, `all_campaigns` and `campaign_metrics` call functions from
`asb_campaign.py` so the example can run as-is. In a production application,
they would query the authoritative campaign data source. Insert the following
code near the top of the module, directly after `load_dotenv()`:

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

Pass the functions through the `tools` parameter so Agent Framework registers
them when the agent is created:

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

The LLM is now given schemas derived from the function definitions, type
annotations, and docstrings. The model can ask to use a tool, and MAF executes
the corresponding function.

```text
User
  ↓
LLM requests campaign_metrics
  ↓
MAF executes the Python function
  ↓
MAF returns the tool result to the LLM
  ↓
LLM produces the answer
```

This design works well as long as the capabilities remain local to the
application and no other system needs to consume them.

---

<a id="step-3"></a>

## Step 3 — Transfer the tools to an MCP server

Next, place the three functions in an independent MCP server called
`agent_campaign_mcp`.

Add a new `agent_campaign_mcp.py` file:

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

Launch the MCP server:

```bash
.venv/bin/python labs/agent_campaign_mcp.py
```

The following output indicates that the HTTP MCP endpoint is available:

```text
[10/05/26 14:50:05] INFO     Starting MCP server 'AdvertSphere Campaign MCP' with transport 'http' on              transport.py:361
                             http://127.0.0.1:8000/mcp
INFO:     Started server process [100965]
INFO:     Waiting for application startup.
INFO:mcp.server.streamable_http_manager:StreamableHTTP session manager started
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

Within the agent's `async def main()` function:

- connect to the MCP server using `MCPStreamableHTTPTool`;
- replace the three local functions with a single MCP connection;
- execute the agent inside an asynchronous context manager.

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

Using `tools=[campaign_mcp]` does not conceal the underlying tools from the
LLM. During MCP discovery, MAF retrieves the names, descriptions, and input
schemas published by the server. The same three operations remain visible to
the model:

```text
all_campaigns()
campaign_metrics(campaign_id)
compute_roi(revenue_eur, budget_eur)
```

What changes is only where they are implemented and executed:

```text
Local tools:
LLM → MAF → Python function

MCP tools:
LLM → MAF → MCP request → MCP server → Python function
```

---

<a id="step-4"></a>

## Step 4 — Examine orchestration inconsistencies

The agent generally handles focused questions effectively because the tool
schemas clearly indicate which operation is needed:

```text
What is the ROI of CMP-004?
```

The resulting sequence is straightforward:

```text
campaign_metrics("CMP-004")
→ compute_roi(revenue_eur, budget_eur)
→ answer
```

Next, ask a more comprehensive question:

```text
Review the entire campaign portfolio and recommend which campaign should
receive additional budget next quarter.
```

The agent has all the required capabilities, but no consistent review process
has been defined for it. When the prompt is repeated or another model is used,
the agent might:

- base the ranking exclusively on ROI;
- evaluate revenue while overlooking conversions;
- review only some of the available campaigns;
- compute certain ROI figures directly rather than calling `compute_roi`;
- leave out caveats about data quality;
- return a table in one execution and plain text in another;
- make a recommendation without discussing the balance between profitability
  and scale.

MCP is not the source of this behavior: it exposes the capabilities correctly.
What is absent is a repeatable procedure for this business domain.

Execute the same prompt multiple times, then examine `response.messages`:

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

The behavior should not be described as necessarily inconsistent in every
execution. A better approach is to check whether each response reliably meets
a set of well-defined criteria:

| Evaluation criterion | Reliable without a skill? |
|---|---|
| All campaigns are reviewed | No guarantee |
| Every ROI is obtained through `compute_roi` | No guarantee |
| Both scale and profitability are evaluated | No guarantee |
| Data constraints are acknowledged | No guarantee |
| A consistent response structure is followed | No guarantee |

---

<a id="step-5"></a>

## Step 5 — Introduce the `campaign-performance-review` skill

Add this file:

```text
skills/campaign-performance-review/SKILL.md
```

Use the following definition:

```markdown
---
name: campaign-performance-review
description: >-
  Use for campaign reviews, portfolio analyses, rankings, investment
  recommendations, and comparisons involving profitability, scale, efficiency,
  or data quality.
---

# Campaign performance review

Assess campaign performance with a repeatable, evidence-driven process.
Support every conclusion with retrieved data and clearly describe trade-offs.

## Required tools

- Call `all_campaigns` to determine which campaigns belong to the portfolio.
- Call `campaign_metrics` to obtain a campaign's budget, impressions,
  conversions, and revenue.
- Call `compute_roi` with the retrieved revenue and budget to obtain ROI.

Never fabricate unavailable tool output or substitute a manual ROI calculation
for `compute_roi`. If a necessary tool fails or cannot be accessed, state what
information is unavailable and restrict the analysis accordingly.

## Procedure

1. For a complete portfolio assessment, begin with `all_campaigns`. For a
   targeted review, use the campaign identifiers given by the user.
2. Retrieve details with `campaign_metrics` for each campaign under review.
3. Use `compute_roi` whenever a campaign has valid revenue and budget values.
4. Assess every campaign according to:
   - profitability, represented by ROI;
   - scale, using revenue and conversions;
   - efficiency, based on conversions in relation to budget;
   - data quality, including absent or invalid values.
5. Unless the user specifically asks for an ROI-only comparison, do not select
   the "best" campaign based solely on ROI.
6. Explain the compromise when scale and ROI point to different leaders.
7. When required values are missing or invalid, name the affected metrics and
   exclude the campaign from rankings based on them.

## Output format

For portfolio assessments and investment recommendations, provide:

1. An executive summary
2. A metrics table
3. A discussion of trade-offs
4. A recommendation
5. Data limitations

For a targeted comparison, include a compact metrics table, describe the
relevant trade-offs, and respond directly to the user's question.
```

Create a `SkillsProvider` and register it with the agent:

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

The skill is made available through progressive disclosure:

1. MAF initially exposes just the `name` and `description`.
2. The LLM recognizes that the skill applies to the request.
3. The model asks for `load_skill("campaign-performance-review")`.
4. MAF retrieves and supplies the complete body of `SKILL.md`.
5. The LLM follows the procedure and requests the appropriate MCP tools.
6. MAF runs those tool calls and provides their output.
7. The LLM formats the result using the standard response structure.

The skill itself does not make any tool available. It refers to and coordinates
tools that must already have been supplied through `Agent(tools=[...])`.

Run the prompt from Step 4 again and assess it against the same criteria. The
agent has not acquired additional data or computational abilities. Instead,
the existing capabilities now operate within a consistent process that can be
reused.

A representative answer is much more structured and follows the required
format:

___
### Executive summary

The complete portfolio review identifies **CMP-004 (VoloBlu, Travel)** as the strongest candidate for additional budget next quarter. Across all campaigns, it offers the best balance of **profitability, scale, and conversion volume**.

Although **CMP-003 (FreschErba)** operates efficiently with the smallest budget, its absolute revenue contribution is lower. **CMP-004** is therefore the preferred option for incremental investment because it ranks first in **ROI, revenue, and conversions**.

### Metrics table

| Campaign | Client | Sector | Budget (€) | Revenue (€) | Conversions | ROI | Revenue / Budget | Notes |
|---|---|---:|---:|---:|---:|---:|---:|---|
| CMP-001 | AutoMilano | Automotive | 120,000 | 210,000 | 1,260 | 75.0% | 1.75x | Solid all-rounder |
| CMP-002 | BancaVerde | Finance | 90,000 | 132,000 | 612 | 46.7% | 1.47x | Moderate performance |
| CMP-003 | FreschErba | FMCG | 60,000 | 96,000 | 1,700 | 60.0% | 1.60x | Very efficient, smaller scale |
| CMP-004 | VoloBlu | Travel | 150,000 | 351,000 | 2,208 | 134.0% | 2.34x | Best overall performer |
| CMP-005 | TeleCasa | Telco | 80,000 | 72,000 | 387 | -10.0% | 0.90x | Underperforming |

### Trade-offs

- **CMP-004** leads decisively in **ROI**, while also generating the most **revenue** and **conversions**, demonstrating both scale and profitability.
- **CMP-003** uses its budget efficiently, but produces a lower **absolute return** than CMP-004. It is therefore a better fit for limited experimentation than for a substantial budget increase.
- **CMP-001** performs well overall, but remains behind CMP-004 in profitability and scale.
- **CMP-005** currently generates a loss and should not receive more budget unless its strategy changes significantly.

### Recommendation

**Direct the additional budget to CMP-004 (VoloBlu).**

If funds permit a secondary investment, the efficiency of **CMP-003** makes it suitable for a smaller increase. Nevertheless, **CMP-004 should remain the main recipient**.

### Data limitations

- The assessment uses only the metrics returned by the portfolio tools.
- Apart from the campaign-level channel label, there is no detailed information by audience, channel, or creative variation.
- Margin and customer lifetime value were not provided, so the recommendation relies on **revenue and ROI** rather than net profit.
___

---

<a id="step-6"></a>

## Step 6 — Introduce an LLM-powered A2A pricing agent

The next requirement is to generate a quotation for a new advertising campaign
from a brief like this:

```text
Create a quote for a Travel campaign with 9,200,000 impressions.
```

The MCP server will remain responsible for the individual pricing calculation,
while a dedicated A2A agent will initially handle the broader business rules.

### 6.1 Introduce `campaign_quote` in the MCP server

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

### 6.2 Specify the quotation rules

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

### 6.3 Implement the A2A pricing agent

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

### 6.4 Make the A2A agent available as a tool

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

<a id="step-7"></a>

## Step 7 — Substitute a skill for the A2A pricing agent

Although the A2A solution works, it introduces:

- an additional agent to deploy;
- a separate reasoning loop powered by an LLM;
- an HTTP/JSON-RPC round trip over A2A;
- data serialization and deserialization;
- extra boundaries for lifecycle management, health, authentication, and retries.

The quotation rules are predictable enough to move into a skill. This skill
directs the primary agent to invoke `campaign_quote` itself, which allows the
A2A agent to be removed from the design.

This change does not remove the LLM. The main model continues to:

- identify that the user is asking for a quotation;
- load the appropriate quotation skill;
- understand and follow its rules;
- obtain the sector and impression count;
- derive the impression volumes at ±20%;
- initiate the three MCP tool invocations;
- present the final answer.

What disappears is the second LLM-based agent, together with the A2A service
round trip.

### 7.1 Build the quotation skill

Add the following file:

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

Produce a campaign quotation that follows policy and uses authoritative pricing
data.

## Required tool

Call `campaign_quote` for each scenario and for every monetary amount. Do not
independently calculate, infer, or adjust CPM rates or campaign prices.

## Required inputs

- The advertising sector
- The desired impression count

Before requesting a quotation, ask the user for any missing input. Impression
volumes equal to or below zero are invalid.

## Procedure

1. Read the sector and target impression count from the user's request.
2. Derive impression volumes only for the following cases:
   - lean: 20% below the requested volume;
   - requested: exactly the original volume;
   - extended: 20% above the requested volume.
3. Express each scenario's impressions as a whole number.
4. Invoke `campaign_quote` separately for all three scenarios.
5. Preserve the CPM and total price exactly as returned by the tool.
6. When the tool returns `used_default_rate=true`, explicitly mention that the
   default CPM was applied to the sector.
7. Never present the result as a formally approved commercial offer.

## Output format

Structure the response as follows:

1. A brief, single-sentence overview
2. A table listing scenario, impressions, CPM, and total price
3. A warning when the default rate applies
4. A statement clarifying that the quoted figures are indicative
```

Mentioning `campaign_quote` in the skill does not register the tool. It must
still be exposed to the primary agent through its MCP connection.

### 7.2 Allow the main agent to call `campaign_quote` directly

Add the tool to `allowed_tools`:

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

The provider targets the parent directory shared by both skills, so each skill
folder is discovered automatically:

```python
skills_provider = SkillsProvider.from_paths(
    Path(__file__).parent / "skills",
    disable_load_skill_approval=True,
)
```

Next, take out the A2A proxy and the associated tool:

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

Run the updated example. **Pets** is not among the configured categories, so
the result shows that the fallback CPM has been applied:

---
Below is an indicative quote for a Pets campaign targeting 10,000,000
impressions.

| Scenario | Impressions | CPM | Total price |
|---|---:|---:|---:|
| Lean | 8,000,000 | €15.00 | €120,000.00 |
| Requested | 10,000,000 | €15.00 | €150,000.00 |
| Extended | 12,000,000 | €15.00 | €180,000.00 |

Default-rate notice: pricing for the Pets sector uses the default CPM.

The amounts shown are indicative estimates and do not constitute an approved
commercial offer.

---

The streamlined execution flow is now:

```text
User
  ↓
Main agent LLM
  ↓ requests load_skill("campaign-quotation-policy")
MAF loads the local SKILL.md
  ↓
Main agent LLM applies the ±20% policy
  ↓ requests campaign_quote three times
MAF invokes the MCP server directly
  ↓
Main agent LLM formats the final answer
  ↓
User
```

As a result, the A2A pricing agent is no longer part of the solution:

```text
Before:
Main agent
  └── A2A pricing agent
        └── campaign_quote MCP tool

After:
Main agent
  ├── campaign-quotation-policy skill
  └── campaign_quote MCP tool
```

---

<a id="comparison"></a>

## Comparison of the A2A and skill-based approaches

Run both implementations with an identical request:

```text
Create a quote for a Travel campaign with 9,200,000 impressions.
```

This should produce the following impression volumes:

| Scenario | Impressions |
|---|---:|
| Lean | 7,360,000 |
| Requested | 9,200,000 |
| Extended | 11,040,000 |

With the Travel CPM set to EUR 16, the deterministic tool is expected to
produce:

| Scenario | Impressions | CPM | Total |
|---|---:|---:|---:|
| Lean | 7,360,000 | EUR 16 | EUR 117,760 |
| Requested | 9,200,000 | EUR 16 | EUR 147,200 |
| Extended | 11,040,000 | EUR 16 | EUR 176,640 |

Add instrumentation to each implementation and record:

- total end-to-end response time;
- LLM calls made by the primary agent;
- LLM calls made by the pricing agent;
- A2A request count;
- MCP tool invocation count;
- tokens sent and received;
- successful fulfillment of every policy rule.

A representative comparison looks like this:

| Aspect | A2A pricing agent | Skill with direct MCP access |
|---|---:|---:|
| Primary LLM | Needed | Needed |
| Additional LLM | Needed | Unnecessary |
| HTTP request over A2A | Needed | Unnecessary |
| Number of MCP calls | Three | Three |
| Where the policy resides | Pricing agent instructions | `SKILL.md` |
| Independent pricing service | Needed | Unnecessary |
| Skill loaded progressively | No | Yes |

The precise number of LLM calls varies with the selected model and its runtime
behavior. A standard skill-based flow usually introduces an LLM turn for
`load_skill`, while removing the remote pricing agent's full reasoning cycle.

The anticipated reduction in latency is achieved by removing:

1. LLM inference within the remote agent;
2. the HTTP/JSON-RPC round trip required by A2A;
3. serialization and deserialization for the A2A exchange;
4. management of an extra service lifecycle.

In most cases, avoiding inference in the second agent has a greater impact than
eliminating local HTTP communication and JSON processing by themselves.

---

<a id="conclusions"></a>

## Key lessons from this tutorial

### Atomic operations can be handled by a tool

`campaign_quote(sector, impressions)` is self-describing and deterministic.
In many cases, the model can call it correctly without needing a skill.

### Skills provide value when they introduce policy

The quotation skill matters because it defines behavior beyond the information
available in the tool schema:

- generation of three scenarios;
- application of the ±20% variation;
- validation of mandatory inputs;
- notification when the default rate is used;
- a prescribed response format;
- protection against changing authoritative prices.

If its only instruction were to read two arguments and invoke
`campaign_quote`, the skill would contribute very little and could simply add
an extra LLM turn.

### MCP and skills address distinct concerns

MCP makes operations available; skills establish the procedure for coordinating
them.

```text
MCP tool:
Which capabilities does the system provide?

Skill:
When should those capabilities be used, and what process should be followed?
```

### Genuine autonomy remains a valid use case for A2A

An A2A agent should not be replaced by a skill when the remote component has a
substantive independent role, for example:

- negotiations that maintain state;
- distinct ownership or security boundaries;
- approvals performed independently;
- operations that take a long time to complete;
- progress reported asynchronously;
- access to private resources the primary agent cannot reach;
- independent collaboration with other agents.

Under those conditions, the additional LLM and networking overhead is the cost
of maintaining a genuine architectural boundary.

### A practical selection rule

Choose:

- a **tool** when the capability is atomic;
- **MCP** when the capability needs to be available remotely;
- a **skill** to capture reusable procedures and policy;
- **A2A** when work must be delegated to a truly autonomous agent.
