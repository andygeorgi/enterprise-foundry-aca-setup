"""
Sample Foundry Agent with Tools

This demonstrates a minimal agent using Foundry's agent framework
with code-based tools (network connectivity).
"""
import asyncio
from typing import Annotated

from agent_framework import tool, chat_middleware, ChatMessage
from agent_framework.azure import AzureAIProjectAgentProvider
from azure.ai.agents.models import SharepointToolDefinition, SharepointGroundingToolParameters, ToolConnection
from azure.identity.aio import DefaultAzureCredential
from pydantic import Field
from agent_framework.devui import serve
import os
import base64
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Directory to store uploaded files
UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)


# Middleware to inspect all chat messages sent to the AI model
@chat_middleware
async def inspect_messages_middleware(context, next):
    """Log all chat messages before and after the AI call."""
    print(f"\n{'='*60}")
    print(
        f"[Chat Middleware] Sending {len(context.messages)} message(s) to AI")
    print(f"[Chat Middleware] Streaming: {context.is_streaming}")
    for i, msg in enumerate(context.messages):
        role = getattr(msg, 'role', 'unknown')
        text = getattr(msg, 'text', None) or '(no text)'

        found_files = []
        for x, content in enumerate(getattr(msg, 'contents', [])):
            content_type = getattr(content, 'type', 'unknown')
            content_data = getattr(content, 'uri', None)
            media_type = getattr(content, 'media_type', None)
            additional_properties = getattr(
                content, 'additional_properties', None)
            filename = None
            if isinstance(additional_properties, dict):
                filename = additional_properties.get('filename', None)
            if content_data:
                label = f"[content {x} - type: {content_type}]"
                if filename:
                    label = f"[content {x} - type: {content_type} - filename: {filename}]"
                    save_result = save_file_to_disk(content_data, filename)
                    found_files.append((filename, save_result))
                text += f"\n{label} {str(content_data)}"

        # If files were found, replace the message with a new ChatMessage
        # that contains only text (no bulky base64 data)
        if found_files:
            original_text = getattr(msg, 'text', '') or ''
            file_descriptions = "\n".join(
                f"- {fname}: {result}" for fname, result in found_files
            )
            # Call parse_uploaded_file directly for each file
            parse_results = "\n".join(
                f"- {parse_uploaded_file(fname)}" for fname, _ in found_files
            )
            replacement_text = (
                f"{original_text}\n\n"
                f"The user uploaded the following files:\n{file_descriptions}\n"
                f"Files have been saved to the uploads directory.\n\n"
                f"Parse results:\n{parse_results}"
            ).strip()
            context.messages[i] = ChatMessage(
                role=msg.role, text=replacement_text
            )
            print(f"  [{i}] {role}: (replaced file message with text summary)")
            print(f"    Files: {[f for f, _ in found_files]}")
        else:
            # Truncate long messages for readability
            preview = text[:200] + '...' if len(text) > 200 else text
            print(f"  [{i}] {role}: {preview}")
    print(f"{'='*60}\n")

    await next(context)

    print(f"\n{'='*60}")
    print(f"[Chat Middleware] AI response received")
    print(f"{'='*60}\n")


def save_file_to_disk(content_data: str, filename: str) -> str:
    """
    Save base64-encoded file content to disk.

    Args:
        content_data: The data URI string (e.g. data:application/pdf;base64,...)
        filename: The filename to save as.

    Returns:
        A success or error message.
    """
    try:
        # Strip the data URI prefix if present
        if "," in content_data:
            content_data = content_data.split(",", 1)[1]

        file_bytes = base64.b64decode(content_data)

        # Add timestamp prefix to avoid collisions
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{filename}"
        filepath = os.path.join(UPLOADS_DIR, safe_filename)

        with open(filepath, "wb") as f:
            f.write(file_bytes)

        print(
            f"[File Saved] {safe_filename} ({len(file_bytes)} bytes) -> {filepath}")
        return f"File '{safe_filename}' saved successfully ({len(file_bytes)} bytes)."
    except Exception as e:
        print(f"[File Save Error] {filename}: {e}")
        return f"Error saving file '{filename}': {str(e)}"

# Define a tool to parse uploaded files


@tool(approval_mode="never_require")
def parse_uploaded_file(
    filename: Annotated[
        str,
        Field(description="The name of the uploaded file to parse.")
    ],
) -> str:
    """
    Parse an uploaded file. Call this tool whenever the user uploads a file.

    Returns the parsing result for the given file.
    """
    return f"parsed filename {filename}"


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
        sharepoint_connection_id = os.getenv(
            "SHAREPOINT_PROJECT_CONNECTION_ID")
        tools: list = [ping_private_vm]
        instructions = """You are a helpful assistant.
You can ping the private VM to test connectivity. Be friendly and concise in your responses."""

        if sharepoint_connection_id:
            tools.append(
                {
                    "type": "sharepoint_grounding_preview",
                    "sharepoint_grounding_preview": {
                        "project_connections": [
                            {
                                "project_connection_id": sharepoint_connection_id,
                            }
                        ]
                    },
                }
            )
            instructions = """You are a helpful assistant.
You can ping the private VM to test connectivity. Whenever the user uploads files, call parse_uploaded_file for each file. Whenever the user mentions travel questions, call the sharepoint_grounding_preview tool to retrieve relevant information from the connected SharePoint sites. Be friendly and concise in your responses."""

        # Create an agent with the tools
        print(f"Creating agent (model: {model_deployment})...")
        agent = await provider.create_agent(
            model=model_deployment,
            name="SampleAgent",
            instructions=instructions,
            tools=tools,
            middleware=[inspect_messages_middleware],
        )
        print(f"✓ Agent created: {agent.id}\n")
        return agent


# Run the agent creation and serve
agent = asyncio.run(create_agent())
serve(entities=[agent], port=8081, auto_open=True)
