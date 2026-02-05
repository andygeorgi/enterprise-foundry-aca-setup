"""
Sample Foundry Agent with Tools

This demonstrates a minimal agent using Foundry's agent framework
with code-based tools (time and network connectivity).
"""
import asyncio
from datetime import datetime, timezone
from typing import Annotated

from agent_framework import tool
from agent_framework.azure import AzureAIProjectAgentProvider
from azure.identity.aio import DefaultAzureCredential
from pydantic import Field
from agent_framework.devui import serve


# Define a code-based tool to tell the time
@tool(approval_mode="never_require")
def get_current_time(
    timezone_name: Annotated[
        str, 
        Field(description="Timezone name (e.g., 'UTC', 'US/Eastern', 'Europe/London'). Defaults to UTC.")
    ] = "UTC",
) -> str:
    """
    Get the current time in a specified timezone.
    
    Returns the current date and time formatted as a human-readable string.
    """
    try:
        import pytz
        
        # Get current UTC time
        current_utc = datetime.now(timezone.utc)
        
        # Convert to requested timezone
        if timezone_name.upper() == "UTC":
            tz = pytz.UTC
        else:
            tz = pytz.timezone(timezone_name)
        
        local_time = current_utc.astimezone(tz)
        
        # Format the time nicely
        formatted_time = local_time.strftime("%A, %B %d, %Y at %I:%M:%S %p %Z")
        
        return f"The current time in {timezone_name} is: {formatted_time}"
    
    except Exception as e:
        return f"Error getting time for timezone '{timezone_name}': {str(e)}"


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

import os

async def create_agent():
    # Get project endpoint from environment variable
    project_endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT", "https://foundry-sbx.services.ai.azure.com/api/projects/default-project")
    if not project_endpoint:
        raise ValueError(
            "AZURE_AI_PROJECT_ENDPOINT environment variable must be set. "
            "Example: https://<your-project>.services.ai.azure.com/api/projects/<project-name>"
        )
    
    # Get model deployment name from environment variable
    model_deployment = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-4.1")
    
    # Use DefaultAzureCredential for authentication (supports managed identity in ACA)
    async with (
        DefaultAzureCredential() as credential,
        AzureAIProjectAgentProvider(
            credential=credential,
            project_endpoint=project_endpoint
        ) as provider,
    ):
        # Create an agent with the tools
        print(f"Creating agent (model: {model_deployment})...")
        agent = await provider.create_agent(
            model=model_deployment,
            name="SampleAgent",
            instructions="""You are a helpful assistant. When asked about the time,
use the get_current_time tool to provide accurate information.
You can tell time in any timezone the user requests.
You can also ping the private VM to test connectivity.
Be friendly and concise in your responses.""",
            tools=[get_current_time, ping_private_vm],
        )
        print(f"✓ Agent created: {agent.id}\n")
        return agent


# Run the agent creation and serve
agent = asyncio.run(create_agent())
serve(entities=[agent], port=8081, auto_open=True)

