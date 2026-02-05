# Copyright (c) Microsoft. All rights reserved.
import asyncio
import subprocess
from datetime import datetime, timezone
from typing import Annotated

from agent_framework import tool
from agent_framework.azure import AzureAIAgentsProvider
from azure.identity.aio import AzureCliCredential
from pydantic import Field

"""
Azure AI Agent with Function Tools Example

This agent demonstrates function tool integration with Azure AI Agents,
including network connectivity testing to private infrastructure.
"""

# NOTE: approval_mode="never_require" is for sample brevity. Use "always_require" in production; see
# samples/getting_started/tools/function_tool_with_approval.py and 
# samples/getting_started/tools/function_tool_with_approval_and_threads.py.


@tool(approval_mode="never_require")
def ping_private_ip(
    ip_address: Annotated[str, Field(description="The private IP address to ping.")],
    count: Annotated[int, Field(description="Number of ping packets to send.")] = 4,
) -> str:
    """
    Ping a private IP address to test network connectivity.
    
    This is useful for testing connectivity to on-premises resources
    or private Azure resources through VPN/ExpressRoute.
    """
    try:
        # Run ping command
        result = subprocess.run(
            ["ping", "-c", str(count), "-W", "2", ip_address],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            # Parse the output for packet loss and timing info
            lines = result.stdout.split('\n')
            stats = [line for line in lines if 'packets transmitted' in line or 'rtt min' in line]
            return f"✓ Ping to {ip_address} successful:\n" + "\n".join(stats)
        else:
            return f"✗ Ping to {ip_address} failed. Host may be unreachable or not responding to ICMP."
            
    except subprocess.TimeoutExpired:
        return f"✗ Ping to {ip_address} timed out after 10 seconds."
    except Exception as e:
        return f"✗ Error pinging {ip_address}: {str(e)}"


@tool(approval_mode="never_require")
def get_time() -> str:
    """Get the current UTC time."""
    current_time = datetime.now(timezone.utc)
    return f"The current UTC time is {current_time.strftime('%Y-%m-%d %H:%M:%S')}."


@tool(approval_mode="never_require")
def check_network_status(
    vm_ip: Annotated[str, Field(description="The VM IP address to check.")] = "10.7.1.4",
) -> str:
    """
    Check the network connectivity status to the on-premises simulated VM.
    
    Default IP is the simulated on-prem VM (10.7.1.4).
    """
    # Test connectivity
    try:
        result = subprocess.run(
            ["ping", "-c", "2", "-W", "2", vm_ip],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            return f"✓ Network connectivity to VM {vm_ip} is operational."
        else:
            return f"✗ Cannot reach VM {vm_ip}. VPN connection may be down."
            
    except Exception as e:
        return f"✗ Error checking network status: {str(e)}"


async def network_monitoring_agent() -> None:
    """Example showing an agent that monitors network connectivity to private infrastructure."""
    print("=== Network Monitoring Agent ===")
    
    # For authentication, run `az login` command in terminal or replace AzureCliCredential with preferred
    # authentication option.
    async with (
        AzureCliCredential() as credential,
        AzureAIAgentsProvider(credential=credential) as provider,
    ):
        agent = await provider.create_agent(
            name="NetworkMonitoringAgent",
            instructions=(
                "You are a network monitoring assistant that helps check connectivity "
                "to private infrastructure. You can ping IP addresses and provide network status reports. "
                "The on-premises simulated VM is at IP 10.7.1.4."
            ),
            tools=[ping_private_ip, check_network_status, get_time],
        )
        
        # Check connectivity to the simulated on-prem VM
        query1 = "Can you check if the on-premises VM at 10.7.1.4 is reachable?"
        print(f"\nUser: {query1}")
        result1 = await agent.run(query1)
        print(f"Agent: {result1}\n")
        
        # Get general network status
        query2 = "What's the current network status?"
        print(f"User: {query2}")
        result2 = await agent.run(query2)
        print(f"Agent: {result2}\n")
        
        # Combined query with time
        query3 = "Ping the VM and tell me the current time."
        print(f"User: {query3}")
        result3 = await agent.run(query3)
        print(f"Agent: {result3}\n")


async def infrastructure_agent() -> None:
    """Example showing an agent focused on infrastructure monitoring."""
    print("=== Infrastructure Monitoring Agent ===")
    
    async with (
        AzureCliCredential() as credential,
        AzureAIAgentsProvider(credential=credential) as provider,
    ):
        agent = await provider.create_agent(
            name="InfrastructureAgent",
            instructions=(
                "You are an infrastructure monitoring expert. You help verify connectivity "
                "and health of private network resources. Always provide clear status updates."
            ),
            tools=[ping_private_ip, check_network_status],
        )
        
        # Test with specific ping count
        query = "Ping 10.7.1.4 with 3 packets and report the results."
        print(f"\nUser: {query}")
        result = await agent.run(query)
        print(f"Agent: {result}\n")


async def main() -> None:
    print("=== Azure AI Agent - Network Monitoring Examples ===\n")
    print("This agent can test connectivity to private infrastructure,")
    print("specifically the simulated on-premises VM at 10.7.1.4\n")
    
    await network_monitoring_agent()
    await infrastructure_agent()


if __name__ == "__main__":
    asyncio.run(main())
