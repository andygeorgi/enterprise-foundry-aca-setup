# Enterprise Foundry - Container Apps Source

This directory contains source code for container applications that run in Azure Container Apps.

## Directory Structure

```
src/
├── file-upload-app/       # File upload web application
│   ├── app.py            # Flask application
│   ├── Dockerfile        # Container image
│   ├── docker-compose.yml # Local testing
│   ├── build.sh          # Build & push to ACR
│   ├── deploy.sh         # Deploy to ACA
│   └── README.md         # Detailed documentation
└── README.md             # This file
```

## Available Applications

### 1. File Upload App

A production-ready web application for uploading multiple files with a modern, user-friendly interface.

**Features:**
- Multiple file upload with drag & drop
- Real-time file validation
- Internal ingress (VNet-only access)
- Auto-scaling (1-3 replicas)
- Health monitoring

**Quick Start:**
```bash
# Option 1: Run in VS Code (with debugging)
# From workspace root, press F5 and select "File Upload App"

# Option 2: Run with Docker
cd src/file-upload-app
./run-local.sh              # Test locally
./build.sh                  # Build & push to ACR
./deploy.sh                 # Deploy to ACA
```

[See full documentation →](file-upload-app/README.md)

## Development Workflow

### Adding a New Container App

1. **Create app directory**:
   ```bash
   mkdir src/my-new-app
   cd src/my-new-app
   ```

2. **Add required files**:
   - Application code
   - `Dockerfile`
   - `requirements.txt` (or equivalent)
   - `docker-compose.yml` (for local testing)
   - `build.sh` (build & push script)
   - `deploy.sh` (deployment script)
   - `README.md` (documentation)

3. **Test locally**:
   ```bash
   docker-compose up --build
   ```

4. **Update Terraform**:
   
   Edit `terraform/container_apps/main.tf`:
   ```terraform
   resource "azurerm_container_app" "my_new_app" {
     name                         = var.app_my_new_name
     container_app_environment_id = data.azurerm_container_app_environment.aca_env.id
     resource_group_name          = var.rg_app
     revision_mode                = "Single"

     identity {
       type         = "UserAssigned"
       identity_ids = [data.azurerm_user_assigned_identity.aca_acr_pull.id]
     }

     registry {
       server   = data.azurerm_container_registry.acr.login_server
       identity = data.azurerm_user_assigned_identity.aca_acr_pull.id
     }

     ingress {
       external_enabled = false
       target_port      = 8080  # Your app's port
       transport        = "auto"

       traffic_weight {
         percentage      = 100
         latest_revision = true
       }
     }

     template {
       min_replicas = 1
       max_replicas = 3

       container {
         name   = "my-new-app"
         image  = "${data.azurerm_container_registry.acr.login_server}/my-new-app:latest"
         cpu    = 0.5
         memory = "1Gi"
       }
     }
   }
   ```

5. **Add variables** to `terraform/container_apps/variables.tf`:
   ```terraform
   variable "app_my_new_name" {
     type        = string
     description = "Name of my new container app"
     default     = "aca-my-new-app"
   }
   ```

6. **Add VS Code launch configuration** (`.vscode/launch.json`):
   ```json
   {
     "name": "My New App",
     "type": "debugpy",
     "request": "launch",
     "program": "${workspaceFolder}/src/my-new-app/app.py",
     "console": "integratedTerminal",
     "justMyCode": true,
     "env": {
       "PORT": "8080",
       // Add your environment variables
     },
     "cwd": "${workspaceFolder}/src/my-new-app",
     "preLaunchTask": "Create directories (my-new-app)"
   }
   ```

7. **Deploy**:
   ```bash
   ./build.sh
   ./deploy.sh
   ```

## Common Patterns

### Dockerfile Template

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["python", "app.py"]
```

### Docker Compose Template

```yaml
version: '3.8'

services:
  my-app:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: my-app
    ports:
      - "8080:8080"
    environment:
      - PORT=8080
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

### Build Script Template

```bash
#!/bin/bash
set -e

ACR_NAME="${ACR_NAME:-foundrysbxacr1}"
IMAGE_NAME="${IMAGE_NAME:-my-app}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
RESOURCE_GROUP="${RESOURCE_GROUP:-rg-foundry-sbx-app1}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🐳 Building Docker image..."
docker build -t "${IMAGE_NAME}:${IMAGE_TAG}" "$SCRIPT_DIR"

echo "🔐 Logging into ACR..."
az acr login --name "$ACR_NAME"

ACR_LOGIN_SERVER=$(az acr show --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" --query loginServer -o tsv)
FULL_IMAGE_NAME="${ACR_LOGIN_SERVER}/${IMAGE_NAME}:${IMAGE_TAG}"

echo "🏷️  Tagging image: ${FULL_IMAGE_NAME}"
docker tag "${IMAGE_NAME}:${IMAGE_TAG}" "$FULL_IMAGE_NAME"

echo "⬆️  Pushing to ACR..."
docker push "$FULL_IMAGE_NAME"

echo "✅ Successfully pushed: ${FULL_IMAGE_NAME}"
```

## Best Practices

### Security

- ✅ Use non-root containers (create dedicated user)
- ✅ Use managed identities for Azure service auth
- ✅ Keep base images updated
- ✅ Minimize attack surface (slim/alpine images)
- ✅ Use internal ingress unless public access required
- ✅ Implement health checks
- ✅ Validate all user inputs

### Performance

- ✅ Use multi-stage builds to reduce image size
- ✅ Leverage layer caching (COPY requirements before code)
- ✅ Configure appropriate CPU/memory limits
- ✅ Enable auto-scaling based on load
- ✅ Use connection pooling for databases
- ✅ Implement proper logging and monitoring

### Reliability

- ✅ Implement health check endpoints
- ✅ Handle graceful shutdown
- ✅ Use liveness and readiness probes
- ✅ Configure appropriate retry policies
- ✅ Implement circuit breakers for external dependencies
- ✅ Use structured logging (JSON)

### Cost Optimization

- ✅ Consider scale-to-zero for dev/test environments
- ✅ Right-size CPU and memory allocations
- ✅ Use consumption-based pricing
- ✅ Clean up unused images from ACR
- ✅ Monitor and optimize resource utilization

## Infrastructure Overview

All container apps run in the Enterprise Foundry infrastructure:

```
┌─────────────────────────────────────────────┐
│ Hub VNet (10.0.0.0/16)                     │
│ - VPN Gateway                              │
│ - Point-to-Site VPN                        │
└──────────────┬──────────────────────────────┘
               │ VNet Peering
┌──────────────▼──────────────────────────────┐
│ Sandbox VNet (10.7.0.0/26)                 │
│                                             │
│  ┌────────────────────────────────────┐    │
│  │ ACA Subnet (10.7.0.0/27)          │    │
│  │ - Container Apps Environment      │    │
│  │ - Internal Load Balancer          │    │
│  │ - Auto-scaling                    │    │
│  └────────────────────────────────────┘    │
│                                             │
│  ┌────────────────────────────────────┐    │
│  │ Private Endpoint Subnet           │    │
│  │ - ACR Private Endpoint            │    │
│  │ - Storage Private Endpoint        │    │
│  └────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
```

## Prerequisites

Before deploying container apps, ensure:

1. **Infrastructure deployed**:
   ```bash
   cd terraform/network && terraform apply
   cd terraform/aca_env && terraform apply
   ```

2. **Azure CLI authenticated**:
   ```bash
   az login
   az account set --subscription <subscription-id>
   ```

3. **Docker installed** (for local testing and builds)

4. **VPN configured** (for accessing internal apps)

## Troubleshooting

### Common Issues

**Image pull failures:**
- Verify managed identity has AcrPull role
- Check ACR name in configuration
- Ensure image exists in ACR

**App not accessible:**
- Verify VPN connection
- Check internal DNS resolution
- Confirm ingress configuration

**Build failures:**
- Check Docker daemon is running
- Verify Azure CLI is logged in
- Check ACR exists and is accessible

**Deployment failures:**
- Verify ACA environment exists
- Check resource quotas
- Review deployment logs

## Monitoring & Logs

### View container app logs:

```bash
# Using Azure CLI
az containerapp logs show \
  --name <app-name> \
  --resource-group rg-foundry-sbx-app1 \
  --follow

# Using Terraform output
cd terraform/container_apps
eval $(terraform output -json logs_commands | jq -r '.file_upload')
```

### Monitor metrics:

```bash
# View replicas
az containerapp replica list \
  --name <app-name> \
  --resource-group rg-foundry-sbx-app1

# View revisions
az containerapp revision list \
  --name <app-name> \
  --resource-group rg-foundry-sbx-app1
```

## Next Steps

- Add more container apps for different workloads
- Implement CI/CD pipelines (GitHub Actions, Azure DevOps)
- Add monitoring dashboards (Application Insights)
- Implement distributed tracing
- Add automated testing
- Configure custom domains and certificates

## Resources

- [Azure Container Apps Documentation](https://learn.microsoft.com/azure/container-apps/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Container Security Best Practices](https://learn.microsoft.com/azure/container-apps/security-baseline)
- [Enterprise Foundry Main README](../README.md)
