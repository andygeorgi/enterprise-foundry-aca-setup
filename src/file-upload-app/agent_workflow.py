#!/usr/bin/env python3
"""
Agent Workflow – Sequential document analysis pipeline (Foundry v2)
===================================================================

Uses Microsoft **agent-framework** with ``AzureAIProjectAgentProvider`` and
``SequentialBuilder`` to build a two-agent sequential workflow hosted inside
an Azure AI Foundry project:

1. **DocumentAnalyst** – analyses extracted document content, produces a
   Markdown table of key fields.
2. **Summarizer** – receives the analyst output and writes a brief
   2-3 sentence description.

Reference:
  https://github.com/microsoft/agent-framework/blob/main/python/samples/
  getting_started/workflows/agents/sequential_workflow_as_agent.py

Environment variables (add to ``.env``):
  AZURE_AI_PROJECT_ENDPOINT          – Foundry project endpoint
  AZURE_AI_MODEL_DEPLOYMENT_NAME     – Deployed model name (e.g. gpt-4.1)
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
    from agent_framework import SequentialBuilder
    from agent_framework.azure import AzureAIProjectAgentProvider
    from azure.identity.aio import DefaultAzureCredential

    _AGENT_FRAMEWORK_AVAILABLE = True
except ImportError as exc:
    _import_error = str(exc)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def format_analysis_for_agent(analysis: dict) -> str:
    """Convert a Document Intelligence analysis JSON into agent-friendly text."""
    parts: list[str] = []

    if analysis.get("content"):
        parts.append(f"## Extracted Text\n{analysis['content']}")

    if analysis.get("key_value_pairs"):
        kv_lines = []
        for kv in analysis["key_value_pairs"]:
            key = kv.get("key", "?")
            val = kv.get("value", "?")
            conf = kv.get("confidence", 0)
            kv_lines.append(f"- **{key}**: {val}  (confidence {conf:.0%})")
        if kv_lines:
            parts.append("## Key-Value Pairs\n" + "\n".join(kv_lines))

    if analysis.get("tables"):
        for idx, table in enumerate(analysis["tables"], 1):
            rows = table.get("row_count", "?")
            cols = table.get("column_count", "?")
            header = f"## Table {idx} ({rows} rows × {cols} columns)"
            cells = table.get("cells", [])
            cell_lines = [
                f"  [{c.get('row_index')},{c.get('column_index')}] {c.get('content', '')}"
                for c in cells[:60]
            ]
            parts.append(header + "\n" + "\n".join(cell_lines))

    if analysis.get("pages"):
        page_summary = ", ".join(
            f"Page {p.get('page_number', '?')} ({p.get('lines_count', 0)} lines, "
            f"{p.get('words_count', 0)} words)"
            for p in analysis["pages"]
        )
        parts.append(f"## Pages\n{page_summary}")

    return "\n\n".join(parts) if parts else "(empty document)"


def is_agent_available() -> bool:
    """Return True when agent-framework is installed and Foundry project is configured."""
    if not _AGENT_FRAMEWORK_AVAILABLE:
        return False
    return bool(os.getenv("AZURE_AI_PROJECT_ENDPOINT"))


# ---------------------------------------------------------------------------
# Agent instructions
# ---------------------------------------------------------------------------

_ANALYST_INSTRUCTIONS = (
    "You are an expert document analyst. You receive extracted content "
    "from an uploaded document (text, tables, key-value pairs).\n\n"
    "Your task:\n"
    "1. Identify the document type (invoice, receipt, contract, letter, "
    "report, form, etc.).\n"
    "2. Extract the most important fields and their values.\n"
    "3. Present your findings as a **Markdown table** with columns:\n"
    "   | Field | Value | Notes |\n"
    "4. Add a one-line heading above the table stating the document type.\n\n"
    "Be concise, structured, and accurate. Always output a Markdown table."
)

_SUMMARIZER_INSTRUCTIONS = (
    "You are a brief summarizer. You receive the structured analysis "
    "produced by a document analyst (the previous assistant message).\n\n"
    "Write a SHORT 2–3 sentence summary:\n"
    "• What type of document was analysed\n"
    "• How many key fields were found\n"
    "• One notable or interesting finding\n\n"
    "Keep it conversational and friendly. Start with an emoji."
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def _run_analysis_async(prompt: str) -> dict:
    """
    Create two Foundry agents via AzureAIProjectAgentProvider, wire them
    into a SequentialBuilder workflow, and run the prompt through it.

    Uses async context managers exactly like the sample agent.
    """
    project_endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT", "")
    model_deployment = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-4.1")

    result: dict[str, Any] = {
        "success": True,
        "analyst": "",
        "summarizer": "",
        "messages": [],
    }

    async with (
        DefaultAzureCredential() as credential,
        AzureAIProjectAgentProvider(
            credential=credential,
            project_endpoint=project_endpoint,
        ) as provider,
    ):
        # --- Agent 1: Document Analyst (Foundry-hosted) --------------------
        analyst = await provider.create_agent(
            model=model_deployment,
            name="DocumentAnalyst",
            instructions=_ANALYST_INSTRUCTIONS,
        )
        print(f"  ✓ DocumentAnalyst created: {analyst.id}")

        # --- Agent 2: Summarizer (Foundry-hosted, light-touch) -------------
        summarizer = await provider.create_agent(
            model=model_deployment,
            name="Summarizer",
            instructions=_SUMMARIZER_INSTRUCTIONS,
        )
        print(f"  ✓ Summarizer created: {summarizer.id}")

        # --- Sequential workflow: analyst → summarizer ---------------------
        workflow = (
            SequentialBuilder()
            .participants([analyst, summarizer])
            .build()
        )

        # Run the workflow — returns WorkflowRunResult (a list of events)
        events = await workflow.run(prompt)

        # Extract per-agent outputs from AgentRunEvent items
        from agent_framework import AgentRunEvent

        agent_outputs: list[tuple[str, str]] = []  # (agent_name, text)
        print(f"  [Workflow] Got {len(events)} event(s):")
        for event in events:
            etype = type(event).__name__
            # AgentRunEvent.data is an AgentResponse with .text
            if isinstance(event, AgentRunEvent):
                agent_name = getattr(event, 'name', '') or ''
                resp = event.data
                text = resp.text if resp else ''
                print(
                    f"    - AgentRunEvent  name={agent_name!r}  text={text[:150]!r}")
                agent_outputs.append((agent_name, text or ''))
                result["messages"].append({
                    "author": agent_name,
                    "role": "assistant",
                    "text": text or '',
                })
            else:
                print(f"    - {etype}")

        # Assign outputs: first AgentRunEvent = analyst, second = summarizer
        if len(agent_outputs) >= 2:
            result["analyst"] = agent_outputs[0][1]
            result["summarizer"] = agent_outputs[1][1]
        elif len(agent_outputs) == 1:
            result["analyst"] = agent_outputs[0][1]

        # Also try get_outputs() as an alternative
        if not result["analyst"]:
            outputs = events.get_outputs()
            print(
                f"  [Workflow] get_outputs() returned {len(outputs)} item(s)")
            for i, out in enumerate(outputs):
                text = getattr(out, 'text', str(out)) if out else ''
                print(
                    f"    output[{i}]: type={type(out).__name__}  text={str(text)[:150]!r}")
                if i == 0:
                    result["analyst"] = str(text)
                elif i == 1:
                    result["summarizer"] = str(text)

        if not result["analyst"] and not result["summarizer"]:
            print("  [Workflow] WARNING: No output captured at all")

    return result


def run_document_analysis(document_content: str) -> dict:
    """
    Run the two-agent sequential workflow on *document_content*.

    Safe to call from synchronous Streamlit code – handles nested event loops.

    Returns
    -------
    dict  with keys ``success``, ``analyst``, ``summarizer``, ``messages``,
          and optionally ``error``.
    """
    if not _AGENT_FRAMEWORK_AVAILABLE:
        return {
            "success": False,
            "error": f"agent-framework is not installed ({_import_error})",
            "analyst": "",
            "summarizer": "",
            "messages": [],
        }

    prompt = (
        "Please analyse the following uploaded document content and create "
        "a structured analysis table:\n\n"
        f"---\n{document_content}\n---"
    )

    try:
        # Streamlit may already have a running event loop
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(asyncio.run, _run_analysis_async(prompt))
                return future.result(timeout=180)
        else:
            return asyncio.run(_run_analysis_async(prompt))

    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
            "analyst": "",
            "summarizer": "",
            "messages": [],
        }
