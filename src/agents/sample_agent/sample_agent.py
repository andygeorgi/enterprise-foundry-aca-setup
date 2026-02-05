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
from azure.identity.aio import AzureCliCredential
from pydantic import Field


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
def ping_private_vm() -> str:
    """
    Ping the private on-premises VM to test connectivity.
    
    Returns the ping result showing if the VM is reachable.
    """
    import subprocess
    
    vm_ip = "10.7.1.4"  # Private on-prem VM IP
    
    try:
        # Ping with count of 3 and timeout of 5 seconds
        result = subprocess.run(
            ["ping", "-c", "3", "-W", "5", vm_ip],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            # Extract summary line from ping output
            lines = result.stdout.strip().split('\n')
            summary = [line for line in lines if 'packets transmitted' in line]
            if summary:
                return f"✓ VM at {vm_ip} is reachable. {summary[0]}"
            return f"✓ VM at {vm_ip} is reachable."
        else:
            return f"✗ VM at {vm_ip} is not reachable (ping failed)"
    
    except subprocess.TimeoutExpired:
        return f"✗ VM at {vm_ip} ping timeout"
    except Exception as e:
        return f"✗ Error pinging VM at {vm_ip}: {str(e)}"


async def main():
    """Main function to run the time agent."""
    
    import os
    
    # Get project endpoint from environment variable
    project_endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
    if not project_endpoint:
        raise ValueError(
            "AZURE_AI_PROJECT_ENDPOINT environment variable must be set. "
            "Example: https://<your-project>.services.ai.azure.com/api/projects/<project-name>"
        )
    
    # Get model deployment name from environment variable
    model_deployment = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-4.1")
    
    # For authentication, run `az login` command in terminal or replace
    # AzureCliCredential with preferred authentication option.
    async with (
        AzureCliCredential() as credential,
        AzureAIProjectAgentProvider(
            credential=credential,
            project_endpoint=project_endpoint
        ) as provider,
    ):
        # Create an agent with the time tool
        print(f"Creating agent with time tool (model: {model_deployment})...")
        agent = await provider.create_agent(
            model=model_deployment,
            name="TimeAgent",
            instructions="""You are a helpful time assistant. When asked about the time,
use the get_current_time tool to provide accurate information.
You can tell time in any timezone the user requests.
You can also ping the private VM to test connectivity.
Be friendly and concise in your responses.""",
            tools=[get_current_time, ping_private_vm],
        )
        print(f"✓ Agent created: {agent.id}\n")
        
        # Example interactions using agent.run()
        queries = [
            "What time is it?",
            "Can you ping the private VM?",
            "What time is it in US/Eastern?",
        ]
        
        for query in queries:
            print(f"{'='*60}")
            print(f"User: {query}")
            print(f"{'='*60}")
            
            # Run the agent with the query
            result = await agent.run(query)
            print(f"Agent: {result}\n")


if __name__ == "__main__":
    asyncio.run(main())
