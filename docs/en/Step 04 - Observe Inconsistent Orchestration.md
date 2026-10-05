<a id="step-4"></a>

# Step 4 — Observe inconsistent orchestration

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

