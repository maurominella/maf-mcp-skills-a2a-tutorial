<a id="step-5"></a>

# Step 5 — Add the `campaign-performance-review` skill

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

Register a `SkillsProvider` and add it to the agent:

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

A typical response is substantially more standardized and adheres to the
requested format:

___
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
- No breakdown was available by audience, channel, or creative variant beyond the campaign-level channel label.
- No margin or lifetime value data was provided, so this recommendation is based on **revenue and ROI**, not net profit.
___

---

