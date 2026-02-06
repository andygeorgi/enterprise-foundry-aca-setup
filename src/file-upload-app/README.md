# File Upload App (Azure Document Intelligence)

Upload files and (optionally) analyze PDFs and images with Azure Document Intelligence. Runs locally via Docker Compose or in Azure Container Apps with internal ingress.

## Architecture

```
┌─────────────┐
│   Browser   │
│  (via VPN)  │
└──────┬──────┘
  │ HTTPS
  │ Internal Ingress
┌──────▼──────────────────────┐
│  Azure Container Apps       │
│  ┌──────────────────────┐   │
│  │  File Upload App     │   │
│  │  - Flask (Python)    │   │
│  │  - Port 80           │   │
│  │  - 1-3 replicas      │   │
│  └──────────────────────┘   │
│          ▲                  │
│          │ Pull Image       │
│  ┌───────┴──────────────┐   │
│  │ Managed Identity     │   │
│  │ (ACR Pull)           │   │
│  └──────────────────────┘   │
└─────────────────────────────┘
  ▲
  │
┌──────┴───────────────────┐
│ Azure Container Registry │
│ (Private Endpoint)       │
└──────────────────────────┘
```

## Quick Start

### Local (Docker Compose)

```bash
cd src/file-upload-app
./run-local.sh
```

Open http://localhost:8080

### Local (Python)

```bash
cd src/file-upload-app
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

### Azure (build + deploy)

```bash
cd src/file-upload-app
./build.sh
./deploy.sh
```

## Configure Document Intelligence

Set environment variables for analysis:

```bash
export AZURE_DOCINTEL_ENDPOINT="https://<your-docintel>.cognitiveservices.azure.com/"
export AZURE_CLIENT_ID="<managed-identity-client-id>"
```

If `AZURE_DOCINTEL_ENDPOINT` is not set, files are uploaded but not analyzed.

## API

- `GET /` UI
- `POST /upload` upload and analyze
- `GET /analysis/<filename>` retrieve analysis JSON
- `GET /files` list uploads
- `GET /health` health check

### Example Upload

```bash
curl -X POST -F "files=@invoice.pdf" http://localhost:8080/upload
```

## Analysis Output (Summary)

Each analyzed file produces `*.analysis.json` containing:

```json
{
  "processed": true,
  "model_id": "prebuilt-document",
  "content": "...",
  "pages": [],
  "tables": [],
  "key_value_pairs": [],
  "paragraphs": []
}
```

Supported analysis types: PDF, PNG, JPG, JPEG, TIFF, BMP. Max file size: 16MB.

## Scripts

- `run-local.sh` start local Docker Compose
- `build.sh` build and push to ACR
- `deploy.sh` deploy to Container Apps
- `quick-deploy.sh` build + deploy
- `generate-env.sh` helper for `.env`

## Notes

- Internal ingress means VPN/VNet access is required in Azure.
- Logs: `az containerapp logs show --name <app> --resource-group <rg> --follow`

3. **Build and push**:
   ```bash
   ./build.sh
   ```

4. **Deploy update**:
   ```bash
   # Option A: Using script
   ./deploy.sh

   # Option B: Using terraform
   cd ../../terraform/container_apps
   terraform apply
   ```

### Adding New Container Apps

This `src/` folder is designed to hold multiple container apps. To add a new app:

1. Create a new directory: `src/my-new-app/`
2. Add your application code, Dockerfile, and scripts
3. Update `terraform/container_apps/main.tf` to add the new container app resource
4. Follow the same build/deploy pattern

## Troubleshooting

### Can't access the app

- ✅ Ensure you're connected to the VPN
- ✅ Check the app is running: `az containerapp show -n aca-file-upload -g rg-foundry-sbx-app1`
- ✅ Verify internal DNS resolution from VPN client

### Image pull failures

- ✅ Verify managed identity has AcrPull role on ACR
- ✅ Check ACR name matches in terraform.tfvars
- ✅ Ensure image exists in ACR: `az acr repository show -n foundrysbxacr1 --image file-upload-app:latest`

### Upload failures

- ✅ Check file size is under 16MB
- ✅ Verify file type is in allowed list
- ✅ Check app logs for errors

### Local testing issues

- ✅ Ensure Docker is running
- ✅ Port 8080 is not in use: `lsof -i :8080`
- ✅ Check docker-compose logs: `docker-compose logs -f`

## Security Considerations

- ✅ **Internal ingress only** - Not exposed to internet
- ✅ **Non-root container** - Runs as user `appuser` (UID 1000)
- ✅ **Managed identity** - No credentials in code
- ✅ **File validation** - Type and size checks
- ✅ **Private ACR** - Registry accessible via Private Endpoint only
- ✅ **VNet isolation** - All traffic stays within Azure network

## Cost Optimization

The app is configured for cost efficiency:

- **Min replicas**: 1 (can be set to 0 for scale-to-zero)
- **Max replicas**: 3 (auto-scales based on load)
- **CPU**: 0.5 cores
- **Memory**: 1 GB

To enable scale-to-zero:

```terraform
template {
  min_replicas = 0  # Change from 1 to 0
  max_replicas = 3
  # ...
}
```

## Next Steps

- [x] ✅ Integrate Azure Document Intelligence for document analysis
- [x] ✅ Extract and save JSON analysis results
- [ ] Store analysis results in Azure Cosmos DB or SQL Database
- [ ] Implement background processing queue (Azure Service Bus/Storage Queue)
- [ ] Add Azure Storage Blob for persistent file storage
- [ ] Build downstream processing pipelines for extracted data
- [ ] Add authentication (Azure AD, Managed Identity)
- [ ] Implement file listing/download functionality
- [ ] Add file scanning (anti-virus, malware detection)
- [ ] Configure custom domain and certificates

## Support

For issues or questions:

1. Check the troubleshooting section above
2. Review application logs
3. Verify Azure resources are deployed correctly
4. Check network connectivity (VPN, DNS)

## License

Enterprise Foundry - Internal Use
