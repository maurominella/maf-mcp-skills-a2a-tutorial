<a id="step-7"></a>

# Step 7 — Replace the A2A pricing agent with a skill

The A2A implementation works, but it adds:

- a second deployed agent;
- another LLM-backed reasoning loop;
- an A2A HTTP/JSON-RPC round trip;
- serialization and deserialization;
- another lifecycle, health, authentication, and retry boundary.

The quotation policy is deterministic enough to be transferred to a skill.
That skill instructs the main agent to call `campaign_quote` directly,
effectively removing the A2A agent from the architecture.

This does not eliminate LLM usage. The main LLM still:

- recognizes the quotation request;
- requests the quotation skill;
- interprets its policy;
- extracts sector and impressions;
- calculates the ±20% impression volumes;
- requests the three MCP tool calls;
- formats the final response.

It does eliminate the second LLM-backed agent and the A2A service hop.

## 7.1 Create the quotation skill

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

## 7.2 Give the main agent direct access to `campaign_quote`

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

Run the new test. Because **Pets** is not a configured category, it
demonstrates that the default CPM was used:

---
Here is an indicative quotation for a Pets campaign at 10,000,000 impressions.

| Scenario | Impressions | CPM | Total price |
|---|---:|---:|---:|
| Lean | 8,000,000 | €15.00 | €120,000.00 |
| Requested | 10,000,000 | €15.00 | €150,000.00 |
| Extended | 12,000,000 | €15.00 | €180,000.00 |

Default-rate warning: the Pets sector was priced with the default CPM.

These figures are indicative quotations, not an approved commercial offer.

---

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

