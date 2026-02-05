# Document Intelligence JSON Output Reference

This document describes the structure of the JSON output from Azure Document Intelligence analysis.

## Overview

When a file is uploaded and processed, the application generates a `.analysis.json` file with structured data extracted from the document.

## JSON Structure

### Root Level

```json
{
  "processed": true,
  "model_id": "prebuilt-document",
  "api_version": "2023-07-31",
  "content": "Full extracted text content...",
  "pages": [...],
  "tables": [...],
  "key_value_pairs": [...],
  "paragraphs": [...]
}
```

### Fields

- **processed** (boolean): Whether the document was successfully analyzed
- **model_id** (string): The Document Intelligence model used (e.g., "prebuilt-document")
- **api_version** (string): API version used for analysis
- **content** (string): Full text content extracted from the document

### Pages Array

Each page contains layout information:

```json
{
  "page_number": 1,
  "width": 8.5,
  "height": 11.0,
  "unit": "inch",
  "lines_count": 50,
  "words_count": 300,
  "lines": [
    {
      "content": "Sample text line",
      "polygon": [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
    }
  ]
}
```

### Tables Array

Extracted tables with cell data:

```json
{
  "row_count": 5,
  "column_count": 3,
  "cells": [
    {
      "content": "Cell value",
      "row_index": 0,
      "column_index": 0,
      "row_span": 1,
      "column_span": 1
    }
  ]
}
```

### Key-Value Pairs Array

Form fields and their values:

```json
{
  "key": "Invoice Number",
  "value": "INV-12345",
  "confidence": 0.95
}
```

### Paragraphs Array

Paragraph-level text with semantic roles:

```json
{
  "content": "This is a paragraph of text...",
  "role": "title"  // Can be: title, sectionHeading, pageHeader, pageFooter, etc.
}
```

## Error Handling

If processing fails, the JSON will contain:

```json
{
  "processed": false,
  "error": "Error description",
  "file_type": "xyz"  // Optional
}
```

## Usage Examples

### Python

```python
import json

# Load analysis result
with open('file.pdf.analysis.json', 'r') as f:
    analysis = json.load(f)

# Extract all text
full_text = analysis['content']

# Get table data
for table in analysis['tables']:
    print(f"Table with {table['row_count']} rows and {table['column_count']} columns")
    for cell in table['cells']:
        print(f"  [{cell['row_index']},{cell['column_index']}]: {cell['content']}")

# Get key-value pairs
for kv in analysis['key_value_pairs']:
    if kv['key'] and kv['value']:
        print(f"{kv['key']}: {kv['value']}")
```

### JavaScript/TypeScript

```javascript
// Load analysis result
const fs = require('fs');
const analysis = JSON.parse(fs.readFileSync('file.pdf.analysis.json', 'utf8'));

// Extract text by page
analysis.pages.forEach(page => {
  console.log(`Page ${page.page_number}:`);
  page.lines.forEach(line => {
    console.log(`  ${line.content}`);
  });
});

// Process tables
analysis.tables.forEach((table, idx) => {
  console.log(`Table ${idx + 1}:`);
  // Reconstruct table structure
  const rows = Array(table.row_count).fill(null).map(() => 
    Array(table.column_count).fill('')
  );
  
  table.cells.forEach(cell => {
    rows[cell.row_index][cell.column_index] = cell.content;
  });
  
  console.table(rows);
});
```

### cURL - Retrieve Analysis

```bash
# Upload file
curl -X POST -F "files=@document.pdf" http://localhost:8080/upload

# Get analysis (filename from upload response)
curl http://localhost:8080/analysis/20260204_120000_document.pdf.analysis.json

# List all files
curl http://localhost:8080/files
```

## Next Steps

The JSON output can be used for:

1. **Database Storage**: Store in Cosmos DB, SQL Database, or other data stores
2. **Search Indexing**: Feed into Azure AI Search for full-text search
3. **Data Processing**: Extract specific fields for business logic
4. **Machine Learning**: Use as training data or features
5. **Integration**: Pass to downstream services via API or message queues

## Document Intelligence Models

The app currently uses the `prebuilt-document` model, which is general-purpose. Other available models include:

- **prebuilt-layout**: Advanced layout analysis
- **prebuilt-read**: Optimized for text extraction
- **prebuilt-invoice**: Specialized for invoices
- **prebuilt-receipt**: For receipts
- **prebuilt-businessCard**: For business cards
- **prebuilt-idDocument**: For ID cards and passports

To use a different model, modify the `process_document_with_ai()` function in `app.py`.

## References

- [Azure Document Intelligence Documentation](https://learn.microsoft.com/azure/ai-services/document-intelligence/)
- [Prebuilt Models](https://learn.microsoft.com/azure/ai-services/document-intelligence/concept-model-overview)
- [Python SDK Documentation](https://learn.microsoft.com/python/api/azure-ai-formrecognizer/)
