# File Upload Container App - Deployment Summary

## ✅ What Was Created

### 1. Application Source Code (`src/file-upload-app/`)

**Core Application:**
- `app.py` - Flask web application with file upload functionality
  - Modern HTML/CSS/JS frontend (embedded)
  - Multiple file upload with drag & drop
  - File validation (type and size)
  - Health check endpoint
  - Real-time upload feedback

**Containerization:**
- `Dockerfile` - Multi-stage container build
  - Based on Python 3.11 slim
  - Non-root user (security)
  - Health checks configured
  - Port 80 exposed
  
- `requirements.txt` - Python dependencies (Flask, Werkzeug)
- `.dockerignore` - Build optimization

**Local Testing:**
- `docker-compose.yml` - Local development setup
  - Port mapping (8080:80)
  - Volume mounts for uploads
  - Environment configuration

**Deployment Scripts:**
- `build.sh` - Build and push image to Azure Container Registry
- `deploy.sh` - Deploy/update app in Azure Container Apps
- `run-local.sh` - Quick local testing with Docker Compose
- `quick-deploy.sh` - Combined build + deploy

**Documentation:**
- `README.md` - Comprehensive app documentation

### 2. Infrastructure as Code Updates

**Terraform Configuration (`terraform/container_apps/`):**

Updated files:
- `main.tf` - Added new container app resource
  - ACR integration with managed identity
  - Internal ingress on port 80
  - Auto-scaling (1-3 replicas)
  - Environment variables configured
  
- `variables.tf` - Added new variables:
  - `acr_name` - Container Registry name
  - `app_file_upload_name` - App name
  - `file_upload_image_name` - Image name
  - `file_upload_image_tag` - Image tag
  
- `outputs.tf` - Added file upload app outputs:
  - App name, FQDN, URL
  - Container image reference
  - Log streaming command
  
- `terraform.tfvars` - Added configuration values
- `terraform.tfvars.example` - Updated example

### 3. Documentation

**New Documentation:**
- `src/README.md` - Container apps development guide
  - How to add new apps
  - Best practices
  - Common patterns
  - Troubleshooting
  
- `src/file-upload-app/README.md` - App-specific docs
  - Features and architecture
  - Deployment instructions
  - Configuration reference
  - Monitoring and logs

**Updated Documentation:**
- `README.md` - Added container apps section
  - Quick start guide
  - Deployment overview
  - Updated project structure

## 🚀 How to Use

### Option 1: Test Locally (Recommended First Step)

```bash
cd src/file-upload-app

# Start the app locally
./run-local.sh

# Open browser to http://localhost:8080
# Upload some files to test
# Press Ctrl+C to stop
```

### Option 2: Deploy to Azure (Full Deployment)

**Prerequisites:**
1. Infrastructure deployed (network + aca_env modules)
2. Azure CLI authenticated
3. Docker installed

**Steps:**

```bash
cd src/file-upload-app

# Option A: Quick deploy (build + deploy in one command)
./quick-deploy.sh

# Option B: Step-by-step
./build.sh   # Build and push to ACR
./deploy.sh  # Deploy to ACA

# Option C: Using Terraform
cd ../../terraform/container_apps
terraform apply
```

**Access the app:**

```bash
# Get the URL
cd terraform/container_apps
terraform output file_upload_app

# Or using Azure CLI
az containerapp show \
  --name aca-file-upload \
  --resource-group rg-foundry-sbx-app1 \
  --query properties.configuration.ingress.fqdn -o tsv
```

**Note:** The app uses internal ingress - you need VPN connection to access it.

## 📊 Infrastructure Components

### Container App Configuration

```yaml
Name: aca-file-upload
Environment: cae-foundry-sbx
Resource Group: rg-foundry-sbx-app1
```

**Compute:**
- CPU: 0.5 cores
- Memory: 1 GB
- Min Replicas: 1
- Max Replicas: 3

**Networking:**
- Ingress: Internal (VPN required)
- Port: 80
- Protocol: HTTP/Auto

**Identity:**
- Type: User Assigned Managed Identity
- Purpose: Pull images from ACR

**Container:**
- Image: `foundrysbxacr1.azurecr.io/file-upload-app:latest`
- Registry: Azure Container Registry (Private)
- Auth: Managed Identity (no credentials)

### Environment Variables

| Variable | Value | Purpose |
|----------|-------|---------|
| `PORT` | `80` | App listening port |
| `UPLOAD_FOLDER` | `/app/uploads` | Upload directory |
| `MAX_CONTENT_LENGTH` | `16777216` | Max file size (16MB) |

## 🔍 Monitoring

### View Logs

```bash
# Real-time logs
az containerapp logs show \
  --name aca-file-upload \
  --resource-group rg-foundry-sbx-app1 \
  --follow

# Or use Terraform output
cd terraform/container_apps
eval $(terraform output -json logs_commands | jq -r '.file_upload')
```

### Check Health

```bash
# Health endpoint
curl https://<app-fqdn>/health

# Expected response:
# {"status":"healthy","service":"file-upload-app"}
```

### View Replicas

```bash
az containerapp replica list \
  --name aca-file-upload \
  --resource-group rg-foundry-sbx-app1
```

## 🛠️ Common Tasks

### Update the Application

1. Modify `app.py` or other files
2. Test locally: `./run-local.sh`
3. Build and push: `./build.sh`
4. Deploy update: `./deploy.sh`

### Change Configuration

**Update environment variables:**

```bash
# Using Azure CLI
az containerapp update \
  --name aca-file-upload \
  --resource-group rg-foundry-sbx-app1 \
  --set-env-vars MAX_CONTENT_LENGTH=33554432

# Or update Terraform and apply
```

**Scale the app:**

```bash
# Using Azure CLI
az containerapp update \
  --name aca-file-upload \
  --resource-group rg-foundry-sbx-app1 \
  --min-replicas 0 \
  --max-replicas 5

# Or update Terraform main.tf
```

### Roll Back

```bash
# List revisions
az containerapp revision list \
  --name aca-file-upload \
  --resource-group rg-foundry-sbx-app1

# Activate previous revision
az containerapp revision activate \
  --name aca-file-upload \
  --resource-group rg-foundry-sbx-app1 \
  --revision <previous-revision-name>
```

## 🔐 Security Features

✅ **Non-root container** - Runs as user `appuser` (UID 1000)
✅ **Managed Identity** - No credentials in code or config
✅ **Internal ingress** - Not exposed to internet
✅ **Private ACR** - Registry only accessible via Private Endpoint
✅ **VNet isolation** - All traffic within Azure network
✅ **File validation** - Type and size checks
✅ **HTTPS only** - TLS termination at ingress

## 💰 Cost Estimate

**Container App:**
- Compute: ~$20-30/month (0.5 vCPU, 1GB RAM, 1-3 replicas)
- With scale-to-zero: ~$5-10/month

**Storage (uploads in container):**
- Ephemeral storage: Included
- For persistent storage: Add Azure Storage Blob (~$5-10/month)

**Total:** ~$25-40/month (excluding ACR and network costs)

## 📝 Next Steps

### Immediate

- [x] Application created and containerized
- [x] Local testing configured
- [x] Deployment scripts ready
- [x] Terraform updated
- [x] Documentation complete

### Suggested Enhancements

- [ ] Add authentication (Azure AD, API keys)
- [ ] Integrate Azure Storage Blob for persistent uploads
- [ ] Add file download/listing functionality
- [ ] Implement file scanning (anti-virus)
- [ ] Add metadata storage (database)
- [ ] Set up CI/CD pipeline (GitHub Actions)
- [ ] Add monitoring dashboard (Application Insights)
- [ ] Configure custom domain and certificates
- [ ] Add file retention policies
- [ ] Implement audit logging

### Production Readiness

- [ ] Enable scale-to-zero for cost savings
- [ ] Configure alerts and monitoring
- [ ] Set up backup and disaster recovery
- [ ] Implement rate limiting
- [ ] Add WAF/DDoS protection (if external)
- [ ] Security scanning in CI/CD
- [ ] Load testing
- [ ] Documentation for operations team

## 🐛 Troubleshooting

### Local Testing Issues

**Docker not found:**
```bash
# Install Docker or Docker Desktop
# Or run: docker --version
```

**Port 8080 in use:**
```bash
# Check what's using the port
lsof -i :8080

# Or change port in docker-compose.yml
```

### Deployment Issues

**ACR login fails:**
```bash
# Verify you're logged into Azure
az account show

# Login again
az login
```

**Image not found:**
```bash
# Verify image exists in ACR
az acr repository show \
  --name foundrysbxacr1 \
  --image file-upload-app:latest
```

**Container app crashes:**
```bash
# Check logs
az containerapp logs show \
  --name aca-file-upload \
  --resource-group rg-foundry-sbx-app1 \
  --follow
```

### Access Issues

**Can't reach the app:**
- Check VPN connection is active
- Verify app is running: `az containerapp show ...`
- Test internal DNS resolution
- Check ingress configuration

## 📚 Additional Resources

- [App README](README.md) - Detailed app documentation
- [Container Apps Guide](../README.md) - Development guide
- [Network README](../../terraform/network/README.md) - Network setup
- [Main README](../../README.md) - Overall project docs

---

**Created:** February 2026
**Infrastructure:** Enterprise Foundry Azure Container Apps
**Version:** 1.0
