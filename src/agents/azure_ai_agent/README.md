# Azure AI Network Monitoring Agent

This agent demonstrates using the Microsoft Agent Framework with Azure AI to monitor network connectivity to private infrastructure.

## Overview

The agent includes tools to:
- **Ping private IP addresses** - Test ICMP connectivity to private resources
- **Check network status** - Verify connectivity to the simulated on-premises VM (10.7.1.4)
- **Get current time** - Retrieve UTC timestamp for logging

## Setup

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Authenticate with Azure:
```bash
az login
```

3. Ensure you have:
   - An Azure AI project configured with the necessary permissions
   - Network connectivity to the private infrastructure (VPN must be active if testing from local machine)

## Running the Agent

Execute the agent example:
```bash
python azure_ai_agent.py
```

## Use Cases

### Network Monitoring Agent
Monitors connectivity to private infrastructure and provides status reports. This agent can:
- Check if the on-premises VM (10.7.1.4) is reachable
- Provide network status updates
- Combine connectivity checks with timestamp information

### Infrastructure Monitoring Agent
Focused on infrastructure health verification with detailed ping diagnostics.

## Tools Reference

### `ping_private_ip(ip_address, count=4)`
Pings a private IP address to test network connectivity.
- **ip_address**: The private IP to ping
- **count**: Number of ICMP packets to send (default: 4)
- **Returns**: Success/failure status with packet statistics

### `check_network_status(vm_ip="10.7.1.4")`
Checks connectivity status to the on-premises simulated VM.
- **vm_ip**: The VM IP address (default: 10.7.1.4)
- **Returns**: Operational status or error message

### `get_time()`
Returns the current UTC timestamp.

## Private Infrastructure

The simulated on-premises VM is deployed at:
- **IP Address**: 10.7.1.4
- **Location**: On-premises simulation VNet
- **Access**: Requires active VPN connection or deployment within Azure VNet

## Production Considerations

- **Approval Mode**: The sample uses `approval_mode="never_require"` for brevity. In production, use `approval_mode="always_require"` for security.
- **Authentication**: Replace `AzureCliCredential` with your preferred method (Managed Identity, Service Principal, etc.)
- **Error Handling**: Add comprehensive error handling and retry logic
- **Logging**: Implement structured logging for audit trails
- **Timeouts**: Adjust ping timeouts based on network latency requirements
- **Security**: Ensure proper network security groups and firewall rules are in place

## Network Prerequisites

Before running:
1. Ensure the on-premises simulation VM is deployed (via Terraform network module)
2. VPN connection is active if testing from outside Azure
3. Network security groups allow ICMP traffic
4. DNS resolution is properly configured

## Learn More

- [Microsoft Agent Framework](https://github.com/microsoft/agent-framework)
- [Azure AI Documentation](https://learn.microsoft.com/azure/ai-services/)
- [Azure VPN Gateway](https://learn.microsoft.com/azure/vpn-gateway/)
