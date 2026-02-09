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
