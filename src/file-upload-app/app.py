#!/usr/bin/env python3
"""
Simple File Upload Application
Serves a web interface for uploading multiple files
"""

from flask import Flask, request, render_template_string, jsonify, send_from_directory
import os
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', '/app/uploads')
MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB default
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'zip', 'csv', 'json', 'xml'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
        <h1>📁 File Upload</h1>
        <p class="subtitle">Enterprise Foundry Container App</p>
        
        <div class="upload-area" id="uploadArea">
            <div class="upload-icon">☁️</div>
            <div class="upload-text">Click to browse or drag and drop files here</div>
            <div class="upload-hint">Supports: txt, pdf, images, documents, zip, csv, json, xml (max 16MB per file)</div>
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
    </div>

    <script>
        let selectedFiles = [];
        const fileInput = document.getElementById('fileInput');
        const uploadArea = document.getElementById('uploadArea');
        const fileList = document.getElementById('fileList');
        const uploadBtn = document.getElementById('uploadBtn');
        const messageDiv = document.getElementById('message');
        
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
                    messageDiv.innerHTML = `
                        <div class="message success">
                            ✅ Successfully uploaded ${result.uploaded} file(s)!
                            ${result.failed > 0 ? `<br>⚠️ Failed: ${result.failed}` : ''}
                        </div>
                    `;
                    selectedFiles = [];
                    updateFileList();
                    fileInput.value = '';
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
    """Handle file upload"""
    if 'files' not in request.files:
        return jsonify({'success': False, 'message': 'No files provided'}), 400
    
    files = request.files.getlist('files')
    
    if not files or all(f.filename == '' for f in files):
        return jsonify({'success': False, 'message': 'No files selected'}), 400
    
    uploaded = 0
    failed = 0
    errors = []
    
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
                
                file.save(filepath)
                uploaded += 1
                print(f"✓ Uploaded: {unique_filename} ({os.path.getsize(filepath)} bytes)")
                
            except Exception as e:
                failed += 1
                errors.append(f"{file.filename}: {str(e)}")
                print(f"✗ Failed: {file.filename} - {str(e)}")
    
    return jsonify({
        'success': uploaded > 0,
        'uploaded': uploaded,
        'failed': failed,
        'errors': errors
    }), 200 if uploaded > 0 else 400

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'file-upload-app'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 80))
    print(f"🚀 File Upload App starting on port {port}")
    print(f"📁 Upload folder: {UPLOAD_FOLDER}")
    print(f"📊 Max file size: {MAX_CONTENT_LENGTH / (1024*1024):.1f}MB")
    app.run(host='0.0.0.0', port=port, debug=False)
