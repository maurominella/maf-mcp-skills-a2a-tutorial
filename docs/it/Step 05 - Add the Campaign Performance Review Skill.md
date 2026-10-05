<a id="passaggio-5"></a>

# Passaggio 5 — Aggiungere lo skill `campaign-performance-review`

Crea:

```text
skills/campaign-performance-review/SKILL.md
```

con il contenuto seguente:

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
- No breakdown was available by audience, channel, or creative variant beyond the campaign-level channellabel.
- No margin or lifetime value data was provided, so this recommendation is based on **revenue and ROI**,not net profit.
___


---

