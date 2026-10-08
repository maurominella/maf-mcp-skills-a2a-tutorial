<a id="comparison"></a>

# Comparison of the A2A and skill-based approaches

Run both implementations with an identical request:

```text
Create a quote for a Travel campaign with 9,200,000 impressions.
```

This should produce the following impression volumes:

| Scenario | Impressions |
|---|---:|
| Lean | 7,360,000 |
| Requested | 9,200,000 |
| Extended | 11,040,000 |

With the Travel CPM set to EUR 16, the deterministic tool is expected to
produce:

| Scenario | Impressions | CPM | Total |
|---|---:|---:|---:|
| Lean | 7,360,000 | EUR 16 | EUR 117,760 |
| Requested | 9,200,000 | EUR 16 | EUR 147,200 |
| Extended | 11,040,000 | EUR 16 | EUR 176,640 |

Add instrumentation to each implementation and record:

- total end-to-end response time;
- LLM calls made by the primary agent;
- LLM calls made by the pricing agent;
- A2A request count;
- MCP tool invocation count;
- tokens sent and received;
- successful fulfillment of every policy rule.

A representative comparison looks like this:

| Aspect | A2A pricing agent | Skill with direct MCP access |
|---|---:|---:|
| Primary LLM | Needed | Needed |
| Additional LLM | Needed | Unnecessary |
| HTTP request over A2A | Needed | Unnecessary |
| Number of MCP calls | Three | Three |
| Where the policy resides | Pricing agent instructions | `SKILL.md` |
| Independent pricing service | Needed | Unnecessary |
| Skill loaded progressively | No | Yes |

The precise number of LLM calls varies with the selected model and its runtime
behavior. A standard skill-based flow usually introduces an LLM turn for
`load_skill`, while removing the remote pricing agent's full reasoning cycle.

The anticipated reduction in latency is achieved by removing:

1. LLM inference within the remote agent;
2. the HTTP/JSON-RPC round trip required by A2A;
3. serialization and deserialization for the A2A exchange;
4. management of an extra service lifecycle.

In most cases, avoiding inference in the second agent has a greater impact than
eliminating local HTTP communication and JSON processing by themselves.

---

<a id="conclusions"></a>

# Key lessons from this tutorial

## Atomic operations can be handled by a tool

`campaign_quote(sector, impressions)` is self-describing and deterministic.
In many cases, the model can call it correctly without needing a skill.

## Skills provide value when they introduce policy

The quotation skill matters because it defines behavior beyond the information
available in the tool schema:

- generation of three scenarios;
- application of the ±20% variation;
- validation of mandatory inputs;
- notification when the default rate is used;
- a prescribed response format;
- protection against changing authoritative prices.

If its only instruction were to read two arguments and invoke
`campaign_quote`, the skill would contribute very little and could simply add
an extra LLM turn.

## MCP and skills address distinct concerns

MCP makes operations available; skills establish the procedure for coordinating
them.

```text
MCP tool:
Which capabilities does the system provide?

Skill:
When should those capabilities be used, and what process should be followed?
```

## Genuine autonomy remains a valid use case for A2A

An A2A agent should not be replaced by a skill when the remote component has a
substantive independent role, for example:

- negotiations that maintain state;
- distinct ownership or security boundaries;
- approvals performed independently;
- operations that take a long time to complete;
- progress reported asynchronously;
- access to private resources the primary agent cannot reach;
- independent collaboration with other agents.

Under those conditions, the additional LLM and networking overhead is the cost
of maintaining a genuine architectural boundary.

## A practical selection rule

Choose:

- a **tool** when the capability is atomic;
- **MCP** when the capability needs to be available remotely;
- a **skill** to capture reusable procedures and policy;
- **A2A** when work must be delegated to a truly autonomous agent.
