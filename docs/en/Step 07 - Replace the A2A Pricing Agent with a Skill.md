<a id="step-7"></a>

# Step 7 — Replace the A2A pricing agent with a skill

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

## 7.1 Build the quotation skill

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

## 7.2 Allow the main agent to call `campaign_quote` directly

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
