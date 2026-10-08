<a id="step-4"></a>

# Step 4 — Examine orchestration inconsistencies

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
