# From a MAF Agent to a Full Skills-Based Solution

A hands-on, step-by-step tutorial for building solutions with
[Microsoft Agent Framework](https://github.com/microsoft/agent-framework),
local function tools, Model Context Protocol (MCP) servers, Agent Skills, and
Agent2Agent (A2A) orchestration.

The repository contains both the complete documentation and runnable Python
labs. Each of the seven tutorial steps has a corresponding `labs-stepNN.py`
file under [`labs/`](./labs), making it possible to follow the architectural
progression in the documentation and run the matching implementation.

## AdvertSphere Broadcasting

The tutorial uses **AdvertSphere Broadcasting (ASB)**, a fictional advertising
concessionaire that sells advertising space for a television network. The same
company provides the shared business context for the
[Microsoft AI Upskilling](https://github.com/maurominella/microsoft-ai-upskilling)
repository:

> Everything is taught against **one coherent business scenario** —
> *AdvertSphere Broadcasting (ASB)*, a fictional advertising concessionaire
> spanning TV, radio, streaming, digital, and social. Every demo, lab, and
> evaluation builds on the same realistic context, so you're solving a
> real-shaped problem instead of disconnected toy examples.

[![AdvertSphere Broadcasting](https://raw.githubusercontent.com/maurominella/microsoft-ai-upskilling/main/_IMAGES/AdvertSphere%20Broadcasting.jpg)](https://github.com/maurominella/microsoft-ai-upskilling/blob/main/_IMAGES/AdvertSphere%20Broadcasting.jpg)

In this tutorial, an ASB analyst needs to:

- retrieve authoritative advertising campaign data;
- calculate and compare campaign ROI;
- review an entire campaign portfolio consistently;
- create policy-compliant campaign quotations;
- decide when an autonomous A2A agent is justified and when a skill is a
  simpler alternative.

## Documentation

The complete tutorial is available in two languages:

- [English documentation](./docs/en/README.md)
- [Documentazione italiana](./docs/it/README.md)

Both versions contain the same seven-step journey, followed by a comparison of
the A2A and skills-based architectures and the final design guidelines.

## Tutorial and lab map

| Step | What it demonstrates | Documentation | Python lab |
|---:|---|---|---|
| 1 | Create a minimal Microsoft Agent Framework agent backed by Azure OpenAI. | [English](<./docs/en/Step 01 - Create a Minimal MAF Agent.md>) · [Italiano](<./docs/it/Step 01 - Create a Minimal MAF Agent.md>) | [`labs-step01.py`](./labs/labs-step01.py) |
| 2 | Add deterministic local function tools for campaign discovery, metrics, and ROI. | [English](<./docs/en/Step 02 - Add Local Function Tools.md>) · [Italiano](<./docs/it/Step 02 - Add Local Function Tools.md>) | [`labs-step02.py`](./labs/labs-step02.py) |
| 3 | Move the campaign tools behind an MCP server and consume them through `MCPStreamableHTTPTool`. | [English](<./docs/en/Step 03 - Move Tools to an MCP Server.md>) · [Italiano](<./docs/it/Step 03 - Move Tools to an MCP Server.md>) | [`labs-step03.py`](./labs/labs-step03.py) |
| 4 | Observe why access to tools alone does not guarantee consistent orchestration. | [English](<./docs/en/Step 04 - Observe Inconsistent Orchestration.md>) · [Italiano](<./docs/it/Step 04 - Observe Inconsistent Orchestration.md>) | [`labs-step04.py`](./labs/labs-step04.py) |
| 5 | Add the `campaign-performance-review` skill to provide a reusable portfolio-review procedure. | [English](<./docs/en/Step 05 - Add the Campaign Performance Review Skill.md>) · [Italiano](<./docs/it/Step 05 - Add the Campaign Performance Review Skill.md>) | [`labs-step05.py`](./labs/labs-step05.py) |
| 6 | Add an LLM-backed A2A pricing agent that applies quotation policy and uses an MCP pricing tool. | [English](<./docs/en/Step 06 - Add an LLM-Based A2A Pricing Agent.md>) · [Italiano](<./docs/it/Step 06 - Add an LLM-Based A2A Pricing Agent.md>) | [`labs-step06.py`](./labs/labs-step06.py) |
| 7 | Replace the pricing A2A agent with a skill and let the main agent call the MCP pricing tool directly. | [English](<./docs/en/Step 07 - Replace the A2A Pricing Agent with a Skill.md>) · [Italiano](<./docs/it/Step 07 - Replace the A2A Pricing Agent with a Skill.md>) | [`labs-step07.py`](./labs/labs-step07.py) |

The architectural comparison and conclusions are also available in
[English](<./docs/en/Comparison and Conclusions.md>) and
[Italian](<./docs/it/Comparison and Conclusions.md>).

## Supporting components

The [`labs/`](./labs) directory also contains the shared services and assets
used by the seven implementations:

- [`asb_campaign.py`](./labs/asb_campaign.py): the deterministic campaign
  dataset used throughout the tutorial;
- [`agent_campaign_mcp.py`](./labs/agent_campaign_mcp.py): the MCP server that
  exposes campaign analysis and pricing tools;
- [`pricing_a2a_agent.py`](./labs/pricing_a2a_agent.py): the standalone A2A
  pricing agent introduced in Step 6;
- [`skills/`](./labs/skills): the campaign review and quotation-policy skills.

## Getting started

1. Review the [environment preparation guide](./environment_preparation.md).
2. Create and configure the required `.env` file from
   [`.env.example`](./.env.example).
3. Start with the [English tutorial](./docs/en/README.md) or the
   [Italian tutorial](./docs/it/README.md).
4. Run the matching Python file in [`labs/`](./labs) as you progress through
   each step.

The later steps require the MCP server and, for Step 6, the A2A pricing agent
to be running. The relevant documentation pages include the exact commands and
execution order.
