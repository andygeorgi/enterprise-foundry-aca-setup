# File Upload Container App

A simple, production-ready web application for uploading multiple files. This app runs in Azure Container Apps with internal ingress for secure, VNet-only access.

## Features

- 📁 **Multiple File Upload** - Drag & drop or click to select multiple files
- 🎨 **Modern UI** - Clean, responsive interface with real-time feedback
- 🔒 **Secure** - Internal ingress, non-root container, managed identity auth
- 📊 **File Management** - Preview selected files with size information
- ✅ **Validation** - File type and size validation before upload
- 🏥 **Health Checks** - Built-in health endpoint for monitoring

## Supported File Types

- Documents: txt, pdf, doc, docx
- Images: png, jpg, jpeg, gif
- Archives: zip
- Data: csv, json, xml

Maximum file size: **16MB per file**

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

### Option 1: Local Testing with VS Code (Recommended)

Run the application directly in VS Code with debugging support:

1. **Install Python dependencies:**
   ```bash
   cd src/file-upload-app
   
   # Create virtual environment (optional but recommended)
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

2. **Start debugging:**
   - Open the workspace root in VS Code
   - Press `F5` or click "Run and Debug"
   - Select "File Upload App" configuration
   - App will start on http://localhost:8080

3. **Benefits:**
   - Set breakpoints and debug
   - Auto-reload on file changes (Debug Mode)
   - Integrated terminal
   - Environment variables pre-configured
   - Launch configs available for all apps in the workspace

### Option 2: Local Testing with Docker Compose

Test the full containerized application:

```bash
cd src/file-upload-app

# Start the app
./run-local.sh

# Or manually with docker-compose
docker-compose up --build
```

The app will be available at: **http://localhost:8080**

Uploaded files are stored in `./uploads/` directory.

### Option 3: Deploy to Azure Container Apps

#### Prerequisites

1. **Infrastructure deployed** - Run terraform modules in order:
   ```bash
   # 1. Network module (creates ACR, VNet, etc.)
   cd terraform/network
   terraform init
   terraform apply

   # 2. ACA Environment module
   cd ../aca_env
   terraform init
   terraform apply

   # 3. Container Apps module (optional - for testing apps)
   cd ../container_apps
   terraform init
   # Don't apply yet - we need to build the image first
   ```

2. **Azure CLI logged in**:
   ```bash
   az login
   az account set --subscription <your-subscription-id>
   ```

#### Build and Push Container Image

```bash
cd src/file-upload-app

# Build and push to ACR (uses terraform.tfvars values)
./build.sh

# Or with custom values:
ACR_NAME=myacr IMAGE_NAME=file-upload-app IMAGE_TAG=v1.0 ./build.sh
```

#### Deploy Using Scripts

```bash
# Deploy the container app
./deploy.sh

# Or with custom values:
ACR_NAME=myacr APP_NAME=aca-file-upload ./deploy.sh
```

#### Deploy Using Terraform

```bash
cd terraform/container_apps

# Make sure terraform.tfvars has the correct ACR name
# and that you've pushed the image to ACR

terraform apply
```

After deployment, get the app URL:

```bash
terraform output file_upload_app
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `80` | Port the app listens on |
| `UPLOAD_FOLDER` | `/app/uploads` | Directory to store uploaded files |
| `MAX_CONTENT_LENGTH` | `16777216` | Max file size in bytes (16MB) |

### Terraform Variables

Configure in `terraform/container_apps/terraform.tfvars`:

```hcl
# ACR Configuration
acr_name = "foundrysbxacr1"

# File Upload App
app_file_upload_name     = "aca-file-upload"
file_upload_image_name   = "file-upload-app"
file_upload_image_tag    = "latest"
```

## Accessing the Application

The app uses **internal ingress** and is only accessible from within the VNet or via VPN.

### 1. Connect via VPN

If you deployed the hub VNet with VPN Gateway:

```bash
# Generate VPN client certificates (if not already done)
cd tools
./generate_vpn_certificates.sh

# Setup VPN client
./setup_vpn_client.sh
```

### 2. Get the App URL

```bash
cd terraform/container_apps
terraform output file_upload_app
```

Or via Azure CLI:

```bash
az containerapp show \
  --name aca-file-upload \
  --resource-group rg-foundry-sbx-app1 \
  --query properties.configuration.ingress.fqdn -o tsv
```

### 3. Access in Browser

Open the FQDN in your browser (ensure you're connected to VPN):

```
https://<app-fqdn>
```

## Monitoring

### View Logs

Using Terraform output:

```bash
cd terraform/container_apps
eval $(terraform output -raw logs_commands | jq -r '.file_upload')
```

Using Azure CLI directly:

```bash
az containerapp logs show \
  --name aca-file-upload \
  --resource-group rg-foundry-sbx-app1 \
  --follow
```

### Health Check

The app includes a health endpoint:

```bash
curl https://<app-fqdn>/health
```

Response:
```json
{
  "status": "healthy",
  "service": "file-upload-app"
}
```

## Development

### Project Structure

```
file-upload-app/
├── app.py                  # Flask application
├── requirements.txt        # Python dependencies
├── Dockerfile             # Container image definition
├── docker-compose.yml     # Local testing setup
├── .dockerignore          # Docker build exclusions
├── build.sh              # Build & push to ACR
├── deploy.sh             # Deploy to ACA
├── run-local.sh          # Local testing script
└── README.md             # This file
```

### Making Changes

1. **Edit the app**:
   ```bash
   # Modify app.py, requirements.txt, or Dockerfile
   ```

2. **Test locally**:
   ```bash
   ./run-local.sh
   # Or: docker-compose up --build
   ```

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

- [ ] Add authentication (Azure AD, Managed Identity)
- [ ] Integrate with Azure Storage Blob for persistent file storage
- [ ] Add file listing/download functionality
- [ ] Implement file scanning (anti-virus, malware detection)
- [ ] Add file metadata storage (database)
- [ ] Configure custom domain and certificates

## Support

For issues or questions:

1. Check the troubleshooting section above
2. Review application logs
3. Verify Azure resources are deployed correctly
4. Check network connectivity (VPN, DNS)

## License

Enterprise Foundry - Internal Use
