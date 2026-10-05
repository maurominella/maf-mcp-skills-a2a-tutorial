# From a MAF Agent to a Full Skills-Based Solution

AI skills were [announced by Anthropic](https://claude.com/blog/skills) in
October 2025 and spread very rapidly. The key—and far from obvious—question is
now where they make sense, because the capabilities they provide already
existed before skills. Skills can therefore be considered an alternative to a
system prompt or to tools and, in some cases, even a way to optimize
multi-agent systems built around A2A.

To explain how to manage these potential overlaps while also showing how to
use skills in practice, this tutorial is aimed at developers and solution
architects. It starts with a minimal Microsoft Agent Framework (MAF) agent and
builds a complete skills-based solution through function calling, tools, an
MCP server, and A2A.

The scenario follows an analyst at AdvertSphere Broadcasting, a fictitious
company that sells advertising space for a television network.

Across seven incremental steps, described and implemented in this public
GitHub repository, you will build a complete solution from scratch that gives
the analyst:

- access to authoritative campaign data;
- consistent portfolio reviews;
- a campaign quotation service.

In the final part of the tutorial, you will first implement the solution with
a multi-agent approach based on
[A2A, announced by Google six months before skills](https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/).
This approach remains entirely valid today, but skills now give us an
opportunity to evaluate a possible optimization in some cases: effectively
moving the A2A agent's capabilities into a skill and using the orchestrating
agent's LLM.

Follow the steps in order if you want to implement the solution end to end. If
you are using the tutorial as an architecture reference, use the table of
contents to jump directly to the pattern or comparison you need.

The table of contents, requirements, and environment setup follow. Then we
will begin with the first implementation step: creating a minimal Agent
Framework agent.

## Table of contents

- [Prerequisites](#prerequisites)
- [Step 1 — Create a minimal MAF agent](#step-1)
- [Step 2 — Add local function tools](#step-2)
- [Step 3 — Move the tools to an MCP server](#step-3)
- [Step 4 — Observe inconsistent orchestration](#step-4)
- [Step 5 — Add the `campaign-performance-review` skill](#step-5)
- [Step 6 — Add an LLM-backed A2A pricing agent](#step-6)
- [Step 7 — Replace the A2A pricing agent with a skill](#step-7)
- [Compare the A2A and skills-based versions](#comparison)
- [Conclusions](#conclusions)

<a id="prerequisites"></a>

## Prerequisites

This tutorial assumes:

- Python 3.13 or later;
- `agent-framework==1.19.0`;
- `fastmcp==3.4.7`;
- `a2a-sdk==1.1.5`;
- `uvicorn==0.54.0`;
- an Azure OpenAI deployment configured through the existing environment
  variables;
- an authenticated Azure CLI session.

The examples use the following variables:

```text
AZURE_OPENAI_ENDPOINT
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME
```

The suggested project layout is:

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

The exact filenames are not important. What matters is how responsibilities
move across the seven stages.

---

<a id="step-1"></a>

## Step 1 — Create a minimal MAF agent

Start with an agent that has only:

- a name;
- instructions;
- an LLM client.

It has no tools, MCP connection, skills, or A2A agents.

```python
import asyncio
import os

from agent_framework import Agent
from agent_framework.openai import OpenAIChatClient
from azure.identity import AzureCliCredential
from dotenv import load_dotenv

load_dotenv()


async def main() -> None:
    client = OpenAIChatClient(
        model=os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"],
        credential=AzureCliCredential(),
    )

    agent = Agent(
        client=client,
        name="CampaignAnalyst",
        description="Analyzes advertising campaign performance.",
        instructions=(
            "You are an analyst at AdvertSphere Broadcasting. "
            "Always answer in English, concisely and professionally."
        ),
    )

    answer = await agent.run(
        "Review campaign CMP-004 and calculate its ROI."
    )
    print(answer.text)


if __name__ == "__main__":
    asyncio.run(main())
```

The agent can explain ROI in general, but it cannot retrieve authoritative
campaign data. If it answers with campaign-specific values, those values are
not grounded in the application data.

At this stage, the architecture is:

```text
User
  ↓
MAF agent
  ↓
LLM
```

---

<a id="step-2"></a>

## Step 2 — Add local function tools

Add three deterministic functions to the same source file:

- `all_campaigns`;
- `campaign_metrics`;
- `compute_roi`.

Assume that `get_campaign` and `list_campaigns` come from the existing
campaign dataset.

```python
from typing import Annotated

from pydantic import Field

from campaign_data import get_campaign, list_campaigns


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

Register them when creating the agent:

```python
agent = Agent(
    client=client,
    name="CampaignAnalyst",
    description="Analyzes advertising campaign performance.",
    instructions=(
        "You are an analyst at AdvertSphere Broadcasting. "
        "Always answer in English, concisely and professionally."
    ),
    tools=[all_campaigns, campaign_metrics, compute_roi],
)
```

The LLM now receives the schemas generated from the functions, annotations,
and docstrings. It can request a tool call, while MAF performs the actual
function invocation.

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

This is an appropriate design while the capabilities belong to the same
application and do not need to be shared.

---

<a id="step-3"></a>

## Step 3 — Move the tools to an MCP server

Now move the three functions into a separate MCP server named
`agent_campaign_mcp`.

Create `agent_campaign_mcp.py`:

```python
import logging
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from campaign_data import get_campaign, list_campaigns

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

Start the MCP server:

```bash
.venv/bin/python labs/solutions/agent_campaign_mcp.py
```

Replace the three local tools in the main agent with one MCP connection:

```python
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

agent = Agent(
    client=client,
    name="CampaignAnalyst",
    description="Analyzes advertising campaign performance.",
    instructions=(
        "You are an analyst at AdvertSphere Broadcasting. "
        "Always answer in English, concisely and professionally."
    ),
    tools=[campaign_mcp],
)

async with agent:
    answer = await agent.run(
        "Between CMP-004 and CMP-005, which campaign has the better ROI?"
    )

print(answer.text)
```

`tools=[campaign_mcp]` does not hide the individual tools from the LLM. During
MCP discovery, MAF obtains the names, descriptions, and input schemas exposed
by the server. The model still sees the three callable capabilities:

```text
all_campaigns()
campaign_metrics(campaign_id)
compute_roi(revenue_eur, budget_eur)
```

Only their implementation and execution location have changed:

```text
Local tools:
LLM → MAF → Python function

MCP tools:
LLM → MAF → MCP request → MCP server → Python function
```

---

<a id="step-4"></a>

## Step 4 — Observe inconsistent orchestration

Atomic questions are usually handled well because the tool schemas make the
required operation obvious:

```text
What is the ROI of CMP-004?
```

The expected path is simple:

```text
campaign_metrics("CMP-004")
→ compute_roi(revenue_eur, budget_eur)
→ answer
```

Now use a broader question:

```text
Review the entire campaign portfolio and recommend which campaign should
receive additional budget next quarter.
```

The agent has enough capabilities to answer, but it has not been given a
standard review procedure. Across repeated runs or different models, it may:

- rank campaigns only by ROI;
- consider revenue but ignore conversions;
- inspect only a subset of campaigns;
- calculate some ROI values itself instead of using `compute_roi`;
- omit data-quality limitations;
- produce a table in one run and prose in another;
- recommend a campaign without explaining the trade-off between profitability
  and scale.

This is not an MCP problem. MCP correctly exposes the capabilities. The missing
element is a reusable domain procedure.

Run the same prompt several times and inspect `response.messages`:

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

Do not claim that the behavior must be inconsistent on every run. Instead,
measure whether the response consistently satisfies explicit criteria:

| Criterion | Expected without a skill? |
|---|---|
| Every campaign is inspected | Not guaranteed |
| Every ROI uses `compute_roi` | Not guaranteed |
| Profitability and scale are both considered | Not guaranteed |
| Data limitations are stated | Not guaranteed |
| The same output structure is used | Not guaranteed |

---

<a id="step-5"></a>

## Step 5 — Add the `campaign-performance-review` skill

Create:

```text
skills/campaign-performance-review/SKILL.md
```

with the following content:

```markdown
---
name: campaign-performance-review
description: >-
  Use for campaign reviews, portfolio analyses, rankings, investment
  recommendations, and comparisons involving profitability, scale, efficiency,
  or data quality.
---

# Campaign performance review

Apply a consistent, evidence-based method to assess campaign performance.
Base every conclusion on retrieved campaign data and make trade-offs explicit.

## Required tools

- Use `all_campaigns` to identify the campaigns in the portfolio.
- Use `campaign_metrics` to retrieve budget, impressions, conversions, and
  revenue for a campaign.
- Use `compute_roi` to calculate ROI from retrieved revenue and budget values.

Do not invent missing tool results or replace `compute_roi` with a manual ROI
calculation. If a required tool is unavailable or fails, identify the missing
information and limit the analysis accordingly.

## Procedure

1. For a portfolio-wide analysis, call `all_campaigns`; for a focused review,
   start with the campaign identifiers supplied by the user.
2. Call `campaign_metrics` for every campaign included in the analysis.
3. Call `compute_roi` for every campaign whose revenue and budget are valid.
4. Evaluate each campaign on:
   - profitability: ROI;
   - scale: revenue and conversions;
   - efficiency: conversions relative to budget;
   - data quality: missing or invalid values.
5. Do not declare a campaign "best" using ROI alone unless the user explicitly
   requests an ROI-only comparison.
6. If ROI and scale suggest different winners, explain the trade-off.
7. If required data is missing or invalid, identify the affected metrics and
   do not rank the campaign on those metrics.

## Output format

For a portfolio review or investment recommendation, return:

1. Executive summary
2. Metrics table
3. Trade-offs
4. Recommendation
5. Data limitations

For a focused comparison, provide a concise metrics table, explain the relevant
trade-offs, and answer the user's question directly.
```

Register a `SkillsProvider`:

```python
from pathlib import Path

from agent_framework import SkillsProvider

skills_provider = SkillsProvider.from_paths(
    Path(__file__).parent / "skills",
    disable_load_skill_approval=True,
)

agent = Agent(
    client=client,
    name="CampaignAnalyst",
    description="Analyzes advertising campaign performance.",
    instructions=(
        "You are an analyst at AdvertSphere Broadcasting. "
        "Always answer in English, concisely and professionally."
    ),
    tools=[campaign_mcp],
    context_providers=[skills_provider],
)
```

The skill follows progressive disclosure:

1. MAF advertises only `name` and `description`.
2. The LLM determines that the skill is relevant.
3. The LLM requests `load_skill("campaign-performance-review")`.
4. MAF loads and returns the full `SKILL.md` body.
5. The LLM interprets the procedure and requests the MCP tool calls.
6. MAF executes those calls and returns the results.
7. The LLM produces the standardized response.

The skill does not register the tools. It names and orchestrates tools that
must already be available through `Agent(tools=[...])`.

Repeat the Step 4 prompt and evaluate the same criteria. The intended
improvement is not that the agent suddenly gains new data or calculations.
The improvement is that the existing capabilities are used through a
consistent, reusable workflow.

---

<a id="step-6"></a>

## Step 6 — Add an LLM-backed A2A pricing agent

The application now needs to quote a new advertising campaign from a brief such
as:

```text
Create a quote for a Travel campaign with 9,200,000 impressions.
```

The atomic pricing calculation belongs in the MCP server. The initial business
policy, however, will be implemented by a dedicated A2A agent.

### 6.1 Add `campaign_quote` to the MCP server

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

### 6.2 Define the quotation policy

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
two arguments.

### 6.3 Create the A2A pricing agent

Create `pricing_a2a_agent.py`:

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

### 6.4 Expose the A2A agent as a tool

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

Register both the performance MCP connection and the A2A tool:

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

This architecture is justified when the pricing agent represents a real
autonomous boundary: a separately owned service, an independent approval
process, a stateful negotiation, or a long-running task.

For this tutorial, however, its policy can also be performed by the main
agent. Step 7 explores that optimization.

---

<a id="step-7"></a>

## Step 7 — Replace the A2A pricing agent with a skill

The A2A implementation works, but it adds:

- a second deployed agent;
- another LLM-backed reasoning loop;
- an A2A HTTP/JSON-RPC round trip;
- serialization and deserialization;
- another lifecycle, health, authentication, and retry boundary.

The quotation policy is deterministic enough to be transferred to a skill.
The main agent can then call `campaign_quote` directly.

This does not eliminate LLM usage. The main LLM still:

- recognizes the quotation request;
- requests the quotation skill;
- interprets its policy;
- extracts sector and impressions;
- calculates the ±20% impression volumes;
- requests the three MCP tool calls;
- formats the final response.

It does eliminate the second LLM-backed agent and the A2A service hop.

### 7.1 Create the quotation skill

Create:

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

The skill references `campaign_quote`, but it does not register the tool. The
tool still has to be made available through the main agent's MCP connection.

### 7.2 Give the main agent direct access to `campaign_quote`

Expand `allowed_tools`:

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

Both skill folders are automatically discovered because the provider points to
their common parent:

```python
skills_provider = SkillsProvider.from_paths(
    Path(__file__).parent / "skills",
    disable_load_skill_approval=True,
)
```

Remove the A2A proxy and its tool:

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

The optimized runtime path is:

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

The A2A pricing agent is no longer required:

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

## Compare the A2A and skills-based versions

Use the same input for both versions:

```text
Create a quote for a Travel campaign with 9,200,000 impressions.
```

The expected scenario volumes are:

| Scenario | Impressions |
|---|---:|
| Lean | 7,360,000 |
| Requested | 9,200,000 |
| Extended | 11,040,000 |

For Travel at a CPM of EUR 16, the deterministic tool should return:

| Scenario | Impressions | CPM | Total |
|---|---:|---:|---:|
| Lean | 7,360,000 | EUR 16 | EUR 117,760 |
| Requested | 9,200,000 | EUR 16 | EUR 147,200 |
| Extended | 11,040,000 | EUR 16 | EUR 176,640 |

Instrument both versions and collect:

- end-to-end latency;
- number of main-agent LLM calls;
- number of pricing-agent LLM calls;
- number of A2A requests;
- number of MCP tool calls;
- input and output tokens;
- whether all policy requirements were satisfied.

An indicative comparison is:

| Dimension | A2A pricing agent | Skill + direct MCP tool |
|---|---:|---:|
| Main LLM | Required | Required |
| Second LLM | Required | Not required |
| A2A HTTP request | Required | Not required |
| MCP calls | Three | Three |
| Policy location | Pricing agent instructions | `SKILL.md` |
| Separate pricing service | Required | Not required |
| Progressive skill load | No | Yes |

Exact LLM call counts depend on the model and runtime behavior. A typical
skills flow adds an LLM turn for `load_skill`, but it avoids the complete
reasoning loop of the remote pricing agent.

The expected latency improvement comes from eliminating:

1. the remote agent's LLM inference calls;
2. the A2A HTTP/JSON-RPC round trip;
3. A2A serialization and deserialization;
4. the additional service lifecycle.

The LLM inference saved in the second agent is normally more significant than
local HTTP and JSON serialization alone.

---

<a id="conclusions"></a>

## What this tutorial demonstrates

### A tool is enough for an atomic operation

`campaign_quote(sector, impressions)` is self-describing and deterministic.
The model can often invoke it correctly without a skill.

### A skill is valuable when it adds policy

The quotation skill is useful because it adds behavior that is not present in
the tool schema:

- three scenarios;
- the ±20% rule;
- required-input handling;
- default-rate warnings;
- output requirements;
- restrictions on modifying authoritative prices.

If the skill merely said "extract two parameters and call `campaign_quote`",
it would add little value and might only introduce another LLM turn.

### MCP and skills solve different problems

MCP exposes the operations. The skills define how to orchestrate them.

```text
MCP tool:
What can the system do?

Skill:
When and according to which procedure should it do it?
```

### A2A remains appropriate for real autonomy

Do not replace an A2A agent with a skill when the remote agent has a meaningful
independent responsibility, such as:

- stateful negotiation;
- separate ownership or security boundaries;
- independent approvals;
- long-running tasks;
- asynchronous progress;
- access to private systems unavailable to the main agent;
- autonomous coordination with additional agents.

In those cases, the additional network and LLM costs are the price of a real
architectural boundary.

### The final decision rule

Use:

- a **tool** for an atomic capability;
- **MCP** when that capability must be shared remotely;
- a **skill** for reusable workflow and policy;
- **A2A** for delegation to a genuinely autonomous agent.
