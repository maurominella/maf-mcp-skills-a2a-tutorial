import os
from contextlib import asynccontextmanager

import uvicorn
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
)
from agent_framework import Agent, MCPStreamableHTTPTool
from agent_framework.a2a import A2AExecutor
from agent_framework.openai import OpenAIChatClient
from azure.identity import AzureCliCredential
from dotenv import load_dotenv
from starlette.applications import Starlette

load_dotenv()

pricing_mcp = MCPStreamableHTTPTool(
    name="campaign_pricing_mcp",
    url="http://127.0.0.1:8000/mcp",
    allowed_tools={"campaign_quote"},
    approval_mode="never_require",
    load_prompts=False,
)

pricing_agent = Agent(
    client=OpenAIChatClient(
        model=os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"],
        credential=AzureCliCredential(),
    ),
    name="PricingAgent",
    description="Creates policy-compliant advertising campaign quotations.",
    instructions=(
        "Extract the sector and requested impressions from the user's request. "
        "Reject missing or non-positive impressions. Create three scenarios: "
        "lean with 20 percent fewer impressions, requested with the original "
        "volume, and extended with 20 percent more impressions. Use the "
        "campaign_quote tool for every scenario and every monetary value. "
        "Never calculate or alter CPM values yourself. Warn if a default "
        "sector rate is used. Return a comparison table."
    ),
    tools=[pricing_mcp],
)

pricing_skill = AgentSkill(
    id="campaign-quotation",
    name="Campaign quotation",
    description=(
        "Creates lean, requested, and extended campaign quotation scenarios."
    ),
    tags=["pricing", "advertising", "quotation"],
    examples=[
        "Create a quote for a Travel campaign with 9,200,000 impressions."
    ],
)

agent_card = AgentCard(
    name="AdvertSphere Pricing Agent",
    description="A policy-aware advertising pricing agent.",
    version="1.0.0",
    default_input_modes=["text"],
    default_output_modes=["text"],
    capabilities=AgentCapabilities(),
    skills=[pricing_skill],
    supported_interfaces=[
        AgentInterface(
            url="http://127.0.0.1:9000/",
            protocol_binding="JSONRPC",
        )
    ],
)

handler = DefaultRequestHandler(
    agent_executor=A2AExecutor(pricing_agent),
    task_store=InMemoryTaskStore(),
    agent_card=agent_card,
)


@asynccontextmanager
async def lifespan(app: Starlette):
    async with pricing_agent:
        yield


app = Starlette(
    routes=[
        *create_agent_card_routes(agent_card),
        *create_jsonrpc_routes(handler, rpc_url="/"),
    ],
    lifespan=lifespan,
)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=9000)