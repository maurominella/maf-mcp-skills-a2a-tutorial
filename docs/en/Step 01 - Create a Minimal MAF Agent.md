<a id="step-1"></a>

# Step 1 — Create a minimal MAF agent

Start with an agent that has only:

- a name;
- instructions;
- an LLM client.

It has no tools, MCP connection, skills, or A2A agents.

```python
import asyncio
import os

from agent_framework import Agent
from agent_framework.openai import OpenAIChatClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()


async def main() -> None:
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
    )

    answer = await maf_agent.run(
        "Review campaign CMP-004 and calculate its ROI."
    )
    print(answer.text)


if __name__ == "__main__":
    asyncio.run(main())
```

The example runs successfully. However, the agent can explain ROI in general
but cannot retrieve authoritative campaign data. We therefore expect an answer
such as *I can help calculate ROI for CMP-004, but I don’t have the campaign's
performance data in this chat*.

At this stage, the architecture is:

```text
User
  ↓
MAF agent
  ↓
LLM
```

---

