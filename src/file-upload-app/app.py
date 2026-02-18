#!/usr/bin/env python3
"""
File Upload App – Streamlit front-end
======================================
Tabbed full-width layout:
  • Tab 1 – File upload with Azure Document Intelligence analysis
  • Tab 2 – Chat interface with multi-agent orchestrator

All heavy lifting (Azure Doc Intelligence, file persistence) is delegated to
``upload_backend.py``.
"""

import os
import threading
from datetime import datetime

import streamlit as st

# -- Backend imports ---------------------------------------------------------
from upload_backend import (
    ALLOWED_EXTENSIONS,
    UPLOAD_FOLDER,
    allowed_file,
    create_flask_app,
    list_uploaded_files,
    load_markdown,
    save_uploaded_bytes,
)

# -- Agent workflow imports --------------------------------------------------
from agent_workflow import (
    _AGENT_FRAMEWORK_AVAILABLE,
    _import_error,
    classify_file_by_content,
    get_design_markers,
    get_other_markers,
    is_agent_available,
    run_chat_query,
    run_document_analysis,
    run_estimation_analysis,
)

# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Enterprise Foundry – File Upload & Agent Chat",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Flask health-check API  (runs in a background thread so container probes
# still work – only the /health endpoint is needed)
# ---------------------------------------------------------------------------
def _start_flask_health_server():
    """Start a minimal Flask server in the background for /health probes.

    Streamlit re-executes the whole script on every interaction, so we
    use a file lock to ensure only one thread ever starts the server.
    """
    import socket
    import tempfile

    try:
        import fcntl
    except ImportError:
        fcntl = None  # type: ignore[assignment]

    health_port = int(os.environ.get("HEALTH_PORT", 8081))
    lock_path = os.path.join(tempfile.gettempdir(), f"flask_health_{health_port}.lock")

    if fcntl is not None:
        try:
            lock_fd = open(lock_path, "w")
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (IOError, OSError):
            # Another process/thread already holds the lock → server is running
            return
    else:
        # Windows: use a simple lock-file existence check
        import msvcrt
        try:
            lock_fd = open(lock_path, "w")
            msvcrt.locking(lock_fd.fileno(), msvcrt.LK_NBLCK, 1)
        except (IOError, OSError):
            return

    # Check if port is already in use (e.g. from a previous container run)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        if s.connect_ex(("127.0.0.1", health_port)) == 0:
            lock_fd.close()
            return

    flask_app = create_flask_app()

    def _run():
        try:
            from werkzeug.serving import make_server
            srv = make_server("0.0.0.0", health_port, flask_app)
            print(f"✓ Flask health-check sidecar listening on :{health_port}")
            srv.serve_forever()
        except Exception:
            pass  # silently ignore – port may have been grabbed in a race

    threading.Thread(target=_run, daemon=True).start()


_start_flask_health_server()

# ---------------------------------------------------------------------------
# Session-state defaults
# ---------------------------------------------------------------------------
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "upload_results" not in st.session_state:
    st.session_state.upload_results = []
if "last_analysis_content" not in st.session_state:
    st.session_state.last_analysis_content = None
if "selected_files" not in st.session_state:
    st.session_state.selected_files = []
if "classified_design_file" not in st.session_state:
    st.session_state.classified_design_file = None
if "classified_other_file" not in st.session_state:
    st.session_state.classified_other_file = None
if "documents_processed" not in st.session_state:
    st.session_state.documents_processed = False
if "processing_result" not in st.session_state:
    st.session_state.processing_result = None
if "estimation_uploaded" not in st.session_state:
    st.session_state.estimation_uploaded = False
if "estimation_result" not in st.session_state:
    st.session_state.estimation_result = None

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    /* tighter padding */
    .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }

    /* card-like sections */
    .upload-card, .chat-card {
        background: #f8f9fa;
        border-radius: 12px;
        padding: 1.2rem;
        margin-bottom: 1rem;
        border: 1px solid #e0e0e0;
    }
    .dark .upload-card, .dark .chat-card {
        background: #1e1e1e;
        border: 1px solid #333;
    }

    /* analysis result badges */
    .badge-ok  { color: #28a745; font-weight: 600; }
    .badge-err { color: #dc3545; font-weight: 600; }

    /* blinking green process button */
    @keyframes pulse-green {
        0%   { box-shadow: 0 0 4px #28a745; }
        50%  { box-shadow: 0 0 18px 4px #28a745; }
        100% { box-shadow: 0 0 4px #28a745; }
    }
    .blink-green button[kind="primary"] {
        animation: pulse-green 1.2s ease-in-out infinite;
        border: 2px solid #28a745 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Agent response helpers
# ---------------------------------------------------------------------------


def _split_agent_replies(result: dict) -> list[dict]:
    """Return a list of chat-message dicts, one per agent section.

    Each dict has ``role`` (always ``'assistant'``) and ``content``.
    This lets us render each agent as its own chat bubble.
    """
    msgs: list[dict] = []

    if result.get("design_analysis"):
        msgs.append({
            "role": "assistant",
            "content": (
                "**📐 DesignDocAgent** — extracted design fields\n\n"
                f"```json\n{result['design_analysis']}\n```"
            ),
        })
    if result.get("other_analysis"):
        msgs.append({
            "role": "assistant",
            "content": (
                "**📄 OtherDocAgent** — extracted specifications\n\n"
                f"```json\n{result['other_analysis']}\n```"
            ),
        })
    if result.get("selection"):
        msgs.append({
            "role": "assistant",
            "content": (
                "**🎯 SelectionAgent** — consolidated result\n\n"
                f"```json\n{result['selection']}\n```"
            ),
        })
    if result.get("estimation_analysis"):
        msgs.append({
            "role": "assistant",
            "content": (
                "**💰 EstimationAgent** — calculation analysis\n\n"
                f"```json\n{result['estimation_analysis']}\n```"
            ),
        })

    # Fallback: raw messages
    if not msgs and result.get("messages"):
        for msg in result["messages"]:
            text = msg.get("text", "")
            author = msg.get("author", "Agent")
            if text:
                msgs.append({
                    "role": "assistant",
                    "content": f"**🤖 {author}**\n\n{text}",
                })

    if not msgs:
        msgs.append({"role": "assistant", "content": "No analysis produced."})

    return msgs


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown(
    '<h4 style="margin:0 0 .25rem 0">🏗️ Enterprise Foundry — File Upload & Agent Chat</h4>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Tabbed layout (full width)
# ---------------------------------------------------------------------------
tab_upload, tab_chat = st.tabs(["📁 Upload & Analysis", "💬 Agent Chat"])

# ===========================  TAB 1 – FILE UPLOAD  =========================
with tab_upload:
    st.subheader("📁 File Upload & Analysis")

    # File uploader widget
    uploaded_files = st.file_uploader(
        "Drop files here or click to browse",
        type=list(ALLOWED_EXTENSIONS),
        accept_multiple_files=True,
        help=f"Max 16 MB per file. Supported: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
    )

    if uploaded_files:
        st.markdown(f"**{len(uploaded_files)}** file(s) selected")

        if st.button("⬆️ Upload & Analyse", type="primary", use_container_width=True):
            progress = st.progress(0, text="Uploading…")
            results = []
            for idx, uf in enumerate(uploaded_files):
                if not allowed_file(uf.name):
                    st.warning(
                        f"⚠️ Skipped **{uf.name}** – file type not allowed")
                    continue
                try:
                    result = save_uploaded_bytes(uf.read(), uf.name)
                    results.append(result)
                except Exception as exc:
                    st.error(f"❌ **{uf.name}**: {exc}")
                progress.progress(
                    (idx + 1) / len(uploaded_files),
                    text=f"Processing {idx + 1}/{len(uploaded_files)}…",
                )
            progress.empty()

            st.session_state.upload_results = results
            if results:
                st.success(f"✅ {len(results)} file(s) uploaded and analysed.")

    # -- Show most recent upload results ------------------------------------
    if st.session_state.upload_results:
        st.markdown("#### Latest Upload Results")
        for r in st.session_state.upload_results:
            with st.expander(f"📄 {r['original_filename']}  ({r['size']:,} bytes)", expanded=False):
                if r.get("processed"):
                    st.markdown(
                        '<span class="badge-ok">✅ Processed</span>',
                        unsafe_allow_html=True,
                    )
                    md_content = load_markdown(r.get("md_file", ""))
                    if md_content:
                        st.markdown(md_content)
                else:
                    st.markdown(
                        f'<span class="badge-err">❌ Not processed</span> — {r.get("error", "unknown")}',
                        unsafe_allow_html=True,
                    )

    # -- Previously uploaded files ------------------------------------------
    st.divider()
    st.markdown("#### 📋 Recent Files")
    existing_files = list_uploaded_files()
    if existing_files:
        for f in existing_files[:20]:
            label = f["filename"]
            size_kb = f["size"] / 1024
            status = "✅" if f["has_analysis"] else "—"
            with st.expander(f"{status} {label}  ({size_kb:.1f} KB)", expanded=False):
                st.text(f"Modified: {f['modified']}")
                if f["has_analysis"] and f["md_file"]:
                    md_content = load_markdown(f["md_file"])
                    if md_content:
                        st.markdown(md_content)
    else:
        st.info("No files uploaded yet.")


# ===========================  TAB 2 – CHAT  ================================
with tab_chat:
    # Agent status indicator
    if is_agent_available():
        st.caption(
            "🟢 Agent orchestrator active — routes to DocumentAnalyst / GeneralAssistant")
    else:
        if not _AGENT_FRAMEWORK_AVAILABLE:
            st.caption(
                f"⚪ Agent not available — agent-framework import failed: `{_import_error}`"
            )
        else:
            st.caption(
                "⚪ Agent not configured — using echo mode  ·  "
                "Set `AZURE_AI_PROJECT_ENDPOINT` in .env"
            )

    # -- File context selector (single multi-select) -----------------------
    existing_files = list_uploaded_files()
    analysed_files = [
        f for f in existing_files if f["has_analysis"] and f["md_file"]
    ]
    file_options = [f["filename"] for f in analysed_files]

    st.markdown("##### 📎 Attach files to process")
    st.caption(
        "Select files to attach. Each file's first page is scanned to "
        "determine whether it is a **design** doc or a **specs** doc.  "
        "Both types are required before the agent can run."
    )

    selected_files = st.multiselect(
        "📄 Select files",
        options=file_options,
        default=st.session_state.selected_files,
        key="file_multiselect",
        help="Pick one or more analysed files.",
    )
    st.session_state.selected_files = selected_files

    # -- Classify each selected file by first-page content -----------------
    def _load_file_content(fname: str | None) -> str | None:
        if not fname:
            return None
        md_name = fname + ".md"
        md_content = load_markdown(md_name)
        if md_content:
            return f"### File: {fname}\n{md_content}"
        return None

    classified_design: str | None = None
    classified_other: str | None = None
    classification_errors: list[str] = []
    classification_info: list[str] = []

    for fname in selected_files:
        md_content = load_markdown(fname + ".md") or ""
        file_type = classify_file_by_content(md_content)
        if file_type == "design":
            if classified_design is not None:
                classification_errors.append(
                    f"Multiple design files detected — only one is allowed. "
                    f"(**{classified_design}** and **{fname}**)"
                )
            else:
                classified_design = fname
                classification_info.append(f"📐 **Design doc:** {fname}")
        elif file_type == "other":
            if classified_other is not None:
                classification_errors.append(
                    f"Multiple specs files detected — only one is allowed. "
                    f"(**{classified_other}** and **{fname}**)"
                )
            else:
                classified_other = fname
                classification_info.append(f"📄 **Specs doc:** {fname}")
        else:
            design_markers = ", ".join(f'`{m}`' for m in get_design_markers())
            other_markers = ", ".join(f'`{m}`' for m in get_other_markers())
            classification_errors.append(
                f"**{fname}** — could not classify. First page must contain "
                f"one of: {design_markers} (design) or {other_markers} (specs)."
            )

    # Show classification results
    for info in classification_info:
        st.info(info)
    for err in classification_errors:
        st.error(f"❌ {err}")

    both_files_ready = (
        classified_design is not None
        and classified_other is not None
        and len(classification_errors) == 0
    )

    if selected_files and not both_files_ready and not classification_errors:
        missing = []
        if classified_design is None:
            missing.append("design")
        if classified_other is None:
            missing.append("specs")
        if missing:
            st.warning(
                f"⚠️ Still need a **{' and a '.join(missing)}** file. "
                "Select more files above."
            )

    # Persist into session state
    st.session_state.classified_design_file = classified_design
    st.session_state.classified_other_file = classified_other

    # -- Reset processed flag if selections change -------------------------
    prev_pair = st.session_state.get("_prev_file_pair")
    curr_pair = (classified_design, classified_other)
    if prev_pair != curr_pair:
        st.session_state.documents_processed = False
        st.session_state.estimation_uploaded = False
        st.session_state.estimation_result = None
    st.session_state._prev_file_pair = curr_pair

    design_content = _load_file_content(classified_design)
    other_content = _load_file_content(classified_other)

    # -- Process button (blinking green when both files ready) --------------
    if both_files_ready and not st.session_state.documents_processed:
        # Wrap in a div that triggers the blinking CSS
        st.markdown('<div class="blink-green">', unsafe_allow_html=True)
        if st.button(
            "🤖 Process uploaded files",
            type="primary",
            use_container_width=True,
        ):
            if is_agent_available() and design_content and other_content:
                with st.spinner("Running concurrent agent workflow…"):
                    result = run_document_analysis(design_content, other_content)
                if result["success"]:
                    # Store processing output for optional chat context
                    proc_parts = []
                    if result.get("design_analysis"):
                        proc_parts.append(f"Design Analysis:\n{result['design_analysis']}")
                    if result.get("other_analysis"):
                        proc_parts.append(f"Specifications Analysis:\n{result['other_analysis']}")
                    if result.get("selection"):
                        proc_parts.append(f"Combined Selection:\n{result['selection']}")
                    st.session_state.processing_result = "\n\n".join(proc_parts)

                    for agent_msg in _split_agent_replies(result):
                        st.session_state.chat_messages.append(agent_msg)
                    st.session_state.documents_processed = True
                    st.rerun()
                else:
                    st.error(f"Agent error: {result.get('error', 'Unknown')}")
            else:
                st.error(
                    "Agent orchestrator is not available. Check your "
                    "`AZURE_AI_PROJECT_ENDPOINT` configuration."
                )
        st.markdown('</div>', unsafe_allow_html=True)
    elif both_files_ready and st.session_state.documents_processed:
        st.success("✅ Documents processed.")
    elif is_agent_available():
        st.button(
            "🤖 Process uploaded files",
            use_container_width=True,
            disabled=True,
            help="Select files that classify as one design doc and one specs doc.",
        )

    # -- Chat history -------------------------------------------------------
    chat_container = st.container(height=500)
    with chat_container:
        for msg in st.session_state.chat_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # -- Estimation upload (inline in chat after last message) ----------
        if st.session_state.documents_processed and not st.session_state.estimation_uploaded:
            st.divider()
            st.markdown(
                "💰 **EstimationAgent** — Upload a heat exchanger calculation "
                "document to verify it against the extracted specifications."
            )
            estimation_file = st.file_uploader(
                "Upload calculation document",
                type=list(ALLOWED_EXTENSIONS),
                accept_multiple_files=False,
                key="estimation_uploader",
                help="Upload a thermal design calculation sheet for analysis.",
            )
            if estimation_file is not None:
                st.markdown('<div class="blink-green">', unsafe_allow_html=True)
                if st.button(
                    "💰 Analyse calculation",
                    type="primary",
                    use_container_width=True,
                    key="estimation_process_btn",
                ):
                    with st.spinner("Processing estimation document…"):
                        # 1. Save & extract via Document Intelligence
                        try:
                            est_result = save_uploaded_bytes(
                                estimation_file.read(), estimation_file.name
                            )
                        except Exception as exc:
                            st.error(f"❌ Upload failed: {exc}")
                            est_result = None

                        if est_result and est_result.get("processed"):
                            est_md = load_markdown(est_result.get("md_file", "")) or ""

                            # 2. Run EstimationAgent
                            est_analysis = run_estimation_analysis(
                                estimation_content=est_md,
                                processing_context=st.session_state.processing_result or "",
                            )

                            if est_analysis["success"]:
                                # Store in processing result
                                est_text = est_analysis["estimation_analysis"]
                                st.session_state.processing_result = (
                                    (st.session_state.processing_result or "")
                                    + f"\n\nEstimation Analysis:\n{est_text}"
                                )
                                st.session_state.estimation_result = est_text
                                st.session_state.estimation_uploaded = True

                                # Add to chat
                                st.session_state.chat_messages.append({
                                    "role": "assistant",
                                    "content": (
                                        "**💰 EstimationAgent** — calculation analysis\n\n"
                                        f"```json\n{est_text}\n```"
                                    ),
                                })
                                st.rerun()
                            else:
                                st.error(
                                    f"EstimationAgent error: "
                                    f"{est_analysis.get('error', 'Unknown')}"
                                )
                        elif est_result:
                            st.error(
                                f"Document extraction failed: "
                                f"{est_result.get('error', 'Unknown')}"
                            )
                st.markdown('</div>', unsafe_allow_html=True)

    # -- Chat options -------------------------------------------------------
    if st.session_state.processing_result:
        include_context = st.checkbox(
            "📎 Include processing results as context",
            value=True,
            help="Attach the document analysis output to your message "
                 "so the Senior Agent can reference it.",
        )
    else:
        include_context = False

    # -- Chat input ---------------------------------------------------------
    user_input = st.chat_input(
        "Ask the Senior Agent about heat exchangers…",
        key="chat_input",
        disabled=not is_agent_available(),
    )

    if user_input:
        st.session_state.chat_messages.append(
            {"role": "user", "content": user_input}
        )

        reply: str | None = None

        if is_agent_available():
            proc_context = (
                st.session_state.processing_result
                if include_context and st.session_state.processing_result
                else None
            )
            with st.spinner("🤖 Senior Agent is thinking…"):
                result = run_chat_query(
                    user_input,
                    processing_context=proc_context,
                    chat_history=st.session_state.chat_messages[:-1],
                )
            if result["success"]:
                st.session_state.chat_messages.append(
                    {"role": "assistant", "content": result["reply"]}
                )
                st.rerun()
            else:
                reply = f"❌ Agent error: {result.get('error', 'Unknown')}"
        else:
            reply = (
                "⚠️ The agent orchestrator is not configured.\n\n"
                "Set `AZURE_AI_PROJECT_ENDPOINT` and `AZURE_AI_MODEL_DEPLOYMENT_NAME` "
                "in your `.env` file to enable the multi-agent workflow."
            )

        if reply:
            st.session_state.chat_messages.append(
                {"role": "assistant", "content": reply}
            )
            st.rerun()


# ---------------------------------------------------------------------------
# Entrypoint (for running via `streamlit run app.py`)
# ---------------------------------------------------------------------------
# Streamlit executes the entire file top-to-bottom on each interaction,
# so no __main__ guard is needed for Streamlit itself.
# However, keep a guard for manual `python app.py` convenience:
if __name__ == "__main__":
    # When invoked directly, just print a hint
    print(
        "ℹ️  This app is powered by Streamlit.\n"
        "   Run it with:  streamlit run app.py --server.port 8080\n"
        "   Or use the Flask backend directly:  python upload_backend.py"
    )
