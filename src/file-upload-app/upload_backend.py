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
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
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
CLIENT_ID = os.environ.get("AZURE_CLIENT_ID", "")

# ---------------------------------------------------------------------------
# Azure Document Intelligence client (singleton)
# ---------------------------------------------------------------------------
document_analysis_client = None


def _init_docintel_client():
    """Initialise the Document Intelligence client once."""
    global document_analysis_client
    if document_analysis_client is not None:
        return

    if not DOCINTEL_ENDPOINT:
        print("⚠️  Warning: AZURE_DOCINTEL_ENDPOINT not set – files will be uploaded but not processed")
        return

    try:
        if CLIENT_ID:
            credential = ManagedIdentityCredential(client_id=CLIENT_ID)
            document_analysis_client = DocumentAnalysisClient(
                endpoint=DOCINTEL_ENDPOINT, credential=credential
            )
            print(
                f"✓ Document Intelligence client initialised with managed identity (client_id: {CLIENT_ID})")
        else:
            credential = DefaultAzureCredential()
            document_analysis_client = DocumentAnalysisClient(
                endpoint=DOCINTEL_ENDPOINT, credential=credential
            )
            print("✓ Document Intelligence client initialised with default credential")
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


def process_document_with_ai(filepath: str) -> dict:
    """
    Process a document with Azure Document Intelligence.
    Returns a dict with analysis results as JSON-serialisable data.
    """
    if not document_analysis_client:
        return {"error": "Document Intelligence not configured", "processed": False}

    try:
        file_ext = filepath.rsplit(
            ".", 1)[1].lower() if "." in filepath else ""
        processable_types = {"pdf", "png", "jpg", "jpeg", "tiff", "bmp"}

        if file_ext not in processable_types:
            return {
                "error": f"File type .{file_ext} not supported for document analysis",
                "processed": False,
                "file_type": file_ext,
            }

        with open(filepath, "rb") as f:
            poller = document_analysis_client.begin_analyze_document(
                "prebuilt-document", f)
            result = poller.result()

        analysis_result = {
            "processed": True,
            "model_id": result.model_id,
            "api_version": result.api_version,
            "content": result.content,
            "pages": [],
            "tables": [],
            "key_value_pairs": [],
            "paragraphs": [],
        }

        for page in result.pages:
            page_info = {
                "page_number": page.page_number,
                "width": page.width,
                "height": page.height,
                "unit": page.unit,
                "lines_count": len(page.lines) if page.lines else 0,
                "words_count": len(page.words) if page.words else 0,
                "lines": [
                    {"content": line.content, "polygon": [
                        list(point) for point in line.polygon]}
                    for line in (page.lines or [])
                ],
            }
            analysis_result["pages"].append(page_info)

        if result.tables:
            for table in result.tables:
                table_info = {
                    "row_count": table.row_count,
                    "column_count": table.column_count,
                    "cells": [
                        {
                            "content": cell.content,
                            "row_index": cell.row_index,
                            "column_index": cell.column_index,
                            "row_span": cell.row_span,
                            "column_span": cell.column_span,
                        }
                        for cell in table.cells
                    ],
                }
                analysis_result["tables"].append(table_info)

        if result.key_value_pairs:
            for kv in result.key_value_pairs:
                kv_info = {
                    "key": kv.key.content if kv.key else None,
                    "value": kv.value.content if kv.value else None,
                    "confidence": kv.confidence,
                }
                analysis_result["key_value_pairs"].append(kv_info)

        if result.paragraphs:
            for para in result.paragraphs:
                para_info = {
                    "content": para.content,
                    "role": para.role if hasattr(para, "role") else None,
                }
                analysis_result["paragraphs"].append(para_info)

        return analysis_result

    except Exception as e:
        return {"error": f"Document analysis failed: {str(e)}", "processed": False}


def save_uploaded_file(uploaded_file_storage) -> dict:
    """
    Accept a werkzeug ``FileStorage`` object (from Flask's ``request.files``),
    persist it to disk, run AI analysis, and return a result dict.
    """
    filename = secure_filename(uploaded_file_storage.filename)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_filename = f"{timestamp}_{filename}"
    filepath = os.path.join(UPLOAD_FOLDER, unique_filename)

    uploaded_file_storage.save(filepath)
    file_size = os.path.getsize(filepath)
    print(f"✓ Uploaded: {unique_filename} ({file_size} bytes)")

    analysis_result = process_document_with_ai(filepath)

    json_filepath = filepath + ".analysis.json"
    with open(json_filepath, "w", encoding="utf-8") as jf:
        json.dump(analysis_result, jf, indent=2, ensure_ascii=False)
    print(f"  → Analysis saved: {os.path.basename(json_filepath)}")

    file_result = {
        "filename": unique_filename,
        "original_filename": filename,
        "size": file_size,
        "processed": analysis_result.get("processed", False),
        "json_file": os.path.basename(json_filepath),
    }

    if analysis_result.get("processed"):
        file_result["pages"] = len(analysis_result.get("pages", []))
        file_result["tables"] = len(analysis_result.get("tables", []))
        file_result["key_value_pairs"] = len(
            analysis_result.get("key_value_pairs", []))
        print(
            f"  → Extracted: {file_result['pages']} pages, "
            f"{file_result['tables']} tables, "
            f"{file_result['key_value_pairs']} key-value pairs"
        )
    else:
        file_result["error"] = analysis_result.get("error", "Unknown error")
        print(f"  ⚠️  Not processed: {file_result['error']}")

    return file_result


def save_uploaded_bytes(file_bytes: bytes, original_filename: str) -> dict:
    """
    Accept raw bytes + filename (e.g. from Streamlit's ``st.file_uploader``),
    persist to disk, run AI analysis, and return a result dict.
    """
    filename = secure_filename(original_filename)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_filename = f"{timestamp}_{filename}"
    filepath = os.path.join(UPLOAD_FOLDER, unique_filename)

    with open(filepath, "wb") as f:
        f.write(file_bytes)

    file_size = os.path.getsize(filepath)
    print(f"✓ Uploaded: {unique_filename} ({file_size} bytes)")

    analysis_result = process_document_with_ai(filepath)

    json_filepath = filepath + ".analysis.json"
    with open(json_filepath, "w", encoding="utf-8") as jf:
        json.dump(analysis_result, jf, indent=2, ensure_ascii=False)
    print(f"  → Analysis saved: {os.path.basename(json_filepath)}")

    file_result = {
        "filename": unique_filename,
        "original_filename": filename,
        "size": file_size,
        "processed": analysis_result.get("processed", False),
        "json_file": os.path.basename(json_filepath),
    }

    if analysis_result.get("processed"):
        file_result["pages"] = len(analysis_result.get("pages", []))
        file_result["tables"] = len(analysis_result.get("tables", []))
        file_result["key_value_pairs"] = len(
            analysis_result.get("key_value_pairs", []))
    else:
        file_result["error"] = analysis_result.get("error", "Unknown error")

    return file_result


def list_uploaded_files() -> list[dict]:
    """Return a list of dicts describing every uploaded file."""
    files: list[dict] = []
    for filename in os.listdir(UPLOAD_FOLDER):
        if filename.endswith(".analysis.json"):
            continue
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        if not os.path.isfile(filepath):
            continue

        json_file = filename + ".analysis.json"
        json_exists = os.path.exists(os.path.join(UPLOAD_FOLDER, json_file))

        files.append(
            {
                "filename": filename,
                "size": os.path.getsize(filepath),
                "modified": datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat(),
                "has_analysis": json_exists,
                "json_file": json_file if json_exists else None,
            }
        )

    files.sort(key=lambda x: x["modified"], reverse=True)
    return files


def load_analysis(json_filename: str) -> dict | None:
    """Load and return a previously saved analysis JSON, or None."""
    if not json_filename.endswith(".analysis.json"):
        return None
    safe = secure_filename(json_filename)
    path = os.path.join(UPLOAD_FOLDER, safe)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


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
        data = load_analysis(filename)
        if data is None:
            return jsonify({"error": "Analysis not found"}), 404
        return jsonify(data), 200

    @app.route("/files")
    def list_files():
        try:
            files = list_uploaded_files()
            return jsonify({"files": files, "count": len(files)}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/view/<filename>")
    def view_analysis(filename):
        data = load_analysis(filename)
        if data is None:
            return "Analysis not found", 404
        return render_template(
            "viewer.html",
            filename=filename,
            json_data=json.dumps(data, indent=2),
            analysis=data,
        )

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
