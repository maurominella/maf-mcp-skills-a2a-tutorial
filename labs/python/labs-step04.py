import asyncio
import os
from agent_framework import Agent
from agent_framework.openai import OpenAIChatClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from typing import Annotated
from pydantic import Field
from asb_campaign import get_campaign, list_campaigns

load_dotenv()

async def main() -> None:
    from agent_framework import Agent, MCPStreamableHTTPTool
    
    campaign_mcp = MCPStreamableHTTPTool(
        name="agent_campaign_mcp",
        url="http://127.0.0.1:8000/mcp",
        allowed_tools={
            "all_campaigns",
            "campaign_metrics",
            "compute_roi",
        },
        approval_mode="never_require",
        load_prompts=False,  # When True, also load MCP prompt resources, not only tools.
    )
    
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
        tools=[campaign_mcp],
    )

    async with maf_agent:
        for run_number in range(1, 5):
            response = await maf_agent.run(
                "Review the entire campaign portfolio and recommend which campaign "
                "should receive additional budget next quarter."
            )
            print(f"\n--- Run {run_number} ---")
            print(response.text)

    return response.text


if __name__ == "__main__":
    asyncio.run(main())