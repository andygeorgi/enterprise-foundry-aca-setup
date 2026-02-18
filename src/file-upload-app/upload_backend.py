#!/usr/bin/env python3
"""
Upload Backend – Flask API serving file upload and Azure Document Intelligence analysis.

This module contains all the original Flask routes and document processing logic,
extracted from app.py so that the Streamlit front-end can call it as a REST backend.
"""

from flask import Flask, request, jsonify, render_template, send_from_directory
import os
import json
from datetime import datetime
from pathlib import Path
from werkzeug.utils import secure_filename
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest, DocumentContentFormat
from azure.identity import AzureCliCredential
from dotenv import load_dotenv

# Load .env from the same directory as this file (src/file-upload-app/.env)
_env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(_env_path)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "/app/uploads")
MAX_CONTENT_LENGTH = int(os.environ.get(
    "MAX_CONTENT_LENGTH", 16 * 1024 * 1024))
ALLOWED_EXTENSIONS = {
    "txt", "pdf", "png", "jpg", "jpeg",
    "gif", "doc", "docx", "zip", "csv", "json", "xml",
}

DOCINTEL_ENDPOINT = os.environ.get("AZURE_DOCINTEL_ENDPOINT", "")

# ---------------------------------------------------------------------------
# Azure Document Intelligence client (singleton)
# ---------------------------------------------------------------------------
doc_intel_client: DocumentIntelligenceClient | None = None


def _init_docintel_client():
    """Initialise the Document Intelligence client once."""
    global doc_intel_client
    if doc_intel_client is not None:
        return

    if not DOCINTEL_ENDPOINT:
        print("⚠️  Warning: AZURE_DOCINTEL_ENDPOINT not set – files will be uploaded but not processed")
        return

    try:
        # Using AzureCliCredential for local development.
        # Switch back to DefaultAzureCredential for deployed environments.
        credential = AzureCliCredential()
        doc_intel_client = DocumentIntelligenceClient(
            endpoint=DOCINTEL_ENDPOINT, credential=credential
        )
        print("✓ Document Intelligence client initialised with AzureCliCredential")
    except Exception as e:
        print(
            f"⚠️  Warning: Could not initialise Document Intelligence client: {e}")
        print("   Files will be uploaded but not processed")


_init_docintel_client()
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def process_document_with_ai(filepath: str) -> tuple[str | None, str | None]:
    """
    Process a document with Azure Document Intelligence (prebuilt-layout,
    markdown output).

    Returns (markdown_content, error).  Exactly one will be non-None.
    """
    if not doc_intel_client:
        return None, "Document Intelligence not configured"

    try:
        file_ext = filepath.rsplit(".", 1)[1].lower() if "." in filepath else ""
        processable_types = {"pdf", "png", "jpg", "jpeg", "tiff", "bmp"}

        if file_ext not in processable_types:
            return None, f"File type .{file_ext} not supported for document analysis"

        with open(filepath, "rb") as f:
            file_bytes = f.read()

        import base64
        b64_content = base64.b64encode(file_bytes).decode("utf-8")

        poller = doc_intel_client.begin_analyze_document(
            "prebuilt-layout",
            AnalyzeDocumentRequest(bytes_source=b64_content),
            output_content_format=DocumentContentFormat.MARKDOWN,
        )
        result = poller.result()
        return result.content or "", None

    except Exception as e:
        return None, f"Document analysis failed: {e}"


def save_uploaded_file(uploaded_file_storage) -> dict:
    """
    Accept a werkzeug ``FileStorage`` object (from Flask's ``request.files``),
    persist it to disk, run layout analysis, and return a result dict.
    """
    filename = secure_filename(uploaded_file_storage.filename)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_filename = f"{timestamp}_{filename}"
    filepath = os.path.join(UPLOAD_FOLDER, unique_filename)

    uploaded_file_storage.save(filepath)
    file_size = os.path.getsize(filepath)
    print(f"✓ Uploaded: {unique_filename} ({file_size} bytes)")

    md_content, error = process_document_with_ai(filepath)

    file_result = {
        "filename": unique_filename,
        "original_filename": filename,
        "size": file_size,
        "processed": md_content is not None,
    }

    if md_content is not None:
        md_filepath = filepath + ".md"
        with open(md_filepath, "w", encoding="utf-8") as mf:
            mf.write(md_content)
        file_result["md_file"] = os.path.basename(md_filepath)
        print(f"  → Markdown saved: {file_result['md_file']} ({len(md_content)} chars)")
    else:
        file_result["error"] = error or "Unknown error"
        print(f"  ⚠️  Not processed: {file_result['error']}")

    return file_result


def save_uploaded_bytes(file_bytes: bytes, original_filename: str) -> dict:
    """
    Accept raw bytes + filename (e.g. from Streamlit's ``st.file_uploader``),
    persist to disk, run layout analysis, and return a result dict.
    """
    filename = secure_filename(original_filename)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_filename = f"{timestamp}_{filename}"
    filepath = os.path.join(UPLOAD_FOLDER, unique_filename)

    with open(filepath, "wb") as f:
        f.write(file_bytes)

    file_size = os.path.getsize(filepath)
    print(f"✓ Uploaded: {unique_filename} ({file_size} bytes)")

    md_content, error = process_document_with_ai(filepath)

    file_result = {
        "filename": unique_filename,
        "original_filename": filename,
        "size": file_size,
        "processed": md_content is not None,
    }

    if md_content is not None:
        md_filepath = filepath + ".md"
        with open(md_filepath, "w", encoding="utf-8") as mf:
            mf.write(md_content)
        file_result["md_file"] = os.path.basename(md_filepath)
        print(f"  → Markdown saved: {file_result['md_file']} ({len(md_content)} chars)")
    else:
        file_result["error"] = error or "Unknown error"

    return file_result


def list_uploaded_files() -> list[dict]:
    """Return a list of dicts describing every uploaded file."""
    files: list[dict] = []
    for filename in os.listdir(UPLOAD_FOLDER):
        # Skip sidecar files
        if filename.endswith(".md") or filename.endswith(".analysis.json"):
            continue
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        if not os.path.isfile(filepath):
            continue

        md_file = filename + ".md"
        md_exists = os.path.exists(os.path.join(UPLOAD_FOLDER, md_file))

        files.append(
            {
                "filename": filename,
                "size": os.path.getsize(filepath),
                "modified": datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat(),
                "has_analysis": md_exists,
                "md_file": md_file if md_exists else None,
            }
        )

    files.sort(key=lambda x: x["modified"], reverse=True)
    return files


def load_markdown(md_filename: str) -> str | None:
    """Load and return a previously saved markdown analysis, or None."""
    if not md_filename.endswith(".md"):
        return None
    safe = secure_filename(md_filename)
    path = os.path.join(UPLOAD_FOLDER, safe)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------------------
# Flask application factory – keeps the REST API available for
# backward-compatible container deployments and health-checks.
# ---------------------------------------------------------------------------

def create_flask_app() -> Flask:
    """Return a fully configured Flask app with all routes registered."""
    app = Flask(__name__)
    app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
    app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/upload", methods=["POST"])
    def upload_file():
        if "files" not in request.files:
            return jsonify({"success": False, "message": "No files provided"}), 400

        files = request.files.getlist("files")
        if not files or all(f.filename == "" for f in files):
            return jsonify({"success": False, "message": "No files selected"}), 400

        uploaded = 0
        failed = 0
        errors = []
        results = []

        for file in files:
            if file and file.filename:
                if not allowed_file(file.filename):
                    failed += 1
                    errors.append(f"{file.filename}: File type not allowed")
                    continue
                try:
                    result = save_uploaded_file(file)
                    results.append(result)
                    uploaded += 1
                except Exception as e:
                    failed += 1
                    errors.append(f"{file.filename}: {str(e)}")

        return (
            jsonify({"success": uploaded > 0, "uploaded": uploaded,
                    "failed": failed, "errors": errors, "results": results}),
            200 if uploaded > 0 else 400,
        )

    @app.route("/health")
    def health():
        return jsonify({"status": "healthy", "service": "file-upload-app"}), 200

    @app.route("/analysis/<filename>")
    def get_analysis(filename):
        content = load_markdown(filename)
        if content is None:
            return jsonify({"error": "Analysis not found"}), 404
        return content, 200, {"Content-Type": "text/markdown; charset=utf-8"}

    @app.route("/files")
    def list_files():
        try:
            files = list_uploaded_files()
            return jsonify({"files": files, "count": len(files)}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return app


# ---------------------------------------------------------------------------
# Standalone execution – start the Flask REST API on its own.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app = create_flask_app()
    port = int(os.environ.get("PORT", 8080))
    print(f"🚀 Upload Backend (Flask) starting on port {port}")
    print(f"📁 Upload folder: {UPLOAD_FOLDER}")
    print(f"📊 Max file size: {MAX_CONTENT_LENGTH / (1024*1024):.1f}MB")
    app.run(host="0.0.0.0", port=port, debug=False)
