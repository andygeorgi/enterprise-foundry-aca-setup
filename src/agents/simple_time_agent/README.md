# Simple Time Agent

A minimal example of using Foundry's agent framework with a code-based tool (v2 API).

## Overview

This agent demonstrates:
- Creating an agent with Azure AI Project Agent Provider (v2 API)
- Defining a code-based tool using the `@tool` decorator
- Running an agent with function calling capabilities using `agent.run()`
- Basic conversation flow with tool execution

## The Tool

The `get_current_time` tool:
- Takes an optional timezone parameter
- Returns the current time in that timezone
- Handles errors gracefully

## Prerequisites

1. **Azure AI Services**: Foundry deployed via Terraform (already done!)
2. **Authentication**: Azure CLI login (`az login`)
3. **Environment Variables** (required):
   
   ```bash
   export AZURE_AI_PROJECT_ENDPOINT="https://foundry-sbx.services.ai.azure.com/api/projects/default-project"
   ```
   
   The agent uses the deployed Foundry instance with GPT-4.1 model.

## Installation

```bash
cd /workspaces/enterprise-foundry-aca-setup/src/agents/simple_time_agent
pip install -r requirements.txt
```

## Usage

### Quick Run (Uses Deployed Foundry)

```bash
cd /workspaces/enterprise-foundry-aca-setup/src/agents/simple_time_agent
export AZURE_AI_PROJECT_ENDPOINT="https://foundry-sbx.services.ai.azure.com/api/projects/default-project"
python simple_time_agent.py
```

The agent automatically uses:
- **Endpoint**: Configured via `AZURE_AI_PROJECT_ENDPOINT`
- **Model**: `gpt-4.1` (deployed via Terraform)

### Expected Output

The agent will:
1. Create an agent with the time tool
2. Ask the time in different timezones
3. Respond using the tool

Example interaction:
```
User: What time is it?
Agent: The current time in UTC is Thursday, February 5, 2026 at 8:51 AM. If you need the time in a different timezone, just let me know!

User: What time is it in US/Eastern?
Agent: The current time in US/Eastern is Thursday, February 5, 2026, at 3:51 AM (EST).
```

## Code Structure (v2 API)

```python
# 1. Define the tool
@tool(approval_mode="never_require")
def get_current_time(timezone_name: str = "UTC") -> str:
    # Tool implementation
    pass

# 2. Create agent with tool using v2 API
async with (
    AzureCliCredential() as credential,
    AzureAIProjectAgentProvider(
        credential=credential,
        project_endpoint=project_endpoint
    ) as provider,
):
    agent = await provider.create_agent(
        model="gpt-4.1",
        name="TimeAgent",
        instructions="...",
        tools=get_current_time,
    )
    
    # 3. Run conversations using agent.run()
    result = await agent.run("What time is it?")
```

## Customization

### Add More Tools

```python
@tool(approval_mode="never_require")
def get_timezone_info(timezone_name: str) -> str:
    """Get information about a timezone."""
    # Implementation
    pass

# Add to agent
agent = await provider.create_agent(
    tools=[get_current_time, get_timezone_info],
)
```

### Interactive Mode

For interactive conversation, replace the example queries with:

```python
while True:
    user_input = input("\nYou: ")
    if user_input.lower() in ['exit', 'quit']:
        break
    
    # Send message and get response
    # ... (same pattern as example)
```

## Notes

- The `approval_mode="never_require"` setting allows automatic tool execution
- For production, consider using `approval_mode="always_require"` for safety
- The agent automatically determines when to call the tool based on the conversation
- Multiple tools can be added to provide more capabilities

## Troubleshooting

### Authentication Errors
Make sure you're logged in with Azure CLI:
```bash
az login
az account show
```

### Missing Environment Variables
The agent uses sensible defaults from your deployed infrastructure:
```bash
# These are set by default:
AZURE_FOUNDRY_ENDPOINT="https://foundry-sbx.cognitiveservices.azure.com/"
GPT4_DEPLOYMENT="gpt-4.1"
```

### Module Not Found
Install dependencies:
```bash
pip install -r requirements.txt
```
