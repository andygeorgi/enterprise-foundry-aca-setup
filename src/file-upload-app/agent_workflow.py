#!/usr/bin/env python3
"""
Agent Workflow – Orchestrator with agents-as-tools (Foundry v2)
===============================================================

Uses Microsoft **agent-framework** with ``AzureAIProjectAgentProvider``.
An **Orchestrator** agent decides which specialist to invoke based on input:

- **DocumentAnalyst** (tool) – analyses attached document content, produces
  a structured Markdown table of key fields.
- **GeneralAssistant** (tool) – answers general questions, follow-ups, or
  conversational queries about the documents or anything else.

The specialist agents are wrapped via ``agent.as_tool()`` and registered as
tools on the orchestrator, which routes requests via normal tool-calling.

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

_ORCHESTRATOR_INSTRUCTIONS = (
    "You are an intelligent orchestrator. Your job is to route the user's "
    "request to the right specialist tool and return their output.\n\n"
    "Rules:\n"
    "1. If the user's message contains document content (extracted text, "
    "tables, key-value pairs, or mentions attached files), call the "
    "**analyse_document** tool with the full content.\n"
    "2. For general questions, follow-up questions about previous analysis, "
    "or any other request, call the **general_assistant** tool.\n"
    "3. You may call both tools if the request needs document analysis AND "
    "a follow-up answer.\n"
    "4. Always return the tool output to the user as-is – do NOT "
    "re-summarize or rewrite it unless the user explicitly asks.\n"
    "5. If no tools are needed for a trivial greeting, respond directly."
)

_DOCUMENT_ANALYST_INSTRUCTIONS = (
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

_GENERAL_ASSISTANT_INSTRUCTIONS = (
    "You are a helpful general assistant. You answer questions about "
    "previously analysed documents, provide summaries, comparisons, and "
    "insights when asked.\n\n"
    "If the user asks about document content you've seen before, draw on "
    "that context. If the user asks something unrelated, answer helpfully "
    "and concisely. Keep responses friendly and to the point."
)

_GENERAL_ASSISTANT_INSTRUCTIONS_SHAREPOINT = (
    "You are a helpful general assistant. You answer questions about "
    "previously analysed documents, provide summaries, comparisons, and "
    "insights when asked.\n\n"
    "You also have access to SharePoint via the sharepoint_grounding_preview "
    "tool. Whenever the user mentions travel questions, company policies, "
    "or asks for information that may be stored in SharePoint, call the "
    "sharepoint_grounding_preview tool to retrieve relevant information "
    "from the connected SharePoint sites.\n\n"
    "If the user asks about document content you've seen before, draw on "
    "that context. If the user asks something unrelated, answer helpfully "
    "and concisely. Keep responses friendly and to the point."
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def _run_analysis_async(prompt: str) -> dict:
    """
    Create an orchestrator agent with two specialist agents as tools,
    then run the prompt through the orchestrator.

    The orchestrator uses tool-calling to route to:
      - DocumentAnalyst  (analyse_document tool)
      - GeneralAssistant (general_assistant tool)
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
        # --- Specialist 1: Document Analyst --------------------------------
        document_agent = await provider.create_agent(
            model=model_deployment,
            name="DocumentAnalyst",
            instructions=_DOCUMENT_ANALYST_INSTRUCTIONS,
        )
        print(f"  ✓ DocumentAnalyst created: {document_agent.id}")

        # --- Specialist 2: General Assistant -------------------------------
        sharepoint_connection_id = os.getenv(
            "SHAREPOINT_PROJECT_CONNECTION_ID")
        general_tools: list = []
        general_instructions = _GENERAL_ASSISTANT_INSTRUCTIONS

        if sharepoint_connection_id:
            general_tools.append(
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
            general_instructions = _GENERAL_ASSISTANT_INSTRUCTIONS_SHAREPOINT
            print(
                f"  ✓ SharePoint grounding tool configured (connection: {sharepoint_connection_id[:20]}…)")

        general_agent = await provider.create_agent(
            model=model_deployment,
            name="GeneralAssistant",
            instructions=general_instructions,
            tools=general_tools if general_tools else None,
        )
        print(f"  ✓ GeneralAssistant created: {general_agent.id}")

        # --- Wrap specialists as tools for the orchestrator ----------------
        document_tool = document_agent.as_tool(
            name="analyse_document",
            description=(
                "Analyse document content (extracted text, tables, "
                "key-value pairs) and produce a structured Markdown table "
                "of key fields. Call this when the user provides or "
                "references attached document content."
            ),
            arg_name="document_content",
            arg_description="The extracted document text and metadata to analyse.",
        )

        general_tool = general_agent.as_tool(
            name="general_assistant",
            description=(
                "Answer general questions, follow-up questions about "
                "previously analysed documents, provide summaries, "
                "comparisons, or handle any non-document-analysis request."
            ),
            arg_name="question",
            arg_description="The user's question or request.",
        )

        # --- Orchestrator agent with tools ---------------------------------
        orchestrator = await provider.create_agent(
            model=model_deployment,
            name="Orchestrator",
            instructions=_ORCHESTRATOR_INSTRUCTIONS,
            tools=[document_tool, general_tool],
        )
        print(f"  ✓ Orchestrator created: {orchestrator.id}")

        # --- Run the orchestrator ------------------------------------------
        response = await orchestrator.run(prompt)
        orchestrator_text = response.text or ""

        print(f"  [Orchestrator] response text ({len(orchestrator_text)} chars): "
              f"{orchestrator_text[:200]!r}")

        result["messages"].append({
            "author": "Orchestrator",
            "role": "assistant",
            "text": orchestrator_text,
        })

        # Try to identify which tool(s) were called from the response
        # The orchestrator returns the combined output
        if orchestrator_text:
            # Heuristic: if output contains a markdown table, the analyst ran
            if "|" in orchestrator_text and "Field" in orchestrator_text:
                result["analyst"] = orchestrator_text
            else:
                result["summarizer"] = orchestrator_text

    return result


def run_document_analysis(document_content: str) -> dict:
    """
    Run the orchestrator agent on *document_content*.

    The orchestrator decides which specialist tool to invoke
    (DocumentAnalyst for document content, GeneralAssistant for questions).

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
