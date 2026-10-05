<a id="step-3"></a>

# Step 3 — Move the tools to an MCP server

Now move the three functions into a separate MCP server named
`agent_campaign_mcp`.

Create `agent_campaign_mcp.py`:

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

Start the MCP server:

```bash
.venv/bin/python labs/solutions/agent_campaign_mcp.py
```

The output confirms that the HTTP MCP endpoint is running:

```text
[10/05/26 14:50:05] INFO     Starting MCP server 'AdvertSphere Campaign MCP' with transport 'http' on              transport.py:361
                             http://127.0.0.1:8000/mcp
INFO:     Started server process [100965]
INFO:     Waiting for application startup.
INFO:mcp.server.streamable_http_manager:StreamableHTTP session manager started
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

In the agent's `async def main()`:

- add the MCP server through `MCPStreamableHTTPTool`;
- replace the main agent's three local tools with one MCP connection;
- wrap the agent execution in an asynchronous context manager.

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

