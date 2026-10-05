# From a MAF Agent to a Full Skills-Based Solution

AI skills were [announced by Anthropic](https://claude.com/blog/skills) in
October 2025 and spread very rapidly. The key—and far from obvious—question is
now where they make sense, because the capabilities they provide already
existed before skills. Skills can therefore be considered an alternative to a
system prompt or to tools and, in some cases, even a way to optimize
multi-agent systems built around A2A.

To explain how to manage these potential overlaps while also showing how to
use skills in practice, this tutorial is aimed at developers and solution
architects. It starts with a minimal Microsoft Agent Framework (MAF) agent and
builds a complete skills-based solution through function calling, tools, an
MCP server, and A2A.

The scenario follows an analyst at AdvertSphere Broadcasting, a fictitious
company that sells advertising space for a television network.

Across seven incremental steps, described and implemented in this public
GitHub repository, you will build a complete solution from scratch that gives
the analyst:

- access to authoritative campaign data;
- consistent portfolio reviews;
- a campaign quotation service.

In the final part of the tutorial, you will first implement the solution with
a multi-agent approach based on
[A2A, announced by Google six months before skills](https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/).
This approach remains entirely valid today, but skills now give us an
opportunity to evaluate a possible optimization in some cases: effectively
moving the A2A agent's capabilities into a skill and using the orchestrating
agent's LLM.

Follow the steps in order if you want to implement the solution end to end. If
you are using the tutorial as an architecture reference, use the table of
contents to jump directly to the pattern or comparison you need.

The table of contents, requirements, and environment setup follow. Then we
will begin with the first implementation step: creating a minimal Agent
Framework agent.

## Table of contents

- [Prerequisites](#prerequisites)
- [Step 1 — Create a minimal MAF agent](<./Step 01 - Create a Minimal MAF Agent.md>)
- [Step 2 — Add local function tools](<./Step 02 - Add Local Function Tools.md>)
- [Step 3 — Move the tools to an MCP server](<./Step 03 - Move Tools to an MCP Server.md>)
- [Step 4 — Observe inconsistent orchestration](<./Step 04 - Observe Inconsistent Orchestration.md>)
- [Step 5 — Add the `campaign-performance-review` skill](<./Step 05 - Add the Campaign Performance Review Skill.md>)
- [Step 6 — Add an LLM-backed A2A pricing agent](<./Step 06 - Add an LLM-Based A2A Pricing Agent.md>)
- [Step 7 — Replace the A2A pricing agent with a skill](<./Step 07 - Replace the A2A Pricing Agent with a Skill.md>)
- [Compare the A2A and skills-based versions](<./Comparison and Conclusions.md#comparison>)
- [Conclusions](<./Comparison and Conclusions.md#conclusions>)

<a id="prerequisites"></a>

## Prerequisites

This tutorial assumes:

- Python 3.13 or later;
- `agent-framework==1.19.0`;
- `fastmcp==3.4.7`;
- `a2a-sdk==1.1.5`;
- `uvicorn==0.54.0`;
- an Azure OpenAI deployment configured through the existing environment
  variables;
- an authenticated Azure CLI session.

The examples use the following variables:

```text
AZURE_OPENAI_ENDPOINT
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME
```

The suggested project layout is:

```text
labs/
├── agent_campaign_mcp.py
├── campaign_data.py
├── campaign_agent.py
├── pricing_a2a_agent.py
└── skills/
    ├── campaign-performance-review/
    │   └── SKILL.md
    └── campaign-quotation-policy/
        └── SKILL.md
```

The exact filenames are not important. What matters is how responsibilities
move across the seven stages.

---
