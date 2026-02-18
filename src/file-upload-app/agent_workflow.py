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
  SHAREPOINT_PROJECT_CONNECTION_ID   – SharePoint connection ID in Foundry (optional)
  DESIGN_FILE_MARKERS                – JSON array of markers for design docs (required)
  OTHER_FILE_MARKERS                 – JSON array of markers for other/specs docs (required)
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


# ---------------------------------------------------------------------------
# Content-based file classification
# ---------------------------------------------------------------------------

def get_design_markers() -> list[str]:
    """Return the list of first-page markers that identify a design document."""
    raw = os.getenv("DESIGN_FILE_MARKERS", "[]")
    try:
        markers = json.loads(raw)
    except json.JSONDecodeError:
        markers = [raw]  # fallback: treat entire value as a single marker
    if isinstance(markers, str):
        markers = [markers]
    return [m.strip() for m in markers if isinstance(m, str) and m.strip()]


def get_other_markers() -> list[str]:
    """Return the list of first-page markers that identify an other/specs document."""
    raw = os.getenv("OTHER_FILE_MARKERS", "[]")
    try:
        markers = json.loads(raw)
    except json.JSONDecodeError:
        markers = [raw]  # fallback: treat entire value as a single marker
    if isinstance(markers, str):
        markers = [markers]
    return [m.strip() for m in markers if isinstance(m, str) and m.strip()]


def classify_file_by_content(md_content: str) -> str | None:
    """Classify a file by scanning its first page content.

    Returns ``'design'``, ``'other'``, or ``None`` if no marker matched.
    Only the first ~3000 characters are checked (approximate first page).
    """
    first_page = md_content[:3000]

    for marker in get_design_markers():
        if marker.lower() in first_page.lower():
            return "design"

    for marker in get_other_markers():
        if marker.lower() in first_page.lower():
            return "other"

    return None


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
1. Determine whether the item described requires **mechanical cleaning** (hot and cold) (yes or no).
2. Extract the **Item No** (part number / item number) from the document.

You MUST respond with **only** a valid JSON object – no markdown fences, no
commentary, no extra text.  The JSON schema is:

{
  "mechanical_cleaning_hot": "yes" or "no",
  "mechanical_cleaning_cold": "yes" or "no",
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
You are a **selection agent** that finds available heat exchangers matching
a set of combined specifications.

You receive a **combined specification JSON** with keys: item_no,
mechanical_cleaning_hot, mechanical_cleaning_cold, min_pressure, max_pressure, pressure_unit,
min_temperature, max_temperature, temperature_unit.

You have access to tools to search for heat exchangers.  Use them to answer
the question: **"Which heat exchangers are available that fit these values?"**

When using tools:
• **SharePoint** – search SharePoint sites for catalogues, data sheets, or
  product lists of heat exchangers that match the specification values.
  Provide citations using: `[ref_idx†source]`.

Your task:
1. Use the available tools to search for heat exchangers that fit the
   provided specification (pressure range, temperature range, mechanical cleaning requirement).
2. Return a JSON object with the search results.

You MUST respond with **only** a valid JSON object – no markdown fences,
no commentary, no extra text.  The JSON schema is:

{
  "matching_heat_exchangers": [
    {
      "name": "<string>",
      "description": "<string>",
      "source": "<string>"
    }
  ]
}

If no matching heat exchangers are found, return:
{"matching_heat_exchangers": []}
"""

_ESTIMATION_AGENT_INSTRUCTIONS = """\
You are an expert **heat exchanger calculation analyst**.

You receive:
- The **combined specification** from the previous pipeline steps (item_no,
  mechanical_cleaning_hot, mechanical_cleaning_cold, min_pressure, max_pressure, pressure_unit,
  min_temperature, max_temperature, temperature_unit, matching heat exchangers).
- The **markdown content** of a heat exchanger calculation / estimation
  document (e.g. a thermal design calculation sheet).

Your task:
1. Extract all key **technical parameters** from the calculation document:
   design pressures (shell & tube side), design temperatures (shell & tube
   side), heat transfer area, tube dimensions (OD, wall thickness, length,
   number of tubes), shell diameter, baffle spacing, TEMA type, material
   specifications, fouling resistances, overall heat transfer coefficient,
   heat duty, and flow rates.
2. Cross-reference the extracted calculation values with the combined
   specification to verify compliance:
   - Are the **design pressures** within the specified min/max range?
   - Are the **design temperatures** within the specified min/max range?
   - Does the **mechanical cleaning** requirement match (e.g. removable
     bundle, adequate tube pitch for cleaning)?
3. Highlight any **discrepancies** or concerns (e.g. pressure rating
   exceeded, temperature out of range, insufficient cleaning access,
   material incompatibility).
4. Provide a structured technical summary.

You MUST respond with **only** a valid JSON object – no markdown fences, no
commentary, no extra text.  The JSON schema is:

{
  "calculation_summary": {
    "tema_type": "<string or null>",
    "heat_duty_kw": <number or null>,
    "heat_transfer_area_m2": <number or null>,
    "overall_u_w_m2k": <number or null>,
    "shell_side": {
      "design_pressure": <number or null>,
      "design_temperature": <number or null>,
      "pressure_unit": "<string or null>",
      "temperature_unit": "<string or null>",
      "fluid": "<string or null>",
      "flow_rate": <number or null>,
      "flow_rate_unit": "<string or null>"
    },
    "tube_side": {
      "design_pressure": <number or null>,
      "design_temperature": <number or null>,
      "pressure_unit": "<string or null>",
      "temperature_unit": "<string or null>",
      "fluid": "<string or null>",
      "flow_rate": <number or null>,
      "flow_rate_unit": "<string or null>"
    },
    "tube_od_mm": <number or null>,
    "tube_wall_mm": <number or null>,
    "tube_length_mm": <number or null>,
    "number_of_tubes": <number or null>,
    "shell_diameter_mm": <number or null>,
    "baffle_spacing_mm": <number or null>,
    "tube_material": "<string or null>",
    "shell_material": "<string or null>",
    "notes": "<string or null>"
  },
  "specification_match": {
    "pressure_ok": true or false or null,
    "temperature_ok": true or false or null,
    "mechanical_cleaning_ok": true or false or null,
    "discrepancies": ["<string>", ...]
  }
}

If you cannot determine a field, use null for its value.
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

        # ── Step 3: Merge results directly ────────────────────────────
        combined: dict[str, Any] = {
            "status": "complete",
            "item_no": design_json.get("item_no") or other_json.get("item_no"),
            "medical_cleaning": design_json.get("medical_cleaning"),
            "min_pressure": other_json.get("min_pressure"),
            "max_pressure": other_json.get("max_pressure"),
            "pressure_unit": other_json.get("pressure_unit"),
            "min_temperature": other_json.get("min_temperature"),
            "max_temperature": other_json.get("max_temperature"),
            "temperature_unit": other_json.get("temperature_unit"),
        }
        # Mark partial when either agent returned nothing useful
        if not design_json.get("item_no") or not other_json.get("item_no"):
            combined["status"] = "partial"

        result["selection"] = json.dumps(combined, indent=2)
        print(f"  ✓ Combined result: {combined}")

        result["messages"].append({
            "author": "CombinedResult",
            "role": "assistant",
            "text": result["selection"],
        })

        # ── Step 4: SelectionAgent – search for heat exchangers ──────
        tools_list: list[dict] = []

        sharepoint_tool = _build_sharepoint_tool()
        if sharepoint_tool is not None:
            tools_list.append(sharepoint_tool)
            print("  ✓ SharePoint grounding tool attached to SelectionAgent")

        if not tools_list:
            print("ℹ️  No tools configured – skipping SelectionAgent")
        else:
            create_kwargs: dict[str, Any] = {
                "model": model_deployment,
                "name": "SelectionAgent",
                "instructions": _SELECTION_AGENT_INSTRUCTIONS,
                "tools": tools_list,
            }

            selection_agent = await provider.create_agent(**create_kwargs)
            print(f"  ✓ SelectionAgent created: {selection_agent.id}")

            selection_resp = await selection_agent.run(
                f"Combined specification:\n```json\n"
                f"{json.dumps(combined, indent=2)}\n```\n\n"
                f"Which heat exchangers are available that fit these values? "
                f"Search for heat exchangers matching the pressure range, "
                f"temperature range, and medical cleaning requirement above."
            )
            selection_text = selection_resp.text or ""
            selection_json = _extract_json(selection_text)

            # Merge search results into combined output
            if selection_json.get("matching_heat_exchangers"):
                combined["matching_heat_exchangers"] = selection_json[
                    "matching_heat_exchangers"
                ]
                result["selection"] = json.dumps(combined, indent=2)

            print(f"  ✓ SelectionAgent result: {selection_json}")

            result["messages"].append({
                "author": "SelectionAgent",
                "role": "assistant",
                "text": json.dumps(selection_json, indent=2),
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


# ---------------------------------------------------------------------------
# Estimation Agent – analyses an uploaded estimation document
# ---------------------------------------------------------------------------

async def _run_estimation_analysis_async(
    estimation_content: str,
    processing_context: str,
) -> dict:
    """Run the EstimationAgent on an uploaded estimation document."""
    project_endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT", "")
    model_deployment = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-4.1")

    result: dict[str, Any] = {
        "success": True,
        "estimation_analysis": "",
        "error": None,
    }

    async with (
        AzureCliCredential(process_timeout=30) as credential,
        AzureAIProjectAgentProvider(
            credential=credential,
            project_endpoint=project_endpoint,
        ) as provider,
    ):
        estimation_agent = await provider.create_agent(
            model=model_deployment,
            name="EstimationAgent",
            instructions=_ESTIMATION_AGENT_INSTRUCTIONS,
        )
        print(f"  ✓ EstimationAgent created: {estimation_agent.id}")

        prompt = (
            f"## Combined specification from previous steps\n"
            f"```\n{processing_context}\n```\n\n"
            f"## Estimation document content\n\n{estimation_content}"
        )

        resp = await estimation_agent.run(prompt)
        resp_text = resp.text or ""
        resp_json = _extract_json(resp_text)
        result["estimation_analysis"] = json.dumps(resp_json, indent=2)
        print(f"  ✓ EstimationAgent result: {resp_json}")

    return result


def run_estimation_analysis(
    estimation_content: str,
    processing_context: str,
) -> dict:
    """Run EstimationAgent – safe to call from synchronous Streamlit code.

    Returns dict with keys: ``success``, ``estimation_analysis``, ``error``.
    """
    if not _AGENT_FRAMEWORK_AVAILABLE:
        return {
            "success": False,
            "estimation_analysis": "",
            "error": f"agent-framework is not installed ({_import_error})",
        }

    try:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(
                    asyncio.run,
                    _run_estimation_analysis_async(
                        estimation_content, processing_context
                    ),
                )
                return future.result(timeout=120)
        else:
            return asyncio.run(
                _run_estimation_analysis_async(
                    estimation_content, processing_context
                )
            )

    except Exception as exc:
        return {"success": False, "estimation_analysis": "", "error": str(exc)}


# ---------------------------------------------------------------------------
# Senior Agent – handles follow-up chat questions
# ---------------------------------------------------------------------------

_SENIOR_AGENT_INSTRUCTIONS = """\
You are a **Senior Heat Exchanger Specialist** with deep expertise in heat
exchanger selection, specifications, standards, and applications.

You have access to tools to search for information:
• **SharePoint** – search SharePoint sites for catalogues, data sheets,
  product lists, and technical documentation about heat exchangers.

When answering questions:
1. Use the available search tools to find relevant documents and data.
2. Provide detailed, accurate answers grounded in the retrieved information.
3. Cite your sources when referencing specific documents using
   `[ref_idx†source]` notation.
4. If processing results from the document analysis pipeline are provided
   as context, leverage them to give more targeted and precise answers.
5. If you cannot find the answer in the available sources, say so clearly
   rather than guessing.

Be helpful, precise, and thorough.  Respond in well-formatted **Markdown**.
"""


async def _run_chat_query_async(
    user_message: str,
    processing_context: str | None = None,
    chat_history: list[dict] | None = None,
) -> dict:
    """Run a single turn of the SeniorAgent to answer a user question."""
    project_endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT", "")
    model_deployment = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-4.1")

    result: dict[str, Any] = {"success": True, "reply": "", "error": None}

    async with (
        AzureCliCredential(process_timeout=30) as credential,
        AzureAIProjectAgentProvider(
            credential=credential,
            project_endpoint=project_endpoint,
        ) as provider,
    ):
        # Collect tools
        tools_list: list[dict] = []

        sharepoint_tool = _build_sharepoint_tool()
        if sharepoint_tool is not None:
            tools_list.append(sharepoint_tool)
            print("  ✓ SharePoint grounding tool attached to SeniorAgent")

        create_kwargs: dict[str, Any] = {
            "model": model_deployment,
            "name": "SeniorAgent",
            "instructions": _SENIOR_AGENT_INSTRUCTIONS,
        }
        if tools_list:
            create_kwargs["tools"] = tools_list

        senior_agent = await provider.create_agent(**create_kwargs)
        print(f"  ✓ SeniorAgent created: {senior_agent.id}")

        # Build prompt with optional history and processing context
        parts: list[str] = []

        if chat_history:
            parts.append("## Previous conversation\n")
            for msg in chat_history[-20:]:  # limit context window
                role = msg.get("role", "user")
                content = msg.get("content", "")
                parts.append(f"**{role}**: {content}\n")
            parts.append("---\n")

        if processing_context:
            parts.append(
                "## Document processing results (from analysis pipeline)\n"
                f"```\n{processing_context}\n```\n\n"
            )

        parts.append(f"## User question\n{user_message}")

        prompt = "\n".join(parts)

        response = await senior_agent.run(prompt)
        result["reply"] = response.text or "No response from SeniorAgent."
        print(f"  ✓ SeniorAgent replied ({len(result['reply'])} chars)")

    return result


def run_chat_query(
    user_message: str,
    processing_context: str | None = None,
    chat_history: list[dict] | None = None,
) -> dict:
    """Run a SeniorAgent query – safe to call from synchronous Streamlit code.

    Returns dict with keys: ``success``, ``reply``, ``error``.
    """
    if not _AGENT_FRAMEWORK_AVAILABLE:
        return {
            "success": False,
            "reply": "",
            "error": f"agent-framework is not installed ({_import_error})",
        }

    try:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(
                    asyncio.run,
                    _run_chat_query_async(
                        user_message, processing_context, chat_history
                    ),
                )
                return future.result(timeout=120)
        else:
            return asyncio.run(
                _run_chat_query_async(
                    user_message, processing_context, chat_history
                )
            )

    except Exception as exc:
        return {"success": False, "reply": "", "error": str(exc)}
