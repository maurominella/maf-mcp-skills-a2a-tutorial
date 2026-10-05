<a id="passaggio-1"></a>

# Passaggio 1 — Creare un agente MAF minimale

Inizia con un agente che dispone soltanto di:

- un nome;
- istruzioni;
- un client LLM.

Non dispone di tool, connessioni MCP, skill o agenti A2A.

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

L'esempio viene eseguito senza errori. Tuttavia, l'agente può spiegare il ROI in generale, ma non può recuperare dati autorevoli sulle campagne. Ci attendiamo quindi una risposta del tipo *I can help calculate ROI for CMP-004, but I don’t have the campaign's performance data in this chat*.<br/>
In questa fase, l'architettura è:

```text
Utente
  ↓
Agente MAF
  ↓
LLM
```

---

