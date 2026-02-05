# Quick Start Guide - Document Intelligence Integration

## What's New?

Your file upload app now automatically analyzes documents using Azure Document Intelligence! 🎉

Upload PDFs or images, and the app will extract:
- ✅ Full text content
- ✅ Tables and their data
- ✅ Key-value pairs (form fields)
- ✅ Page layout information
- ✅ Structured JSON output for further processing

## Files You Need to Know About

1. **[INTEGRATION_SUMMARY.md](INTEGRATION_SUMMARY.md)** - Complete technical overview of all changes
2. **[JSON_OUTPUT_REFERENCE.md](JSON_OUTPUT_REFERENCE.md)** - JSON structure and usage examples
3. **[README.md](README.md)** - Full documentation with API reference
4. **[test_local.py](test_local.py)** - Testing script

## How It Works

```
User uploads file.pdf
     ↓
App saves to: 20260204_120000_file.pdf
     ↓
Azure Document Intelligence analyzes
     ↓
App saves to: 20260204_120000_file.pdf.analysis.json
     ↓
User sees: "✅ Analyzed - 3 pages, 2 tables, 15 key-value pairs"
```

## Quick Test (Local)

**Without Azure (basic upload only):**
```bash
cd src/file-upload-app

# Install dependencies
pip install -r requirements.txt

# Run app
python app.py

# Open browser: http://localhost:8080
```

**With Azure Document Intelligence:**
```bash
# Set endpoint (authentication uses Azure CLI or managed identity)
export AZURE_DOCINTEL_ENDPOINT="https://your-service.cognitiveservices.azure.com/"

# For local testing, make sure you're logged in with Azure CLI:
az login

# Run app
python app.py

# Test with script
python test_local.py sample.pdf
```

## Deployment to Azure

The infrastructure already has Document Intelligence configured!

**1. Get the endpoint and identity:**
```bash
cd terraform/ai_services
terraform output docintel_endpoint
terraform output aca_ai_services_identity_client_id
```

**2. Update Container App with environment variables:**

Add to your container app configuration:
```hcl
env {
  name  = "AZURE_DOCINTEL_ENDPOINT"
  value = "<output-from-step-1>"
}

env {
  name  = "AZURE_CLIENT_ID"
  value = "<identity-client-id-from-step-1>"
}
```

**3. Deploy:**
```bash
cd src/file-upload-app
./build.sh
./deploy.sh
```

## Example API Usage

**Upload a file:**
```bash
curl -X POST -F "files=@invoice.pdf" \
  https://aca-file-upload.internal/upload
```

**Response:**
```json
{
  "success": true,
  "uploaded": 1,
  "results": [
    {
      "filename": "20260204_120000_invoice.pdf",
      "processed": true,
      "pages": 2,
      "tables": 1,
      "key_value_pairs": 8,
      "json_file": "20260204_120000_invoice.pdf.analysis.json"
    }
  ]
}
```

**Get the analysis:**
```bash
curl https://aca-file-upload.internal/analysis/20260204_120000_invoice.pdf.analysis.json
```

**List all files:**
```bash
curl https://aca-file-upload.internal/files
```

## What Can You Do With The JSON?

The `.analysis.json` files contain all extracted data. Use them to:

1. **Store in a database** (Cosmos DB, SQL)
   ```python
   with open('file.pdf.analysis.json') as f:
       data = json.load(f)
   db.documents.insert(data)
   ```

2. **Search with AI Search**
   - Index the content field
   - Enable semantic search
   - Build a document search engine

3. **Extract specific data**
   ```python
   # Get all invoice amounts
   for kv in analysis['key_value_pairs']:
       if 'amount' in kv['key'].lower():
           print(f"Amount: {kv['value']}")
   ```

4. **Process tables**
   ```python
   # Convert tables to pandas DataFrame
   for table in analysis['tables']:
       df = table_to_dataframe(table)
       df.to_sql('invoices', connection)
   ```

5. **Trigger workflows**
   - Send to Azure Logic Apps
   - Process with Azure Functions
   - Queue for downstream systems

## Troubleshooting

**File uploads but shows "Not processed":**
- Check that AZURE_DOCINTEL_ENDPOINT is set
- Verify the file type (must be PDF, PNG, JPG, JPEG, TIFF, or BMP)
- Check app logs for authentication errors

**"Document Intelligence not configured":**
- Environment variable AZURE_DOCINTEL_ENDPOINT is missing
- Files will upload but won't be analyzed

**Authentication errors:**
- In Azure: Verify AZURE_CLIENT_ID is correct and managed identity is assigned
- Locally: Ensure you're logged in with `az login`
- Verify the identity has "Cognitive Services User" role on the Document Intelligence resource

## Next Steps

1. ✅ Test locally with sample files
2. ✅ Deploy to Azure Container Apps
3. ✅ Upload some test documents
4. ✅ Check the JSON output
5. 🔄 Build your data processing pipeline!

## Support

- 📖 Full docs: [README.md](README.md)
- 🔧 Technical details: [INTEGRATION_SUMMARY.md](INTEGRATION_SUMMARY.md)
- 📊 JSON reference: [JSON_OUTPUT_REFERENCE.md](JSON_OUTPUT_REFERENCE.md)
- 🧪 Testing: [test_local.py](test_local.py)

---

**Ready to get started? Upload a PDF and watch the magic happen! ✨**
