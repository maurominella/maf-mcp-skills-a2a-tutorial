<a id="step-2"></a>

# Step 2 — Add local function tools

Add three deterministic functions to the same source file:

- `all_campaigns`;
- `campaign_metrics`;
- `compute_roi`.

In this example, `all_campaigns` and `campaign_metrics` use functions
implemented in `asb_campaign.py` solely to make the exercise executable. In a
real application, these functions should query the authoritative campaign
dataset. Add this code near the beginning of the module, immediately after
`load_dotenv()`:

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

Agent Framework can register these functions when creating the agent by
passing them to the `tools` parameter:

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

