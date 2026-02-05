# Sample Agent

A minimal example of using Foundry's agent framework with code-based tools (v2 API).

## Overview

This agent demonstrates:
- Creating an agent with Azure AI Project Agent Provider (v2 API)
- Defining code-based tools using the `@tool` decorator
- Running an agent with function calling capabilities using `agent.run()`
- Basic conversation flow with tool execution

## The Tools

1. **get_current_time** - Gets the current time in any timezone
2. **ping_private_vm** - Pings the private on-premises VM to test connectivity

## Prerequisites

1. **Azure AI Services**: Foundry deployed via Terraform (already done!)
2. **Authentication**: Azure CLI login (`az login`)
3. **Environment Variables** (required):
   
   ```bash
   export AZURE_AI_PROJECT_ENDPOINT="https://foundry-sbx.services.ai.azure.com/api/projects/default-project"
   export AZURE_AI_MODEL_DEPLOYMENT_NAME="gpt-4.1"
   ```

## Installation

```bash
cd /workspaces/enterprise-foundry-aca-setup/src/agents/sample_agent
pip install -r requirements.txt
```

## Usage

### Quick Run

```bash
cd /workspaces/enterprise-foundry-aca-setup/src/agents/sample_agent
export AZURE_AI_PROJECT_ENDPOINT="https://foundry-sbx.services.ai.azure.com/api/projects/default-project"
export AZURE_AI_MODEL_DEPLOYMENT_NAME="gpt-4.1"
python sample_agent.py
```

### Expected Output

The agent will:
1. Create an agent with tools
2. Ask questions and use the appropriate tools
3. Respond with results

Example interactions:
```
User: What time is it?
Agent: The current time in UTC is Thursday, February 5, 2026 at 8:59 AM.

User: Can you ping the private VM?
Agent: I tried to ping the private VM, but it is not reachable (ping failed).

User: What time is it in US/Eastern?
Agent: The current time in US/Eastern is Thursday, February 5, 2026, at 3:59 AM EST.
```

## Code Structure (v2 API)

```python
# 1. Define tools
@tool(approval_mode="never_require")
def get_current_time(timezone_name: str = "UTC") -> str:
    # Tool implementation
    pass

@tool(approval_mode="never_require")
def ping_private_vm() -> str:
    # Tool implementation
    pass

# 2. Create agent with tools using v2 API
async with (
    AzureCliCredential() as credential,
    AzureAIProjectAgentProvider(
        credential=credential,
        project_endpoint=project_endpoint
    ) as provider,
):
    agent = await provider.create_agent(
        model=model_deployment,
        name="TimeAgent",
        instructions="...",
        tools=[get_current_time, ping_private_vm],
    )
    
    # 3. Run conversations using agent.run()
    result = await agent.run("What time is it?")
```

## Customization

### Add More Tools

```python
@tool(approval_mode="never_require")
def your_custom_tool(param: str) -> str:
    """Your tool description."""
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
