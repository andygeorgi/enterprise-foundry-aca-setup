#!/usr/bin/env python3
"""
File Upload Application with Azure Document Intelligence
Serves a web interface for uploading files and processing them with Azure Document Intelligence
"""

from flask import Flask, request, render_template_string, jsonify, send_from_directory
import os
import json
from datetime import datetime
from werkzeug.utils import secure_filename
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', '/app/uploads')
MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB default
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'zip', 'csv', 'json', 'xml'}

# Azure Document Intelligence Configuration
DOCINTEL_ENDPOINT = os.environ.get('AZURE_DOCINTEL_ENDPOINT', '')
CLIENT_ID = os.environ.get('AZURE_CLIENT_ID', '')  # For managed identity

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize Document Intelligence Client with Managed Identity
document_analysis_client = None
if DOCINTEL_ENDPOINT:
    try:
        if CLIENT_ID:
            # Use managed identity with specific client ID
            credential = ManagedIdentityCredential(client_id=CLIENT_ID)
            document_analysis_client = DocumentAnalysisClient(
                endpoint=DOCINTEL_ENDPOINT,
                credential=credential
            )
            print(f"✓ Document Intelligence client initialized with managed identity (client_id: {CLIENT_ID})")
        else:
            # Use default credential (managed identity, Azure CLI, etc.)
            credential = DefaultAzureCredential()
            document_analysis_client = DocumentAnalysisClient(
                endpoint=DOCINTEL_ENDPOINT,
                credential=credential
            )
            print("✓ Document Intelligence client initialized with default credential")
    except Exception as e:
        print(f"⚠️  Warning: Could not initialize Document Intelligence client: {e}")
        print("   Files will be uploaded but not processed")
else:
    print("⚠️  Warning: AZURE_DOCINTEL_ENDPOINT not set")
    print("   Files will be uploaded but not processed")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_document_with_ai(filepath):
    """
    Process a document with Azure Document Intelligence
    Returns a dictionary with analysis results as JSON
    """
    if not document_analysis_client:
        return {
            'error': 'Document Intelligence not configured',
            'processed': False
        }
    
    try:
        # Determine file type
        file_ext = filepath.rsplit('.', 1)[1].lower() if '.' in filepath else ''
        
        # Document types supported by Document Intelligence
        processable_types = {'pdf', 'png', 'jpg', 'jpeg', 'tiff', 'bmp'}
        
        if file_ext not in processable_types:
            return {
                'error': f'File type .{file_ext} not supported for document analysis',
                'processed': False,
                'file_type': file_ext
            }
        
        # Read the document
        with open(filepath, 'rb') as f:
            # Use the general document model (prebuilt-document)
            # This extracts text, tables, key-value pairs, and document structure
            poller = document_analysis_client.begin_analyze_document(
                "prebuilt-document", f
            )
            result = poller.result()
        
        # Convert result to JSON-serializable format
        analysis_result = {
            'processed': True,
            'model_id': result.model_id,
            'api_version': result.api_version,
            'content': result.content,  # Full text content
            'pages': [],
            'tables': [],
            'key_value_pairs': [],
            'paragraphs': []
        }
        
        # Extract page information
        for page in result.pages:
            page_info = {
                'page_number': page.page_number,
                'width': page.width,
                'height': page.height,
                'unit': page.unit,
                'lines_count': len(page.lines) if page.lines else 0,
                'words_count': len(page.words) if page.words else 0,
                'lines': [{'content': line.content, 'polygon': [list(point) for point in line.polygon]} for line in (page.lines or [])]
            }
            analysis_result['pages'].append(page_info)
        
        # Extract tables
        if result.tables:
            for table in result.tables:
                table_info = {
                    'row_count': table.row_count,
                    'column_count': table.column_count,
                    'cells': []
                }
                for cell in table.cells:
                    table_info['cells'].append({
                        'content': cell.content,
                        'row_index': cell.row_index,
                        'column_index': cell.column_index,
                        'row_span': cell.row_span,
                        'column_span': cell.column_span,
                    })
                analysis_result['tables'].append(table_info)
        
        # Extract key-value pairs
        if result.key_value_pairs:
            for kv in result.key_value_pairs:
                kv_info = {
                    'key': kv.key.content if kv.key else None,
                    'value': kv.value.content if kv.value else None,
                    'confidence': kv.confidence
                }
                analysis_result['key_value_pairs'].append(kv_info)
        
        # Extract paragraphs
        if result.paragraphs:
            for para in result.paragraphs:
                para_info = {
                    'content': para.content,
                    'role': para.role if hasattr(para, 'role') else None
                }
                analysis_result['paragraphs'].append(para_info)
        
        return analysis_result
        
    except Exception as e:
        return {
            'error': f'Document analysis failed: {str(e)}',
            'processed': False
        }

# JSON Viewer Template
JSON_VIEWER_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Document Analysis - {{ filename }}</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }
        
        .header h1 {
            color: white;
            margin-bottom: 10px;
            font-size: 2em;
        }
        
        .header .filename {
            color: rgba(255,255,255,0.9);
            font-size: 1.1em;
            font-family: 'Courier New', monospace;
        }
        
        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        
        .tab {
            background: #2d2d30;
            border: none;
            color: #d4d4d4;
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1em;
            transition: all 0.3s ease;
        }
        
        .tab:hover {
            background: #3e3e42;
        }
        
        .tab.active {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        .tab-content {
            display: none;
            background: #252526;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }
        
        .tab-content.active {
            display: block;
        }
        
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .summary-card {
            background: #1e1e1e;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }
        
        .summary-card h3 {
            color: #667eea;
            margin-bottom: 10px;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .summary-card .value {
            font-size: 2em;
            font-weight: 600;
            color: white;
        }
        
        .content-section {
            background: #1e1e1e;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        
        .content-section h2 {
            color: #667eea;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #3e3e42;
        }
        
        .text-content {
            line-height: 1.8;
            white-space: pre-wrap;
            font-family: 'Courier New', monospace;
            font-size: 0.95em;
        }
        
        .table-container {
            overflow-x: auto;
            margin: 20px 0;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            background: #1e1e1e;
        }
        
        th {
            background: #667eea;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }
        
        td {
            padding: 12px;
            border-bottom: 1px solid #3e3e42;
        }
        
        tr:hover {
            background: #2d2d30;
        }
        
        .kv-pair {
            background: #1e1e1e;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 10px;
            border-left: 3px solid #667eea;
        }
        
        .kv-key {
            color: #4ec9b0;
            font-weight: 600;
            margin-bottom: 5px;
        }
        
        .kv-value {
            color: #ce9178;
            font-family: 'Courier New', monospace;
        }
        
        .confidence {
            color: #858585;
            font-size: 0.85em;
            margin-left: 10px;
        }
        
        pre {
            background: #1e1e1e;
            padding: 20px;
            border-radius: 8px;
            overflow-x: auto;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            line-height: 1.6;
        }
        
        .json-key {
            color: #9cdcfe;
        }
        
        .json-string {
            color: #ce9178;
        }
        
        .json-number {
            color: #b5cea8;
        }
        
        .json-boolean {
            color: #569cd6;
        }
        
        .json-null {
            color: #569cd6;
        }
        
        .back-link {
            display: inline-block;
            background: #2d2d30;
            color: #d4d4d4;
            padding: 10px 20px;
            border-radius: 6px;
            text-decoration: none;
            margin-bottom: 20px;
            transition: all 0.3s ease;
        }
        
        .back-link:hover {
            background: #3e3e42;
            transform: translateX(-5px);
        }
        
        .page-info {
            background: #1e1e1e;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 15px;
        }
        
        .page-number {
            color: #667eea;
            font-weight: 600;
            font-size: 1.2em;
        }
        
        .line {
            padding: 8px;
            margin: 5px 0;
            background: #2d2d30;
            border-radius: 4px;
        }
    </style>
</head>
<body>
    <div class="container">
        <a href="/" class="back-link">← Back to Upload</a>
        
        <div class="header">
            <h1>📊 Document Analysis</h1>
            <div class="filename">{{ filename }}</div>
        </div>
        
        <div class="tabs">
            <button class="tab active" onclick="showTab('summary')">📈 Summary</button>
            <button class="tab" onclick="showTab('content')">📄 Content</button>
            <button class="tab" onclick="showTab('tables')">📋 Tables</button>
            <button class="tab" onclick="showTab('kvpairs')">🔑 Key-Value Pairs</button>
            <button class="tab" onclick="showTab('pages')">📑 Pages</button>
            <button class="tab" onclick="showTab('json')">💾 Raw JSON</button>
        </div>
        
        <!-- Summary Tab -->
        <div id="summary" class="tab-content active">
            <div class="summary-grid">
                <div class="summary-card">
                    <h3>Status</h3>
                    <div class="value">{{ '✅ Processed' if analysis.processed else '❌ Failed' }}</div>
                </div>
                {% if analysis.processed %}
                <div class="summary-card">
                    <h3>Pages</h3>
                    <div class="value">{{ analysis.pages|length }}</div>
                </div>
                <div class="summary-card">
                    <h3>Tables</h3>
                    <div class="value">{{ analysis.tables|length }}</div>
                </div>
                <div class="summary-card">
                    <h3>Key-Value Pairs</h3>
                    <div class="value">{{ analysis.key_value_pairs|length }}</div>
                </div>
                <div class="summary-card">
                    <h3>Paragraphs</h3>
                    <div class="value">{{ analysis.paragraphs|length }}</div>
                </div>
                <div class="summary-card">
                    <h3>Model</h3>
                    <div class="value" style="font-size: 1.2em;">{{ analysis.model_id }}</div>
                </div>
                {% endif %}
            </div>
            
            {% if not analysis.processed %}
            <div class="content-section">
                <h2>❌ Error</h2>
                <p style="color: #f48771;">{{ analysis.error }}</p>
            </div>
            {% endif %}
        </div>
        
        <!-- Content Tab -->
        <div id="content" class="tab-content">
            {% if analysis.processed and analysis.content %}
            <div class="content-section">
                <h2>📄 Extracted Text</h2>
                <div class="text-content">{{ analysis.content }}</div>
            </div>
            {% else %}
            <p>No content extracted.</p>
            {% endif %}
        </div>
        
        <!-- Tables Tab -->
        <div id="tables" class="tab-content">
            {% if analysis.processed and analysis.tables %}
                {% for table in analysis.tables %}
                <div class="content-section">
                    <h2>Table {{ loop.index }} ({{ table.row_count }} rows × {{ table.column_count }} columns)</h2>
                    <div class="table-container">
                        <table>
                            {% for row in range(table.row_count) %}
                            <tr>
                                {% for col in range(table.column_count) %}
                                    {% set cell = table.cells|selectattr('row_index', 'equalto', row)|selectattr('column_index', 'equalto', col)|first %}
                                    {% if cell %}
                                        <{{ 'th' if row == 0 else 'td' }}>{{ cell.content }}</{{ 'th' if row == 0 else 'td' }}>
                                    {% else %}
                                        <{{ 'th' if row == 0 else 'td' }}></{{ 'th' if row == 0 else 'td' }}>
                                    {% endif %}
                                {% endfor %}
                            </tr>
                            {% endfor %}
                        </table>
                    </div>
                </div>
                {% endfor %}
            {% else %}
            <p>No tables found in the document.</p>
            {% endif %}
        </div>
        
        <!-- Key-Value Pairs Tab -->
        <div id="kvpairs" class="tab-content">
            {% if analysis.processed and analysis.key_value_pairs %}
                <div class="content-section">
                    <h2>🔑 Extracted Key-Value Pairs</h2>
                    {% for kv in analysis.key_value_pairs %}
                    <div class="kv-pair">
                        <div class="kv-key">{{ kv.key or '(no key)' }}<span class="confidence">(confidence: {{ "%.1f"|format(kv.confidence * 100) }}%)</span></div>
                        <div class="kv-value">{{ kv.value or '(no value)' }}</div>
                    </div>
                    {% endfor %}
                </div>
            {% else %}
            <p>No key-value pairs found in the document.</p>
            {% endif %}
        </div>
        
        <!-- Pages Tab -->
        <div id="pages" class="tab-content">
            {% if analysis.processed and analysis.pages %}
                {% for page in analysis.pages %}
                <div class="content-section">
                    <div class="page-info">
                        <span class="page-number">Page {{ page.page_number }}</span>
                        <span class="confidence">{{ page.width }} × {{ page.height }} {{ page.unit }}</span>
                        <span class="confidence">{{ page.lines_count }} lines, {{ page.words_count }} words</span>
                    </div>
                    {% if page.lines %}
                        {% for line in page.lines %}
                        <div class="line">{{ line.content }}</div>
                        {% endfor %}
                    {% endif %}
                </div>
                {% endfor %}
            {% else %}
            <p>No page information available.</p>
            {% endif %}
        </div>
        
        <!-- Raw JSON Tab -->
        <div id="json" class="tab-content">
            <div class="content-section">
                <h2>💾 Raw JSON Data</h2>
                <pre id="jsonContent">{{ json_data }}</pre>
            </div>
        </div>
    </div>
    
    <script>
        function showTab(tabName) {
            // Hide all tabs
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Show selected tab
            document.getElementById(tabName).classList.add('active');
            event.target.classList.add('active');
        }
        
        // Syntax highlight JSON
        function syntaxHighlight(json) {
            json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, function (match) {
                var cls = 'json-number';
                if (/^"/.test(match)) {
                    if (/:$/.test(match)) {
                        cls = 'json-key';
                    } else {
                        cls = 'json-string';
                    }
                } else if (/true|false/.test(match)) {
                    cls = 'json-boolean';
                } else if (/null/.test(match)) {
                    cls = 'json-null';
                }
                return '<span class="' + cls + '">' + match + '</span>';
            });
        }
        
        // Apply syntax highlighting
        const jsonElement = document.getElementById('jsonContent');
        if (jsonElement) {
            jsonElement.innerHTML = syntaxHighlight(jsonElement.textContent);
        }
    </script>
</body>
</html>
"""

# HTML Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>File Upload - Enterprise Foundry</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        
        .container {
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            max-width: 700px;
            width: 100%;
            padding: 40px;
        }
        
        h1 {
            color: #333;
            margin-bottom: 10px;
            font-size: 2em;
        }
        
        .subtitle {
            color: #666;
            margin-bottom: 30px;
            font-size: 0.95em;
        }
        
        .upload-area {
            border: 3px dashed #667eea;
            border-radius: 12px;
            padding: 40px;
            text-align: center;
            background: #f8f9ff;
            transition: all 0.3s ease;
            cursor: pointer;
            margin-bottom: 20px;
        }
        
        .upload-area:hover, .upload-area.drag-over {
            background: #eef0ff;
            border-color: #764ba2;
            transform: scale(1.02);
        }
        
        .upload-icon {
            font-size: 4em;
            margin-bottom: 15px;
            color: #667eea;
        }
        
        .upload-text {
            color: #666;
            font-size: 1.1em;
            margin-bottom: 10px;
        }
        
        .upload-hint {
            color: #999;
            font-size: 0.9em;
        }
        
        #fileInput {
            display: none;
        }
        
        .file-list {
            margin: 20px 0;
        }
        
        .file-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px;
            background: #f5f5f5;
            border-radius: 8px;
            margin-bottom: 8px;
            transition: all 0.2s ease;
        }
        
        .file-item:hover {
            background: #ebebeb;
        }
        
        .file-name {
            flex: 1;
            font-size: 0.95em;
            color: #333;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        
        .file-size {
            color: #999;
            font-size: 0.85em;
            margin: 0 15px;
        }
        
        .remove-btn {
            background: #ff4757;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 6px 12px;
            cursor: pointer;
            font-size: 0.85em;
            transition: all 0.2s ease;
        }
        
        .remove-btn:hover {
            background: #ee5a6f;
            transform: scale(1.05);
        }
        
        .upload-btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 14px 30px;
            font-size: 1.1em;
            cursor: pointer;
            width: 100%;
            transition: all 0.3s ease;
            font-weight: 600;
        }
        
        .upload-btn:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.4);
        }
        
        .upload-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        .message {
            padding: 15px;
            border-radius: 8px;
            margin-top: 20px;
            font-size: 0.95em;
        }
        
        .message.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        
        .message.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        
        .stats {
            display: flex;
            justify-content: space-around;
            margin-top: 30px;
            padding-top: 30px;
            border-top: 1px solid #eee;
        }
        
        .stat-item {
            text-align: center;
        }
        
        .stat-value {
            font-size: 2em;
            font-weight: 600;
            color: #667eea;
            display: block;
        }
        
        .stat-label {
            color: #999;
            font-size: 0.85em;
            margin-top: 5px;
        }
        
        .recent-files {
            margin-top: 30px;
            padding-top: 30px;
            border-top: 1px solid #eee;
        }
        
        .recent-files h2 {
            color: #333;
            margin-bottom: 15px;
            font-size: 1.3em;
        }
        
        .recent-file-item {
            background: #f8f9ff;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: all 0.2s ease;
        }
        
        .recent-file-item:hover {
            background: #eef0ff;
            transform: translateX(5px);
        }
        
        .recent-file-name {
            color: #333;
            font-weight: 500;
        }
        
        .recent-file-date {
            color: #999;
            font-size: 0.85em;
            margin-left: 10px;
        }
        
        .view-analysis-btn {
            background: #667eea;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            cursor: pointer;
            font-size: 0.9em;
            text-decoration: none;
            display: inline-block;
            transition: all 0.2s ease;
        }
        
        .view-analysis-btn:hover {
            background: #764ba2;
            transform: scale(1.05);
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .spinner {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid rgba(255,255,255,.3);
            border-radius: 50%;
            border-top-color: white;
            animation: spin 1s ease-in-out infinite;
            margin-right: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📁 File Upload with AI Analysis</h1>
        <p class="subtitle">Enterprise Foundry - Powered by Azure Document Intelligence</p>
        
        <div class="upload-area" id="uploadArea">
            <div class="upload-icon">☁️</div>
            <div class="upload-text">Click to browse or drag and drop files here</div>
            <div class="upload-hint">Supports: PDF, images (analyzed with AI), and other documents (max 16MB per file)</div>
        </div>
        
        <input type="file" id="fileInput" multiple>
        
        <div class="file-list" id="fileList"></div>
        
        <button class="upload-btn" id="uploadBtn" onclick="uploadFiles()" disabled>
            Upload Files
        </button>
        
        <div id="message"></div>
        
        <div class="stats">
            <div class="stat-item">
                <span class="stat-value" id="fileCount">0</span>
                <span class="stat-label">Files Selected</span>
            </div>
            <div class="stat-item">
                <span class="stat-value" id="totalSize">0 KB</span>
                <span class="stat-label">Total Size</span>
            </div>
        </div>
        
        <div class="recent-files" id="recentFiles" style="display: none;">
            <h2>📋 Recent Analyses</h2>
            <div id="recentFilesList"></div>
        </div>
    </div>

    <script>
        let selectedFiles = [];
        const fileInput = document.getElementById('fileInput');
        const uploadArea = document.getElementById('uploadArea');
        const fileList = document.getElementById('fileList');
        const uploadBtn = document.getElementById('uploadBtn');
        const messageDiv = document.getElementById('message');
        
        // Load recent files on page load
        loadRecentFiles();
        
        async function loadRecentFiles() {
            try {
                const response = await fetch('/files');
                const data = await response.json();
                
                if (data.files && data.files.length > 0) {
                    const recentFiles = data.files.slice(0, 5);  // Show last 5 files
                    const recentFilesList = document.getElementById('recentFilesList');
                    const recentFilesDiv = document.getElementById('recentFiles');
                    
                    recentFilesList.innerHTML = '';
                    recentFiles.forEach(file => {
                        if (file.has_analysis) {
                            const fileItem = document.createElement('div');
                            fileItem.className = 'recent-file-item';
                            
                            const fileInfo = document.createElement('div');
                            fileInfo.innerHTML = `
                                <span class="recent-file-name">${file.filename}</span>
                                <span class="recent-file-date">${new Date(file.modified).toLocaleString()}</span>
                            `;
                            
                            const viewBtn = document.createElement('a');
                            viewBtn.href = file.view_url;
                            viewBtn.className = 'view-analysis-btn';
                            viewBtn.textContent = '📊 View Analysis';
                            viewBtn.target = '_blank';
                            
                            fileItem.appendChild(fileInfo);
                            fileItem.appendChild(viewBtn);
                            recentFilesList.appendChild(fileItem);
                        }
                    });
                    
                    if (recentFilesList.children.length > 0) {
                        recentFilesDiv.style.display = 'block';
                    }
                }
            } catch (error) {
                console.error('Failed to load recent files:', error);
            }
        }
        
        // Click to browse
        uploadArea.addEventListener('click', () => fileInput.click());
        
        // File selection
        fileInput.addEventListener('change', (e) => {
            handleFiles(Array.from(e.target.files));
        });
        
        // Drag and drop
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('drag-over');
        });
        
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('drag-over');
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('drag-over');
            handleFiles(Array.from(e.dataTransfer.files));
        });
        
        function handleFiles(files) {
            files.forEach(file => {
                if (!selectedFiles.find(f => f.name === file.name)) {
                    selectedFiles.push(file);
                }
            });
            updateFileList();
        }
        
        function removeFile(index) {
            selectedFiles.splice(index, 1);
            updateFileList();
        }
        
        function updateFileList() {
            fileList.innerHTML = '';
            let totalSize = 0;
            
            selectedFiles.forEach((file, index) => {
                totalSize += file.size;
                const fileItem = document.createElement('div');
                fileItem.className = 'file-item';
                fileItem.innerHTML = `
                    <span class="file-name">${file.name}</span>
                    <span class="file-size">${formatFileSize(file.size)}</span>
                    <button class="remove-btn" onclick="removeFile(${index})">Remove</button>
                `;
                fileList.appendChild(fileItem);
            });
            
            document.getElementById('fileCount').textContent = selectedFiles.length;
            document.getElementById('totalSize').textContent = formatFileSize(totalSize);
            uploadBtn.disabled = selectedFiles.length === 0;
        }
        
        function formatFileSize(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
        }
        
        async function uploadFiles() {
            if (selectedFiles.length === 0) return;
            
            const formData = new FormData();
            selectedFiles.forEach(file => {
                formData.append('files', file);
            });
            
            uploadBtn.disabled = true;
            uploadBtn.innerHTML = '<span class="spinner"></span>Uploading...';
            messageDiv.innerHTML = '';
            
            try {
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    let detailsHtml = '';
                    if (result.results && result.results.length > 0) {
                        detailsHtml = '<div style="margin-top: 15px; text-align: left;"><strong>Processing Results:</strong><ul style="margin: 10px 0;">';
                        result.results.forEach(r => {
                            detailsHtml += `<li style="margin: 5px 0;"><strong>${r.original_filename}</strong>: `;
                            if (r.processed) {
                                detailsHtml += `✅ Analyzed - ${r.pages} page(s), ${r.tables} table(s), ${r.key_value_pairs} key-value pairs<br>`;
                                detailsHtml += `<small><a href="/view/${r.json_file}" target="_blank" style="color: #667eea; text-decoration: underline;">📊 View Analysis</a> | `;
                                detailsHtml += `<a href="/analysis/${r.json_file}" target="_blank" style="color: #667eea; text-decoration: underline;">📥 Download JSON</a></small>`;
                            } else {
                                detailsHtml += `⚠️ ${r.error || 'Not processed'}`;
                            }
                            detailsHtml += '</li>';
                        });
                        detailsHtml += '</ul></div>';
                    }
                    
                    messageDiv.innerHTML = `
                        <div class="message success">
                            ✅ Successfully uploaded ${result.uploaded} file(s)!
                            ${result.failed > 0 ? `<br>⚠️ Failed: ${result.failed}` : ''}
                            ${detailsHtml}
                        </div>
                    `;
                    selectedFiles = [];
                    updateFileList();
                    fileInput.value = '';
                    
                    // Reload recent files list
                    loadRecentFiles();
                } else {
                    messageDiv.innerHTML = `
                        <div class="message error">
                            ❌ Error: ${result.message || 'Upload failed'}
                        </div>
                    `;
                }
            } catch (error) {
                messageDiv.innerHTML = `
                    <div class="message error">
                        ❌ Network error: ${error.message}
                    </div>
                `;
            } finally {
                uploadBtn.disabled = selectedFiles.length === 0;
                uploadBtn.innerHTML = 'Upload Files';
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Serve the upload interface"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and process with Document Intelligence"""
    if 'files' not in request.files:
        return jsonify({'success': False, 'message': 'No files provided'}), 400
    
    files = request.files.getlist('files')
    
    if not files or all(f.filename == '' for f in files):
        return jsonify({'success': False, 'message': 'No files selected'}), 400
    
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
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                unique_filename = f"{timestamp}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                
                # Save the uploaded file
                file.save(filepath)
                file_size = os.path.getsize(filepath)
                uploaded += 1
                print(f"✓ Uploaded: {unique_filename} ({file_size} bytes)")
                
                # Process with Document Intelligence
                analysis_result = process_document_with_ai(filepath)
                
                # Save JSON result alongside the file
                json_filepath = filepath + '.analysis.json'
                with open(json_filepath, 'w', encoding='utf-8') as json_file:
                    json.dump(analysis_result, json_file, indent=2, ensure_ascii=False)
                
                print(f"  → Analysis saved: {os.path.basename(json_filepath)}")
                
                # Add to results
                file_result = {
                    'filename': unique_filename,
                    'original_filename': filename,
                    'size': file_size,
                    'processed': analysis_result.get('processed', False),
                    'json_file': os.path.basename(json_filepath)
                }
                
                if analysis_result.get('processed'):
                    file_result['pages'] = len(analysis_result.get('pages', []))
                    file_result['tables'] = len(analysis_result.get('tables', []))
                    file_result['key_value_pairs'] = len(analysis_result.get('key_value_pairs', []))
                    print(f"  → Extracted: {file_result['pages']} pages, {file_result['tables']} tables, {file_result['key_value_pairs']} key-value pairs")
                else:
                    file_result['error'] = analysis_result.get('error', 'Unknown error')
                    print(f"  ⚠️  Not processed: {file_result['error']}")
                
                results.append(file_result)
                
            except Exception as e:
                failed += 1
                error_msg = f"{file.filename}: {str(e)}"
                errors.append(error_msg)
                print(f"✗ Failed: {error_msg}")
    
    return jsonify({
        'success': uploaded > 0,
        'uploaded': uploaded,
        'failed': failed,
        'errors': errors,
        'results': results
    }), 200 if uploaded > 0 else 400

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'file-upload-app'}), 200

@app.route('/analysis/<filename>')
def get_analysis(filename):
    """Retrieve the JSON analysis for a specific file"""
    try:
        # Security: only allow .json files and prevent directory traversal
        if not filename.endswith('.analysis.json'):
            return jsonify({'error': 'Invalid file type'}), 400
        
        filename = secure_filename(filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'Analysis not found'}), 404
        
        with open(filepath, 'r', encoding='utf-8') as f:
            analysis_data = json.load(f)
        
        return jsonify(analysis_data), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/files')
def list_files():
    """List all uploaded files and their analyses"""
    try:
        files = []
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            if filename.endswith('.analysis.json'):
                continue  # Skip JSON files
            
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.isfile(filepath):
                json_file = filename + '.analysis.json'
                json_exists = os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], json_file))
                
                file_info = {
                    'filename': filename,
                    'size': os.path.getsize(filepath),
                    'modified': datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat(),
                    'has_analysis': json_exists,
                    'analysis_url': f'/analysis/{json_file}' if json_exists else None,
                    'view_url': f'/view/{json_file}' if json_exists else None
                }
                files.append(file_info)
        
        # Sort by modification time (newest first)
        files.sort(key=lambda x: x['modified'], reverse=True)
        
        return jsonify({'files': files, 'count': len(files)}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/view/<filename>')
def view_analysis(filename):
    """View formatted JSON analysis in browser"""
    try:
        # Security: only allow .json files and prevent directory traversal
        if not filename.endswith('.analysis.json'):
            return "Invalid file type", 400
        
        filename = secure_filename(filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        if not os.path.exists(filepath):
            return "Analysis not found", 404
        
        with open(filepath, 'r', encoding='utf-8') as f:
            analysis_data = json.load(f)
        
        # Render the JSON viewer template
        return render_template_string(JSON_VIEWER_TEMPLATE, 
                                      filename=filename,
                                      json_data=json.dumps(analysis_data, indent=2),
                                      analysis=analysis_data)
    except Exception as e:
        return f"Error: {str(e)}", 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print(f"🚀 File Upload App starting on port {port}")
    print(f"📁 Upload folder: {UPLOAD_FOLDER}")
    print(f"📊 Max file size: {MAX_CONTENT_LENGTH / (1024*1024):.1f}MB")
    app.run(host='0.0.0.0', port=port, debug=False)
