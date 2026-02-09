#!/usr/bin/env python3
"""
File Upload App – Streamlit front-end
======================================
Two-column layout:
  • LEFT  – File upload with Azure Document Intelligence analysis
  • RIGHT – Chat interface (dummy for now – will support multi-agent interaction)

All heavy lifting (Azure Doc Intelligence, file persistence) is delegated to
``upload_backend.py``.
"""

import json
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
    load_analysis,
    save_uploaded_bytes,
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
_flask_started = False


def _start_flask_health_server():
    """Start a minimal Flask server in the background for /health probes."""
    global _flask_started
    if _flask_started:
        return
    _flask_started = True
    flask_app = create_flask_app()
    health_port = int(os.environ.get("HEALTH_PORT", 8081))

    def _run():
        import socket
        try:
            # Check if port is already in use before attempting to bind
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                if s.connect_ex(("127.0.0.1", health_port)) == 0:
                    print(
                        f"⚠️  Health-check port {health_port} already in use – skipping Flask sidecar")
                    return
            from werkzeug.serving import make_server
            srv = make_server("0.0.0.0", health_port, flask_app)
            print(f"✓ Flask health-check sidecar listening on :{health_port}")
            srv.serve_forever()
        except Exception as exc:
            print(f"⚠️  Could not start Flask health-check sidecar: {exc}")

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()


_start_flask_health_server()

# ---------------------------------------------------------------------------
# Session-state defaults
# ---------------------------------------------------------------------------
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = [
        {
            "role": "assistant",
            "content": (
                "👋 Hello! I'm the **Enterprise Foundry Agent**.\n\n"
                "I can help you with document analysis, data extraction, and more. "
                "This chat will soon support multi-agent workflows.\n\n"
                "For now, feel free to type a message and I'll echo it back."
            ),
        }
    ]
if "upload_results" not in st.session_state:
    st.session_state.upload_results = []

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
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Dummy agent helpers (to be replaced with real multi-agent orchestrator)
# ---------------------------------------------------------------------------


def _generate_dummy_response(user_message: str) -> str:
    """
    Placeholder response generator.
    Replace this with a real multi-agent orchestration call.
    """
    lower = user_message.lower()

    if any(w in lower for w in ("hello", "hi", "hey", "greetings")):
        return "👋 Hi there! How can I help you today?"

    if "file" in lower or "upload" in lower or "document" in lower:
        n = len(list_uploaded_files())
        return (
            f"📂 You currently have **{n}** file(s) uploaded.\n\n"
            "Use the panel on the left to upload and analyse new documents. "
            "Once multi-agent support lands, I'll be able to run deeper analysis pipelines for you."
        )

    if "help" in lower:
        return (
            "🛠️ Here's what I can help with (soon):\n"
            "- **Document analysis** – extract text, tables, key-value pairs\n"
            "- **Multi-agent workflows** – orchestrate specialised agents\n"
            "- **Data queries** – ask questions about uploaded documents\n\n"
            "For now, upload files on the left and I'll echo your messages here."
        )

    if "status" in lower or "health" in lower:
        return "✅ All systems operational. The upload backend is running."

    # Default echo
    return (
        f"🤖 *Echo:* {user_message}\n\n"
        "_(This is a placeholder response. Multi-agent interaction will be wired in soon.)_"
    )


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown("## 🏗️ Enterprise Foundry — File Upload & Agent Chat")
st.caption(
    "Upload documents for AI analysis  ·  Chat with agents (multi-agent support coming soon)")
st.divider()

# ---------------------------------------------------------------------------
# Two-column layout
# ---------------------------------------------------------------------------
col_upload, col_chat = st.columns([1, 1], gap="large")

# ===========================  LEFT COLUMN – FILE UPLOAD  ===================
with col_upload:
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
                        f'<span class="badge-ok">✅ Processed</span> — '
                        f'{r.get("pages", 0)} pages · '
                        f'{r.get("tables", 0)} tables · '
                        f'{r.get("key_value_pairs", 0)} key-value pairs',
                        unsafe_allow_html=True,
                    )
                    # Show analysis JSON
                    analysis = load_analysis(r["json_file"])
                    if analysis:
                        if analysis.get("content"):
                            st.text_area(
                                "Extracted text",
                                analysis["content"],
                                height=200,
                                disabled=True,
                                key=f"txt_{r['filename']}",
                            )
                        with st.popover("🔍 Full JSON"):
                            st.json(analysis)
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
                if f["has_analysis"] and f["json_file"]:
                    analysis = load_analysis(f["json_file"])
                    if analysis:
                        st.json(analysis)
    else:
        st.info("No files uploaded yet.")


# ===========================  RIGHT COLUMN – CHAT  =========================
with col_chat:
    st.subheader("💬 Agent Chat")
    st.caption("Multi-agent interaction · coming soon")

    # -- Chat history -------------------------------------------------------
    chat_container = st.container(height=520)
    with chat_container:
        for msg in st.session_state.chat_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # -- Chat input ---------------------------------------------------------
    user_input = st.chat_input("Type a message…", key="chat_input")

    if user_input:
        # Store user message
        st.session_state.chat_messages.append(
            {"role": "user", "content": user_input})

        # ---- Dummy agent response (placeholder for multi-agent workflow) ---
        dummy_reply = _generate_dummy_response(user_input)
        st.session_state.chat_messages.append(
            {"role": "assistant", "content": dummy_reply})

        # Rerun to render the new messages
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
