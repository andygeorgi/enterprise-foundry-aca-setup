# Document Intelligence Integration Summary

## Overview

The file upload application has been enhanced with Azure Document Intelligence (formerly Form Recognizer) to automatically analyze uploaded documents and extract structured data as JSON.

## Changes Made

### 1. Updated Dependencies ([requirements.txt](requirements.txt))

Added Azure SDK packages:
- `azure-ai-formrecognizer==3.3.3` - Document Intelligence SDK
- `azure-identity==1.18.0` - Managed identity authentication
- `requests==2.32.3` - For testing scripts

### 2. Enhanced Application ([app.py](app.py))

#### New Imports
```python
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
```

#### Configuration
Added environment variables for Document Intelligence:
- `AZURE_DOCINTEL_ENDPOINT` - Document Intelligence service endpoint
- `AZURE_CLIENT_ID` - (Optional) Managed identity client ID

#### New Function: `process_document_with_ai(filepath)`
Analyzes documents and extracts:
- **Text content** - Full document text
- **Pages** - Layout information with lines and words
- **Tables** - Structured table data
- **Key-value pairs** - Form fields
- **Paragraphs** - Semantic text blocks

Supported file types: PDF, PNG, JPG, JPEG, TIFF, BMP

#### Updated `/upload` Endpoint
- Saves uploaded files with timestamp prefix
- Processes files with Document Intelligence
- Saves analysis results as `.analysis.json` files
- Returns detailed processing results

#### New Endpoints

**`GET /analysis/<filename>`**
- Retrieves JSON analysis for a specific file
- Example: `/analysis/20260204_120000_document.pdf.analysis.json`

**`GET /files`**
- Lists all uploaded files
- Shows which files have analysis available
- Returns file metadata (size, modified date, analysis URL)

#### UI Updates
- Updated title: "File Upload with AI Analysis"
- Added subtitle: "Powered by Azure Document Intelligence"
- Enhanced success messages with analysis details
- Shows extracted data counts (pages, tables, key-value pairs)

### 3. Documentation

#### Updated [README.md](README.md)
- Added Document Intelligence features section
- Documented API endpoints with examples
- Updated environment variables
- Added JSON response examples
- Updated next steps to reflect integration

#### New [JSON_OUTPUT_REFERENCE.md](JSON_OUTPUT_REFERENCE.md)
- Complete JSON structure documentation
- Field descriptions
- Usage examples (Python, JavaScript)
- cURL examples
- Integration guidance

#### New [test_local.py](test_local.py)
- Local testing script
- Tests health, upload, and file listing endpoints
- Demonstrates JSON retrieval
- Usage: `python test_local.py <file1> [file2]...`

## JSON Output Structure

Each processed file generates a `.analysis.json` file with:

```json
{
  "processed": true,
  "model_id": "prebuilt-document",
  "content": "Full text...",
  "pages": [
    {
      "page_number": 1,
      "lines_count": 50,
      "words_count": 300,
      "lines": [...]
    }
  ],
  "tables": [
    {
      "row_count": 5,
      "column_count": 3,
      "cells": [...]
    }
  ],
  "key_value_pairs": [
    {
      "key": "Invoice Number",
      "value": "INV-12345",
      "confidence": 0.95
    }
  ],
  "paragraphs": [...]
}
```

## Deployment Considerations

### Environment Variables Required

When deploying to Azure Container Apps, configure:

```bash
AZURE_DOCINTEL_ENDPOINT="https://<your-docintel>.cognitiveservices.azure.com/"
AZURE_CLIENT_ID="<managed-identity-client-id>"
```

### Terraform Integration

The infrastructure already includes Document Intelligence service from the `ai_services` module:

```bash
cd terraform/ai_services
terraform output docintel_endpoint
terraform output aca_ai_services_identity_client_id
```

Use these outputs to configure the container app environment variables.

### Authentication

The app uses Azure Managed Identity for secure, keyless authentication:

1. **Managed Identity with Client ID** (Recommended for Azure)
   - Uses `AZURE_CLIENT_ID`
   - No keys or secrets needed
   - Best for production

2. **Default Azure Credential** (Fallback)
   - Uses managed identity, Azure CLI, environment variables, etc.
   - Good for local development and testing

## Testing

### Local Testing (Without Azure)

If Document Intelligence is not configured:
- Files are uploaded successfully
- Analysis is skipped with a warning message
- JSON files contain: `{"processed": false, "error": "Document Intelligence not configured"}`

### Local Testing (With Azure)

1. Set environment variables:
   ```bash
   export AZURE_DOCINTEL_ENDPOINT="https://your-service.cognitiveservices.azure.com/"
   # Authentication will use Azure CLI credentials or environment-based managed identity
   ```

2. Run the app:
   ```bash
   python app.py
   ```

3. Test with the script:
   ```bash
   python test_local.py sample.pdf sample.png
   ```

### Docker Testing

```bash
docker-compose up --build
```

Add environment variables to `docker-compose.yml`:
```yaml
environment:
  - AZURE_DOCINTEL_ENDPOINT=${AZURE_DOCINTEL_ENDPOINT}
  - AZURE_CLIENT_ID=${AZURE_CLIENT_ID}
```

## Usage Flow

1. **User uploads file(s)** via web interface or API
2. **App saves file** with timestamp prefix
3. **App processes file** with Document Intelligence (if supported type)
4. **App saves JSON** analysis alongside the file
5. **User receives response** with analysis summary
6. **User can retrieve** full JSON via `/analysis/<filename>` endpoint

## Next Steps (Future Enhancements)

1. **Database Integration**
   - Store analysis results in Cosmos DB or SQL Database
   - Enable querying and searching extracted data

2. **Background Processing**
   - Use Azure Service Bus or Storage Queue
   - Process large files asynchronously
   - Send notifications when complete

3. **Advanced Features**
   - Support custom Document Intelligence models
   - Batch processing
   - File comparison
   - OCR quality metrics

4. **Data Pipeline**
   - Stream to Azure Data Lake
   - Trigger Azure Functions
   - Power BI visualization

## Files Modified/Created

- ✏️ Modified: `requirements.txt`
- ✏️ Modified: `app.py`
- ✏️ Modified: `README.md`
- ✨ Created: `test_local.py`
- ✨ Created: `JSON_OUTPUT_REFERENCE.md`
- ✨ Created: `INTEGRATION_SUMMARY.md` (this file)

## References

- [Azure Document Intelligence](https://learn.microsoft.com/azure/ai-services/document-intelligence/)
- [Python SDK](https://learn.microsoft.com/python/api/azure-ai-formrecognizer/)
- [Managed Identity](https://learn.microsoft.com/azure/active-directory/managed-identities-azure-resources/)
