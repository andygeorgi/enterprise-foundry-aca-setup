# Enterprise Foundry - Azure Container Apps Sandbox Setup

A Terraform-based infrastructure setup for deploying Azure Container Apps (ACA) with hub-and-spoke network topology, VPN Gateway for Point-to-Site connectivity, VNet integration, private endpoints, and hybrid connectivity simulation.

## 🏗️ Architecture

![Architecture Diagram](architecture_diagram.svg)

### Components

| Component | Description |
|-----------|-------------|
| **Hub VNet** | Central hub network with VPN Gateway for Point-to-Site connectivity |
| **VPN Gateway** | Enables secure remote access from local machines to Azure resources |
| **Sandbox VNet** | Contains ACA environment with VNet injection (spoke) |
| **On-Prem Simulation VNet** | Ubuntu VM with nginx simulating on-premises servers (spoke) |
| **Azure Container Apps** | VNet-injected container environment with internal load balancer |
| **AI Services** | Document Intelligence + AI Search with Private Endpoints |
| **Azure AI Foundry** | AI Hub & Project with Managed VNet (Portal-deployed) |
| **Private Endpoints** | Secure access to Storage, ACR, Document Intelligence, AI Search |
| **Private DNS Zones** | DNS resolution for privatelink endpoints |
| **Hub-Spoke Peering** | All spokes peer to hub with gateway transit enabled |

## 🤖 Azure AI Foundry Setup (Portal)

Azure AI Foundry is deployed **manually via the Azure Portal** with a Managed VNet for network isolation. This allows AI Foundry to access the same AI Services (Document Intelligence, AI Search) that Container Apps access via Private Endpoints.

### Why Portal Deployment?

- **Managed VNet**: AI Foundry's Managed VNet is fully Azure-managed - no Terraform support
- **Auto Private Endpoints**: Creates its own private endpoints to connected services
- **Simplified Setup**: Portal wizard handles all networking complexity

### Setup Steps

1. **Navigate to AI Foundry**
   - Go to [ai.azure.com](https://ai.azure.com) or search "AI Foundry" in Azure Portal

2. **Create AI Hub**
   ```
   Name: hub-foundry-sbx
   Resource Group: rg-foundry-sbx-app
   Region: West Europe (same as other resources)
   
   Networking:
   ├── Network Isolation: Private with Internet Outbound
   ├── Workspace managed outbound access: Allow only approved outbound
   └── No private endpoint (uses Managed VNet instead)
   ```

3. **Create AI Project**
   ```
   Name: project-foundry-sbx
   Hub: hub-foundry-sbx (created above)
   ```

4. **Connect to AI Services**
   
   In the AI Hub settings, add connections to existing resources:
   ```
   Connections:
   ├── Document Intelligence: <your-docintel-name>
   ├── AI Search: <your-search-name>
   └── Storage Account: <your-storage-name>
   ```
   
   > AI Foundry automatically creates managed private endpoints to these services.

5. **Verify Connectivity**
   
   In the AI Project:
   - Open **Notebooks** or **Prompt Flow**
   - Test connection to Document Intelligence
   - Verify AI Search index access

### Architecture: Dual Access Pattern

Both **Container Apps** and **AI Foundry** can access the same AI Services:

```
┌─────────────────────────────┐     ┌─────────────────────────────┐
│      Container Apps         │     │      Azure AI Foundry       │
│     (Sandbox VNet)          │     │     (Managed VNet)          │
│                             │     │                             │
│  ┌─────────────────────┐    │     │  ┌─────────────────────┐    │
│  │  pe-docintel        │────┼─────┼──│  Auto PE (Managed)  │    │
│  │  pe-search          │────┼─────┼──│  Auto PE (Managed)  │    │
│  └─────────────────────┘    │     │  └─────────────────────┘    │
└─────────────────────────────┘     └─────────────────────────────┘
               │                                   │
               └───────────────┬───────────────────┘
                               ▼
                    ┌─────────────────────┐
                    │    AI Services      │
                    │  ┌───────────────┐  │
                    │  │ Doc Intel     │  │
                    │  │ AI Search     │  │
                    │  │ Storage       │  │
                    │  └───────────────┘  │
                    └─────────────────────┘
```

**Benefits:**
- 🔒 Both environments access services privately
- 🔄 Same data, different tools (code vs. no-code)
- 📊 Container Apps for production workloads
- 🧪 AI Foundry for experimentation and prompt engineering

### Network Topology

```
                      Your Local Machine
                      (192.168.x.x / 172.16.0.x)
                              │
                              │ P2S VPN
                              ▼
                    ┌─────────────────┐
                    │   VPN Gateway   │
                    │                 │
                    │    Hub VNet     │
                    │   10.0.0.0/16   │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │ VNet Peering │ VNet Peering │
              ▼  (Gateway    │  (Gateway    ▼
    ┌─────────────────┐      │  Transit)   ┌─────────────────┐
    │  Sandbox VNet   │◄─────┴────►│  On-Prem Sim    │
    │  10.7.0.0/26    │  Direct    │  10.7.1.0/24    │
    │                 │  Peering   │                 │
    │  ┌───────────┐  │            │  ┌───────────┐  │
    │  │ ACA Env   │  │            │  │ Ubuntu VM │  │
    │  │ /27 subnet│  │            │  │  nginx    │  │
    │  └───────────┘  │            │  └───────────┘  │
    │  ┌───────────┐  │            └─────────────────┘
    │  │    PEs    │  │
    │  │ /28 subnet│  │
    │  └───────────┘  │
    └─────────────────┘
```

> **Key Features**:
> - **Point-to-Site VPN**: Connect your local machine securely to Azure networks
> - **Hub-Spoke Topology**: Centralized gateway with spoke VNets for workloads
> - **Gateway Transit**: Spokes use the hub's VPN gateway for remote connectivity
> - **Direct Peering**: Sandbox and On-Prem VNets also have direct peering for ACA connectivity

For detailed architecture and network setup information, see [Network README](terraform/network/README.md).

## 📋 Prerequisites

- Azure subscription with Owner/Contributor access
- WSL2 (Ubuntu) or Linux environment
- Azure CLI
- Terraform >= 1.5.0
- OpenSSL (for VPN certificate generation)

### Install Prerequisites

```bash
./00_install_prerequisites.sh
```

This script installs or upgrades:
- Azure CLI
- Terraform

## 🐳 Development Container

This project includes a **VS Code Dev Container** for a consistent development experience with all tools pre-installed.

### Quick Start with Devcontainer

1. **Open in VS Code** with [Remote - Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) extension
2. Click **"Reopen in Container"** when prompted (or `F1` → "Dev Containers: Reopen in Container")
3. Wait for container to build (~2-3 minutes first time)

### Included Tools

| Tool | Purpose |
|------|--------|
| **Terraform** | Infrastructure deployment |
| **Azure CLI** | Azure authentication & management |
| **OpenVPN** | VPN connectivity from container |
| **Git** | Version control |
| **Zsh + Oh My Zsh** | Enhanced shell experience |

### VS Code Extensions (Auto-installed)

- HashiCorp Terraform
- Azure Terraform
- Azure CLI Tools
- GitHub Copilot

### VPN from Devcontainer

The devcontainer is pre-configured for Point-to-Site VPN:

```bash
# Setup VPN client (one-time)
./tools/setup_vpn_client.sh

# Connect to VPN
./tools/vpn_helper.sh connect

# Check status
./tools/vpn_helper.sh status
```

> **Note**: Requires `--privileged` mode (already configured in devcontainer.json)

## 🔐 VPN Setup (Point-to-Site Connectivity)

The infrastructure supports **flexible hub VNet configuration**:

**Option 1: Create New Hub with VPN** (Default)
- Creates hub VNet with VPN Gateway
- Cost: ~$250/month
- Deployment: 30-45 minutes

**Option 2: Create New Hub without VPN**
- Creates hub VNet only (no VPN Gateway)
- Cost: ~$30/month (saves $150+/month)
- Add VPN later if needed

**Option 3: Use Existing Hub VNet**
- Connect to your existing corporate hub
- Cost: ~$30/month (peering only)
- Reuse existing VPN/ExpressRoute

See [Network README - Configuration Scenarios](terraform/network/README.md#configuration-scenarios) for detailed scenarios.

### Quick VPN Setup (Option 1)

1. **Generate VPN Certificates**:
   ```bash
   ./tools/generate_vpn_certificates.sh
   ```
   This creates the necessary certificates in `~/vpn-certs/` and displays the root certificate data.

2. **Configure Terraform**:
   ```bash
   cd terraform/network
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars:
   #   create_hub_vnet = true
   #   create_vpn_gateway = true
   #   vpn_root_cert_data = "MIID..."
   ```

3. **Deploy the Infrastructure** (VPN Gateway takes 30-45 minutes)
   ```bash
   terraform init
   terraform apply
   ```

4. **Connect to VPN** - See [Network README - VPN Setup](terraform/network/README.md#vpn-setup)

### What You Can Access via VPN

Once connected to the VPN:
- ✅ Access resources in all VNets (Hub, Sandbox, On-Prem Simulation)
- ✅ SSH to the on-premises simulation VM
- ✅ Access private endpoints (Storage, ACR)
- ✅ Connect to internal Container Apps
- ✅ Troubleshoot network connectivity issues

## 🚀 Quick Start

### 1. Clone and Configure

```bash
git clone <repository-url>
cd enterprise-foundry-aca-setup

# Copy example configs and customize
cp terraform/network/terraform.tfvars.example terraform/network/terraform.tfvars
cp terraform/aca_env/terraform.tfvars.example terraform/aca_env/terraform.tfvars
cp terraform/ai_services/terraform.tfvars.example terraform/ai_services/terraform.tfvars
cp terraform/container_apps/terraform.tfvars.example terraform/container_apps/terraform.tfvars

# Edit each terraform.tfvars with your values
```

### 2. Login to Azure

```bash
az login
az account set --subscription "<your-subscription-id>"
```

### 3. Deploy Infrastructure

Use the interactive Terraform executor:

```bash
./01_terraform.sh
```

**Menu options:**
- `1-4` - Toggle module selection
- `a` - Select all modules
- `p` - Plan (preview changes)
- `d` - Deploy selected modules
- `x` - Destroy selected modules
- `q` - Quit

**Deployment order** (handled automatically):
1. `network` - VNets, VMs, Storage, ACR, Private Endpoints
2. `aca_env` - Azure Container Apps Environment
3. `ai_services` - Document Intelligence, AI Search, Private Endpoints
4. `container_apps` - Test container applications

## 📚 Documentation

For detailed guides and references:

- **[Network Infrastructure Guide](terraform/network/README.md)** - Complete hub-and-spoke network setup, VPN configuration, troubleshooting
- **[VPN & Tools Guide](tools/README.md)** - VPN client setup, helper scripts, troubleshooting
- **[Container Apps Guide](src/README.md)** - Building and deploying container applications
- **Architecture Diagrams** - See above and `architecture_diagram.svg`
- **Terraform Examples** - See `terraform.tfvars.example` in each module

## 📁 Project Structure

```
enterprise-foundry-aca-setup/
├── .devcontainer/                  # VS Code Dev Container configuration
│   └── devcontainer.json           # Container settings, tools, VPN support
├── 00_install_prerequisites.sh     # Install Azure CLI + Terraform
├── 01_terraform.sh                 # Interactive deployment script
├── architecture_diagram.svg        # Visual architecture diagram
├── src/                            # Container application source code
│   ├── README.md                   # Container apps development guide
│   └── file-upload-app/            # File upload web application
│       ├── app.py                  # Flask application
│       ├── Dockerfile              # Container image
│       ├── docker-compose.yml      # Local testing
│       ├── build.sh                # Build & push to ACR
│       ├── deploy.sh               # Deploy to ACA
│       └── README.md               # App documentation
├── terraform/
│   ├── network/                    # Core networking infrastructure
│   │   ├── README.md               # ⭐ Complete network setup guide
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── terraform.tfvars.example
│   ├── aca_env/                    # Container Apps Environment
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── terraform.tfvars.example
│   ├── ai_services/                # AI Services (Doc Intel, AI Search)
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── terraform.tfvars.example
│   └── container_apps/             # Test container applications
│       ├── main.tf
│       ├── variables.tf
│       ├── outputs.tf
│       └── terraform.tfvars.example
└── tools/
    ├── README.md                   # Tools documentation
    ├── generate_vpn_certificates.sh # VPN certificate generation
    ├── setup_vpn_client.sh         # Automated VPN client setup
    ├── vpn_helper.sh               # VPN management & diagnostics
    ├── monitor_onprem.sh           # Monitor VM connectivity test
    ├── monitor_storage.sh          # Monitor storage PE test
    └── generate_architecture_diagram.sh
```

## 🧪 Connectivity Tests

The `container_apps` module deploys two test applications:

### On-Prem Connectivity Test

Tests HTTP connectivity from ACA to the simulated on-premises VM.

```bash
./tools/monitor_onprem.sh
```

**Output:**
```
✅ [2024-01-30 12:00:00] onprem 10.7.1.4 port 80 TCP=FAIL HTTP=OK
✅ [2024-01-30 12:00:00] onprem 10.7.1.4 port 443 TCP=FAIL HTTP=OK
```

> **Note:** Only HTTP connectivity is tested (not raw TCP sockets). This is intentional - the test uses `curl` to verify HTTP-level connectivity, which is the typical use case for container apps communicating with backend services. The `TCP=FAIL` is expected because Alpine's `/dev/tcp` isn't available; the `HTTP=OK` confirms actual connectivity works.

### Storage Private Endpoint Test

Tests connectivity to Azure Storage via Private Endpoint using managed identity.

```bash
./tools/monitor_storage.sh
```

**Output:**
```
✅ [2024-01-30 12:00:00] Storage: mystorageaccount.blob.core.windows.net
   Private IP: 10.7.0.36 | Response: 299 bytes
```

## � Container Applications

The `src/` directory contains production-ready container applications that run in Azure Container Apps.

### File Upload App

A web application for uploading multiple files with a modern, responsive interface.

**Features:**
- 📁 Multiple file upload with drag & drop
- 🎨 Modern, responsive UI
- 🔒 Internal ingress (VPN-only access)
- 📊 Real-time file validation
- ⚡ Auto-scaling (1-3 replicas)

**Quick Start:**

```bash
# Test locally
cd src/file-upload-app
./run-local.sh

# Access at http://localhost:8080
```

**Deploy to Azure:**

```bash
# 1. Build and push to ACR
./build.sh

# 2. Deploy to Container Apps
./deploy.sh

# 3. Or use Terraform
cd ../../terraform/container_apps
terraform apply
```

**Access the app:**

```bash
# Get the URL (requires VPN connection)
cd terraform/container_apps
terraform output file_upload_app
```

See [Container Apps Development Guide](src/README.md) for detailed documentation and how to add more apps.

## �🔧 Configuration Reference

### Required Variables

| Module | Variable | Description |
|--------|----------|-------------|
| All | `subscription_id` | Azure Subscription ID |
| All | `location` | Azure region (e.g., westeurope) |
| All | `rg_net` | Network resource group name |
| All | `rg_app` | Application resource group name |
| network | `storage_account_name` | Globally unique storage account name |
| network | `acr_name` | Globally unique container registry name |
| aca_env | `vnet_name` | Sandbox VNet name (from network module) |
| aca_env | `subnet_aca` | ACA subnet name (from network module) |
| ai_services | `docintel_name` | Globally unique Document Intelligence name |
| ai_services | `search_name` | Globally unique AI Search name |
| container_apps | `aca_env_name` | ACA environment name (from aca_env module) |
| container_apps | `storage_account_name` | Storage account name (from network module) |

### Network Address Spaces

| Network | CIDR | Purpose |
|---------|------|---------|
| Hub VNet | 10.0.0.0/16 | Corporate hub simulation |
| Sandbox VNet | 10.7.0.0/26 | ACA workloads |
| └─ ACA Subnet | 10.7.0.0/27 | Container Apps (min /27 required) |
| └─ PE Subnet | 10.7.0.32/28 | Private Endpoints |
| On-Prem VNet | 10.7.1.0/24 | On-premises simulation |

## 🗑️ Cleanup

Destroy in reverse order:

```bash
./01_terraform.sh
# Select modules in reverse order: container_apps → aca_env → network
# Press 'x' to destroy
```

Or manually:

```bash
cd terraform/container_apps && terraform destroy
cd ../aca_env && terraform destroy
cd ../network && terraform destroy
```

> **Note**: ACA environment deletion can take 15-30 minutes due to Azure internal cleanup processes.

## ⚠️ Important Notes

### VNet Peering is Non-Transitive

Azure VNet peering does not allow transitive routing. If you have:
- Hub ↔ Sandbox (peered)
- Hub ↔ On-Prem (peered)

Traffic from Sandbox **cannot** reach On-Prem via Hub. You need **direct peering** between Sandbox and On-Prem VNets.

### ACA Subnet Requirements

- Minimum subnet size: **/27** (32 addresses)
- Must be delegated to `Microsoft.App/environments`
- Cannot be shared with other resources

### Managed Identity in ACA

Container Apps use a different token endpoint than VMs:
- ❌ `169.254.169.254` (VM metadata endpoint - doesn't work)
- ✅ `$IDENTITY_ENDPOINT` with `$IDENTITY_HEADER` (ACA environment variables)

## 📄 License

MIT License - feel free to use and modify for your projects.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

---

**Built with** ❤️ **using Terraform and Azure**
