<a id="comparison"></a>

# Compare the A2A and skills-based versions

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

# What this tutorial demonstrates

## A tool is enough for an atomic operation

`campaign_quote(sector, impressions)` is self-describing and deterministic.
The model can often invoke it correctly without a skill.

## A skill is valuable when it adds policy

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

## MCP and skills solve different problems

MCP exposes the operations. The skills define how to orchestrate them.

```text
MCP tool:
What can the system do?

Skill:
When and according to which procedure should it do it?
```

## A2A remains appropriate for real autonomy

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

## The final decision rule

Use:

- a **tool** for an atomic capability;
- **MCP** when that capability must be shared remotely;
- a **skill** for reusable workflow and policy;
- **A2A** for delegation to a genuinely autonomous agent.
