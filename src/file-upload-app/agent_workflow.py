#!/usr/bin/env python3
"""
Agent Workflow – Sequential orchestration (Foundry v2)
======================================================

Uses Microsoft **agent-framework** with ``AzureAIProjectAgentProvider``
to run a **three-step sequential chain**:

1. **DesignDocAgent**   – extracts ``medical_cleaning`` (yes/no) and
   ``item_no`` from the design document.
2. **OtherDocAgent**    – given the Item No, extracts ``min_pressure``,
   ``max_pressure``, ``min_temperature``, ``max_temperature`` from
   the supporting document.
3. **SelectionAgent**   – merges both JSON payloads into a single
   consolidated result.

Environment variables (add to ``.env``):
  AZURE_AI_PROJECT_ENDPOINT          – Foundry project endpoint
  AZURE_AI_MODEL_DEPLOYMENT_NAME     – Deployed model name (e.g. gpt-4.1)
  AI_SEARCH_PROJECT_CONNECTION_ID    – Azure AI Search connection ID in Foundry (optional)
  AI_SEARCH_INDEX_NAME               – Index name (default: heat-exchangers)
  SHAREPOINT_PROJECT_CONNECTION_ID   – SharePoint connection ID in Foundry (optional)
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Load .env from the same directory as this file
_env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(_env_path)

# ---------------------------------------------------------------------------
# Lazy imports – app stays functional even when agent-framework is missing
# ---------------------------------------------------------------------------
_AGENT_FRAMEWORK_AVAILABLE = False
_import_error: str | None = None

try:
    from agent_framework.azure import AzureAIProjectAgentProvider
    from azure.identity.aio import AzureCliCredential

    _AGENT_FRAMEWORK_AVAILABLE = True
except ImportError as exc:
    _import_error = str(exc)
    print(f"⚠️  agent-framework import failed: {_import_error}")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_agent_available() -> bool:
    """Return True when agent-framework is installed and Foundry project is configured."""
    if not _AGENT_FRAMEWORK_AVAILABLE:
        return False
    return bool(os.getenv("AZURE_AI_PROJECT_ENDPOINT"))


def _is_ai_search_configured() -> bool:
    """Return True when an AI Search connection is configured in the Foundry project."""
    return bool(os.getenv("AI_SEARCH_PROJECT_CONNECTION_ID"))


def _build_ai_search_tool() -> dict | None:
    """Build the ``azure_ai_search`` tool definition for the agent framework.

    Returns the tool dict to pass to ``create_agent(tools=...)`` or ``None``
    when AI Search is not configured (no connection ID provided).
    """
    connection_id = os.getenv("AI_SEARCH_PROJECT_CONNECTION_ID", "")
    if not connection_id:
        return None

    index_name = os.getenv("AI_SEARCH_INDEX_NAME", "heat-exchangers")

    return {
        "type": "azure_ai_search",
        "azure_ai_search": {
            "indexes": [
                {
                    "project_connection_id": connection_id,
                    "index_name": index_name,
                    "query_type": "vector",
                }
            ]
        },
    }


def _build_sharepoint_tool() -> dict | None:
    """Build the ``sharepoint_grounding_preview`` tool definition.

    Returns the tool dict to pass to ``create_agent(tools=...)`` or ``None``
    when SharePoint is not configured (no connection ID provided).
    """
    connection_id = os.getenv("SHAREPOINT_PROJECT_CONNECTION_ID", "")
    if not connection_id:
        return None

    return {
        "type": "sharepoint_grounding_preview",
        "sharepoint_grounding_preview": {
            "project_connections": [
                {
                    "project_connection_id": connection_id,
                }
            ]
        },
    }


# ---------------------------------------------------------------------------
# Agent instructions
# ---------------------------------------------------------------------------

_DESIGN_DOC_AGENT_INSTRUCTIONS = """\
You are an expert **design document analyst**.

You receive the markdown content extracted from an uploaded design document.

Your task:
1. Determine whether the item described requires **medical cleaning** (yes or no).
2. Extract the **Item No** (part number / item number) from the document.

You MUST respond with **only** a valid JSON object – no markdown fences, no
commentary, no extra text.  The JSON schema is:

{
  "medical_cleaning": "yes" or "no",
  "item_no": "<string>"
}

If you cannot determine a field, use null for its value.
"""

_OTHER_DOC_AGENT_INSTRUCTIONS = """\
You are an expert **specifications analyst**.

You receive:
- The markdown content of a supporting / specifications document.
- An **Item No** to look up.

Your task:
1. Find the entry for the given Item No in the document.
2. Extract the **minimum and maximum pressure** and the **minimum and
   maximum temperature** for that item.

You MUST respond with **only** a valid JSON object – no markdown fences, no
commentary, no extra text.  The JSON schema is:

{
  "item_no": "<string>",
  "min_pressure": <number or null>,
  "max_pressure": <number or null>,
  "pressure_unit": "<string or null>",
  "min_temperature": <number or null>,
  "max_temperature": <number or null>,
  "temperature_unit": "<string or null>"
}

If you cannot determine a field, use null for its value.
"""

_SELECTION_AGENT_INSTRUCTIONS = """\
You are a **selection agent** that merges two JSON payloads produced by
previous analysis steps into one consolidated result **and** identifies
available heat exchangers that match the extracted specifications.

You receive:
- A JSON from the Design Document Agent with keys: medical_cleaning, item_no.
- A JSON from the Specifications Agent with keys: item_no, min_pressure,
  max_pressure, pressure_unit, min_temperature, max_temperature, temperature_unit.

You may have access to the following tools (use them when available):

• **Azure AI Search** – search an index for heat exchangers that satisfy the
  combined specification parameters (pressure range, temperature range,
  medical cleaning requirement).  Always provide citations using the format:
  `[ref_idx†source]`.
• **SharePoint** – search SharePoint sites for additional documentation or
  catalogue data about heat exchangers.

If a tool is not available or returns no results, simply omit the
corresponding key from your output.

Your task:
1. Merge both agent payloads into a single JSON object.
2. If there are conflicts on item_no, prefer the design document value.
3. Add a top-level "status" key set to "complete" when both inputs are
   present, or "partial" when one is missing or errored.
4. Use the available tools to find which heat exchangers are available
   based on the merged specification.  Include the results under the key
   "matching_heat_exchangers" as an array of objects.

You MUST respond with **only** a valid JSON object – no markdown fences,
no commentary, no extra text.  The JSON schema is:

{
  "status": "complete" or "partial",
  "item_no": "<string>",
  "medical_cleaning": "yes" or "no",
  "min_pressure": <number or null>,
  "max_pressure": <number or null>,
  "pressure_unit": "<string or null>",
  "min_temperature": <number or null>,
  "max_temperature": <number or null>,
  "temperature_unit": "<string or null>",
  "matching_heat_exchangers": [ ... ]   // optional
}
"""


# ---------------------------------------------------------------------------
# Helper: extract JSON from agent response (strip markdown fences if any)
# ---------------------------------------------------------------------------

def _extract_json(text: str) -> dict:
    """Best-effort extraction of a JSON object from agent text."""
    text = text.strip()
    # Strip ```json ... ``` fences
    if text.startswith("```"):
        lines = text.splitlines()
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"_raw": text}


# ---------------------------------------------------------------------------
# Sequential workflow (no WorkflowBuilder needed – plain async chain)
# ---------------------------------------------------------------------------

async def _run_sequential_analysis_async(
    design_content: str,
    other_content: str,
) -> dict:
    """
    Run a three-step sequential chain:
      1. DesignDocAgent  → {medical_cleaning, item_no}
      2. OtherDocAgent   → {min/max pressure/temperature}
      3. SelectionAgent  → merged final JSON

    Returns a result dict with keys: success, design_analysis, other_analysis,
    selection, messages.
    """
    project_endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT", "")
    model_deployment = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-4.1")

    result: dict[str, Any] = {
        "success": True,
        "design_analysis": "",
        "other_analysis": "",
        "selection": "",
        "messages": [],
    }

    async with (
        AzureCliCredential(process_timeout=30) as credential,
        AzureAIProjectAgentProvider(
            credential=credential,
            project_endpoint=project_endpoint,
        ) as provider,
    ):
        # ── Step 1: DesignDocAgent ────────────────────────────────────────
        design_agent = await provider.create_agent(
            model=model_deployment,
            name="DesignDocAgent",
            instructions=_DESIGN_DOC_AGENT_INSTRUCTIONS,
        )
        print(f"  ✓ DesignDocAgent created: {design_agent.id}")

        design_resp = await design_agent.run(
            f"Analyse this design document:\n\n{design_content}"
        )
        design_text = design_resp.text or ""
        design_json = _extract_json(design_text)
        result["design_analysis"] = json.dumps(design_json, indent=2)
        print(f"  ✓ DesignDocAgent result: {design_json}")

        result["messages"].append({
            "author": "DesignDocAgent",
            "role": "assistant",
            "text": result["design_analysis"],
        })

        # ── Step 2: OtherDocAgent ────────────────────────────────────────
        item_no = design_json.get("item_no", "unknown")

        other_agent = await provider.create_agent(
            model=model_deployment,
            name="OtherDocAgent",
            instructions=_OTHER_DOC_AGENT_INSTRUCTIONS,
        )
        print(f"  ✓ OtherDocAgent created: {other_agent.id}")

        other_resp = await other_agent.run(
            f"Item No to look up: **{item_no}**\n\n"
            f"Document content:\n\n{other_content}"
        )
        other_text = other_resp.text or ""
        other_json = _extract_json(other_text)
        result["other_analysis"] = json.dumps(other_json, indent=2)
        print(f"  ✓ OtherDocAgent result: {other_json}")

        result["messages"].append({
            "author": "OtherDocAgent",
            "role": "assistant",
            "text": result["other_analysis"],
        })

        # ── Step 3: SelectionAgent (with optional tools) ─────────────
        tools_list: list[dict] = []

        search_tool = _build_ai_search_tool()
        if search_tool is not None:
            tools_list.append(search_tool)
            print("  ✓ Azure AI Search tool attached to SelectionAgent")

        sharepoint_tool = _build_sharepoint_tool()
        if sharepoint_tool is not None:
            tools_list.append(sharepoint_tool)
            print("  ✓ SharePoint grounding tool attached to SelectionAgent")

        create_kwargs: dict[str, Any] = {
            "model": model_deployment,
            "name": "SelectionAgent",
            "instructions": _SELECTION_AGENT_INSTRUCTIONS,
        }
        if tools_list:
            create_kwargs["tools"] = tools_list
        else:
            print("ℹ️  No tools configured – SelectionAgent will run without tools")

        selection_agent = await provider.create_agent(**create_kwargs)
        print(f"  ✓ SelectionAgent created: {selection_agent.id}")

        selection_resp = await selection_agent.run(
            f"Design Document Agent output:\n```json\n"
            f"{json.dumps(design_json, indent=2)}\n```\n\n"
            f"Specifications Agent output:\n```json\n"
            f"{json.dumps(other_json, indent=2)}\n```\n\n"
            f"Use the search tool to find which heat exchangers are available "
            f"for the above specifications."
        )
        selection_text = selection_resp.text or ""
        selection_json = _extract_json(selection_text)
        result["selection"] = json.dumps(selection_json, indent=2)
        print(f"  ✓ SelectionAgent result: {selection_json}")

        result["messages"].append({
            "author": "SelectionAgent",
            "role": "assistant",
            "text": result["selection"],
        })

    return result


def run_document_analysis(
    design_content: str,
    other_content: str,
) -> dict:
    """
    Run sequential document analysis:
      DesignDocAgent → OtherDocAgent → SelectionAgent.

    Safe to call from synchronous Streamlit code – handles nested event loops.

    Returns
    -------
    dict  with keys ``success``, ``design_analysis``, ``other_analysis``,
          ``selection``, ``messages``, and optionally ``error``.
    """
    if not _AGENT_FRAMEWORK_AVAILABLE:
        return {
            "success": False,
            "error": f"agent-framework is not installed ({_import_error})",
            "design_analysis": "",
            "other_analysis": "",
            "selection": "",
            "messages": [],
        }

    try:
        # Streamlit may already have a running event loop
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(
                    asyncio.run,
                    _run_sequential_analysis_async(design_content, other_content),
                )
                return future.result(timeout=180)
        else:
            return asyncio.run(
                _run_sequential_analysis_async(design_content, other_content)
            )

    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
            "design_analysis": "",
            "other_analysis": "",
            "selection": "",
            "messages": [],
        }
