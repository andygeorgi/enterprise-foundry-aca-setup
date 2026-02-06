"""
Sample Foundry Agent with Tools

This demonstrates a minimal agent using Foundry's agent framework
with code-based tools (network connectivity).
"""
import asyncio
from typing import Annotated

from agent_framework import tool
from agent_framework.azure import AzureAIProjectAgentProvider
from azure.ai.agents.models import SharepointToolDefinition, SharepointGroundingToolParameters, ToolConnection
from azure.identity.aio import DefaultAzureCredential
from pydantic import Field
from agent_framework.devui import serve
import os
from dotenv import load_dotenv

load_dotenv()

# Define a tool to ping the private VM
@tool(approval_mode="never_require")
def ping_private_vm(
    count: Annotated[
        int,
        Field(description="Number of ping attempts. Defaults to 3.")
    ] = 3,
) -> str:
    """
    Ping the private on-premises VM to test connectivity.
    
    Returns the ping result showing if the VM is reachable.
    """
    import subprocess
    
    vm_ip = "10.7.1.4"  # Private on-prem VM IP
    
    try:
        # Ping with specified count and timeout of 5 seconds
        result = subprocess.run(
            ["ping", "-c", str(count), "-W", "5", vm_ip],
            capture_output=True,
            text=True,
            timeout=15
        )
        
        if result.returncode == 0:
            # Extract summary line from ping output
            lines = result.stdout.strip().split('\n')
            summary = [line for line in lines if 'packets transmitted' in line]
            if summary:
                return f"VM at {vm_ip} is reachable. {summary[0]}"
            return f"VM at {vm_ip} is reachable."
        else:
            return f"VM at {vm_ip} is not reachable (ping failed)"
    
    except subprocess.TimeoutExpired:
        return f"VM at {vm_ip} ping timeout"
    except Exception as e:
        return f"Error pinging VM at {vm_ip}: {str(e)}"


"""Main function to run the agent."""

async def create_agent():
    # Get project endpoint from environment variable
    project_endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
    if not project_endpoint:
        raise ValueError(
            "AZURE_AI_PROJECT_ENDPOINT environment variable must be set. "
            "Example: https://<your-project>.services.ai.azure.com/api/projects/<project-name>"
        )
    
    # Get model deployment name from environment variable
    model_deployment = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")
    
    # DefaultAzureCredential: uses az CLI locally, managed identity in Azure.
    async with (
        DefaultAzureCredential() as credential,
        AzureAIProjectAgentProvider(
            credential=credential,
            project_endpoint=project_endpoint
        ) as provider,
    ):
        sharepoint_connection_id = os.getenv("SHAREPOINT_PROJECT_CONNECTION_ID")
        tools = [ping_private_vm]
        instructions = """You are a helpful assistant.
You can ping the private VM to test connectivity. Be friendly and concise in your responses."""

        if sharepoint_connection_id:
            tools.append(
                SharepointToolDefinition(
                    sharepoint_grounding=SharepointGroundingToolParameters(
                        connection_list=[
                            ToolConnection(connection_id=sharepoint_connection_id)
                        ]
                    )
                )
            )
            instructions = """You are a helpful assistant.
You can ping the private VM to test connectivity. Whenever the user mentions travel questions, call the sharepoint_grounding_preview tool to retrieve relevant information from the connected SharePoint sites. Be friendly and concise in your responses."""

        # Create an agent with the tools
        print(f"Creating agent (model: {model_deployment})...")
        agent = await provider.create_agent(
            model=model_deployment,
            name="SampleAgent",
            instructions=instructions,
            tools=tools,
        )
        print(f"✓ Agent created: {agent.id}\n")
        return agent


# Run the agent creation and serve
agent = asyncio.run(create_agent())
serve(entities=[agent], port=8081, auto_open=True)

