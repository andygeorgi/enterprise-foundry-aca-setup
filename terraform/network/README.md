# Network Infrastructure - Hub & Spoke with VPN

Complete guide for deploying a hub-and-spoke network topology with Point-to-Site VPN connectivity for Azure Container Apps.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Configuration Scenarios](#configuration-scenarios)
3. [Quick Start](#quick-start)
4. [VPN Setup](#vpn-setup)
5. [Network Details](#network-details)
6. [Troubleshooting](#troubleshooting)
7. [Cost & Monitoring](#cost--monitoring)

---

## Architecture Overview

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

### IP Address Allocation

| Resource | CIDR | IP Range | Purpose |
|----------|------|----------|---------|
| Hub VNet | 10.0.0.0/16 | 10.0.0.0 - 10.0.255.255 | Central hub network |
| Gateway Subnet | 10.0.1.0/24 | 10.0.1.0 - 10.0.1.255 | VPN Gateway |
| Firewall Subnet | 10.0.2.0/24 | 10.0.2.0 - 10.0.2.255 | Azure Firewall (optional) |
| Sandbox VNet | 10.7.0.0/26 | 10.7.0.0 - 10.7.0.63 | ACA spoke network |
| ACA Subnet | 10.7.0.0/27 | 10.7.0.0 - 10.7.0.31 | ACA infrastructure |
| PE Subnet | 10.7.0.32/28 | 10.7.0.32 - 10.7.0.47 | Private endpoints |
| On-Prem VNet | 10.7.1.0/24 | 10.7.1.0 - 10.7.1.255 | On-prem simulation |
| VPN Clients | 172.16.0.0/24 | 172.16.0.0 - 172.16.0.255 | P2S VPN clients |

### Key Features

✅ **Hub-Spoke Topology** - Centralized gateway with spoke VNets  
✅ **Point-to-Site VPN** - Secure remote access via certificate auth  
✅ **Gateway Transit** - Spokes use hub's VPN gateway  
✅ **Private Endpoints** - ACR and Storage via private link  
✅ **Direct Peering** - Sandbox ↔ On-Prem for ACA traffic  
✅ **VNet Injection** - ACA environment with internal load balancer  

---

## Configuration Scenarios

### 🎯 Choose Your Deployment Model

| Scenario | When to Use | Monthly Cost | Deployment Time |
|----------|-------------|--------------|-----------------|
| **1. New Hub + VPN** | No existing hub, need remote access | ~$250 | 30-45 min |
| **2. New Hub, No VPN** | No existing hub, use Bastion/other | ~$30 | 5-10 min |
| **3. Existing Hub** | Have corporate hub VNet | ~$30 | 5-10 min |

### Scenario 1: New Hub with VPN Gateway (Default)

**Best For:** Complete new setup with remote access needs

```hcl
# terraform.tfvars
create_hub_vnet    = true
create_vpn_gateway = true

hub_vnet_name   = "vnet-hub-weu"
hub_vnet_prefix = "10.0.0.0/16"

vpn_gateway_sku          = "VpnGw1"
vpn_client_address_space = "172.16.0.0/24"
vpn_root_cert_data       = "MIID..."  # From certificate generation
```

**Resources Created:**
- ✅ Hub VNet with Gateway & Firewall subnets
- ✅ VPN Gateway with P2S configuration
- ✅ Public IP for VPN Gateway
- ✅ VNet peerings with gateway transit
- ✅ Spoke VNets (Sandbox & On-Prem Sim)

**Cost:** ~$250/month (mostly VPN Gateway)  
**Time:** 30-45 minutes (VPN Gateway provisioning)

---

### Scenario 2: New Hub WITHOUT VPN Gateway

**Best For:** Cost-optimized setup, using Azure Bastion or other access methods

```hcl
# terraform.tfvars
create_hub_vnet    = true
create_vpn_gateway = false

hub_vnet_name   = "vnet-hub-weu"
hub_vnet_prefix = "10.0.0.0/16"
```

**Resources Created:**
- ✅ Hub VNet with Gateway subnet (ready for future VPN)
- ✅ VNet peerings (without gateway transit)
- ✅ Spoke VNets
- ❌ No VPN Gateway (saves ~$150/month)

**Cost:** ~$30/month  
**Time:** 5-10 minutes

**💡 Tip:** Add VPN later by setting `create_vpn_gateway = true` and running `terraform apply`

---

### Scenario 3: Use Existing Hub VNet

**Best For:** Integration with existing corporate network infrastructure

```hcl
# terraform.tfvars
create_hub_vnet        = false
existing_hub_vnet_rg   = "rg-corp-network"
hub_vnet_name          = "vnet-corp-hub-prod"
```

**Resources Created:**
- ❌ No hub VNet (uses existing)
- ✅ Spoke VNets only
- ✅ Peerings to existing hub

**Requirements:**
- Hub VNet must already exist
- Permissions to create peerings on both sides
- For VPN access: existing hub must have VPN Gateway with gateway transit enabled

**Cost:** ~$30/month  
**Time:** 5-10 minutes

---

## Quick Start

### Prerequisites

- Azure subscription with Contributor access
- Azure CLI installed
- Terraform >= 1.5.0
- OpenSSL (for VPN certificate generation)

### 1. Configure Terraform

```bash
cd terraform/network
cp terraform.tfvars.example terraform.tfvars
nano terraform.tfvars
```

**Required Variables:**
```hcl
subscription_id      = "your-subscription-id"
location            = "swedencentral"
rg_net              = "rg-foundry-sbx-net"
rg_app              = "rg-foundry-sbx-app"

# Storage & Registry (must be globally unique, alphanumeric only)
storage_account_name = "foundrysbxstg1"
acr_name            = "foundrysbxacr1"

# Choose your scenario (1, 2, or 3)
create_hub_vnet     = true
create_vpn_gateway  = true  # false for Scenario 2
```

### 2. Deploy Infrastructure

```bash
terraform init
terraform plan
terraform apply
```

⏰ **Wait Time:**
- With VPN Gateway: 30-45 minutes
- Without VPN Gateway: 5-10 minutes

### 3. Verify Deployment

```bash
# Check outputs
terraform output hub_vnet_id
terraform output vpn_gateway_public_ip
terraform output sandbox_vnet_id
```

---

## VPN Setup

### Quick Setup (Automated)

For dev containers or Linux environments, use the automated setup script:

```bash
# 1. Generate certificates
./tools/generate_vpn_certificates.sh

# 2. Copy root cert data to terraform.tfvars and deploy
cd terraform/network
# Add vpn_root_cert_data = "..." to terraform.tfvars
terraform apply

# 3. Automated VPN client setup
cd /workspaces/enterprise-foundry-aca-setup
./tools/setup_vpn_client.sh

# 4. Connect
cd ~/OpenVPN && ./connect.sh
```

The **setup_vpn_client.sh** script automatically:
- ✅ Verifies prerequisites (Azure CLI, OpenSSL, OpenVPN)
- ✅ Checks certificates have correct Extended Key Usage
- ✅ Downloads VPN client configuration from Azure
- ✅ Configures OpenVPN with inline certificates
- ✅ Creates a quick connection helper script
- ✅ Validates TUN/TAP device availability

---

### Step 1: Generate VPN Certificates (2 minutes)

Use the helper script:

```bash
./tools/generate_vpn_certificates.sh
```

**What it does:**
1. Generates root certificate
2. Generates client certificate with proper Extended Key Usage
3. Displays root certificate data (base64 encoded)

**Save the output!** You'll need the base64 certificate data for Terraform.

**Manual Generation (OpenSSL):**
```bash
mkdir -p ~/vpn-certs && cd ~/vpn-certs

# Generate root certificate
openssl genrsa -out rootCA.key 4096
openssl req -x509 -new -nodes -key rootCA.key -sha256 -days 3650 \
  -out rootCA.crt -subj "/C=US/ST=State/L=City/O=MyOrg/CN=P2SRootCert"

# Export root cert for Azure (base64, no headers)
openssl x509 -in rootCA.crt -outform der | base64 -w 0 > rootCA.base64

# Create OpenSSL config for client cert with proper Extended Key Usage
cat > client_cert.cnf << 'EOF'
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req

[req_distinguished_name]

[v3_req]
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = clientAuth
EOF

# Generate client certificate with TLS Client Authentication EKU
openssl genrsa -out client.key 4096
openssl req -new -key client.key -out client.csr \
  -subj "/C=US/ST=State/L=City/O=MyOrg/CN=P2SClient" \
  -config client_cert.cnf
openssl x509 -req -in client.csr -CA rootCA.crt -CAkey rootCA.key \
  -CAcreateserial -out client.crt -days 365 -sha256 \
  -extensions v3_req -extfile client_cert.cnf

# Package for easy import
openssl pkcs12 -export -out client.p12 \
  -inkey client.key -in client.crt -certfile rootCA.crt

# Clean up
rm -f client_cert.cnf
```

> **Important:** The client certificate MUST include `extendedKeyUsage = clientAuth` or Azure VPN Gateway will reject the connection.

### Step 2: Add Certificate to Terraform (1 minute)

Edit `terraform.tfvars`:

```hcl
vpn_root_cert_data = "MIID...paste base64 cert here..."  # No BEGIN/END headers
```

Then apply:

```bash
terraform apply
```

### Step 3: Setup VPN Client (Automated - Recommended for Dev Containers)

**Option A: Automated setup script**

```bash
./tools/setup_vpn_client.sh
```

This downloads the VPN config, embeds your certificates, and creates a connection helper.

Then connect:
```bash
cd ~/OpenVPN && ./connect.sh
```

**Option B: Using helper script (manual download)**
```bash
./tools/vpn_helper.sh
# Choose option 2: Download VPN client configuration
```

**Option B: Using Azure CLI**
```bash
az network vnet-gateway vpn-client generate \
  --resource-group rg-foundry-sbx-net \
  --name vpngw-vnet-hub-weu \
  --processor-architecture Amd64
```

**Option C: Azure Portal**
1. Navigate to VPN Gateway
2. Click "Point-to-site configuration"
3. Click "Download VPN client"

### Step 4: Install Client Certificate (1 minute)

**macOS:**
```bash
security import ~/vpn-certs/client.p12 -k ~/Library/Keychains/login.keychain
```

**Linux:**
```bash
# Store path for VPN client configuration
echo ~/vpn-certs/client.p12
```

**Windows:**
```powershell
Import-PfxCertificate -FilePath "$env:USERPROFILE\vpn-certs\client.p12" `
  -CertStoreLocation "Cert:\CurrentUser\My"
```

### Step 5: Connect to VPN

**Dev Container / Linux (OpenVPN CLI - Recommended):**

If you used the automated setup script:
```bash
cd ~/OpenVPN && ./connect.sh
``` - Manual):**
```bash
cd ~/Downloads
unzip VpnClient.zip
cd OpenVPN

# Update config with certificates
sed -i '/<cert>/,/<\/cert>/d' vpnconfig.ovpn
sed -i '/<key>/,/<\/key>/d' vpnconfig.ovpn
echo "" >> vpnconfig.ovpn
echo "<cert>" >> vpnconfig.ovpn
cat ~/vpn-certs/client.crt >> vpnconfig.ovpn
echo "</cert>" >> vpnconfig.ovpn
ecIn a NEW terminal (keep OpenVPN running):

# Install ping if needed
sudo apt install iputils-ping

# Test 1: Ping on-prem simulation VM
ping 10.7.1.4

# Test 2: Test HTTP connection
curl http://10.7.1.4

# Test 3: Verify VPN interface
ip addr show tun0

# Test 4: Check VPN routes
ip route | grep tun0

# Test 5: SSH to VM (if configured)
ssh azureuser@10.7.1.4
```

**Using helper script:**
```bash
./tools/vpn_helper.sh
# Choose option 6: Test connectivity
```

### Dev Container VPN Support

The dev container is pre-configured with:
- **NET_ADMIN capability** - Required for creating VPN tunnel interfaces
- **/dev/net/tun device** - TUN/TAP device for VPN connections
- **OpenVPN client** - Auto-installed on container creation

If VPN fails with `Cannot open TUN/TAP dev`:
1. Rebuild the container: `Dev Containers: Rebuild Container`
2. Verify TUN device: `ls -la /dev/net/tun`
3. On host (if needed): `sudo modprobe tun Import the downloaded VPN configuration
3. Click "Connect"

**OpenVPN (Linux/macOS):**
```bash
cd ~/Downloads
unzip VpnClient.zip
sudo openvpn --config OpenVPN/vpnconfig.ovpn
```

**IKEv2 (Native):**
Extract VPN client ZIP and follow instructions in Generic or WindowsAmd64 folder.

### Step 6: Test Connectivity (1 minute)

```bash
# Ping on-prem simulation VM
ping 10.7.1.4

# Test HTTP connection
curl http://10.7.1.4

# SSH to VM (if configured)
ssh azureuser@10.7.1.4
```

**Using helper script:**
```bash
./tools/vpn_helper.sh
# Choose option 6: Test connectivity
```

---

## Network Details

### VNet Peering Configuration

All spoke VNets are peered to the hub with:
- **Gateway Transit:** Enabled on hub side
- **Use Remote Gateways:** Enabled on spoke side
- **Allow Forwarded Traffic:** Enabled both sides

**Direct Peering:** Sandbox ↔ On-Prem also have direct peering for optimized ACA-to-VM traffic.

### Private DNS Zones

1. **privatelink.blob.core.windows.net**
   - Linked to: Sandbox VNet
   - Purpose: Storage account private endpoint resolution
   - Example: `stfoundry123.blob.core.windows.net` → `10.7.0.35`

2. **privatelink.azurecr.io**
   - Linked to: Sandbox VNet
   - Purpose: ACR private endpoint resolution
   - Example: `acrfoundry123.azurecr.io` → `10.7.0.36`

### Network Security

**VPN Authentication:**
- Certificate-based (mutual TLS)
- Protocols: OpenVPN, IKEv2
- Strong encryption enforced by Azure
- Each client requires signed certificate

**Private Endpoints:**
- Storage Account: Public access disabled
- ACR: Public access disabled
- Access only via private endpoint IPs

### Routing Behavior

**VPN Client Effective Routes:**
- Hub VNet: 10.0.0.0/16
- Sandbox VNet: 10.7.0.0/26 (via peering)
- On-Prem VNet: 10.7.1.0/24 (via peering)

**ACA Effective Routes:**
- Local VNet: 10.7.0.0/26 (direct)
- Hub VNet: 10.0.0.0/16 (via peering)
- On-Prem VNet: 10.7.1.0/24 (direct or via hub)
- VPN Clients: 172.16.0.0/24 (via hub gateway)

---

## Troubleshooting

### VPN Connection Issues

**❌ "Connection failed" or "Authentication failed"**

**Cause:** Client certificate not installed or not found

**Solution:**
```bash
# macOS: Verify certificate is installed
security find-identity -v -p codesigning

# Windows: Check certificate store
Get-ChildItem -Path Cert:\CurrentUser\My

# Linux: Verify P12 file path
ls -la ~/vpn-certs/client.p12
```

---

**❌ "Cannot reach Azure resources" after connecting**

**Cause:** Routes not properly received or NSG blocking traffic

**Solution:**
```bash
# Check VPN routes
ip route show | grep vpn  # Linux/macOS
route print | findstr "10.0 10.7"  # Windows

# Verify gateway status
az network vnet-gateway show \
  --resource-group rg-foundry-sbx-net \
  --name vpngw-vnet-hub-weu \
  --query provisioningState
```

---

**❌ "Certificate validation failed"**

**Cause:** Client certificate not signed by configured root certificate

**Solution:**
```bash
# Regenerate client certificate with same root CA
./tools/vpn_helper.sh  # Option 5

# Verify certificate chain
openssl verify -CAfile ~/vpn-certs/rootCA.crt ~/vpn-certs/client.crt
```

---

### Terraform Errors

**❌ Invalid storage account name**

```
Error: name can only consist of lowercase letters and numbers
```

**Solution:** Storage account names must be 3-24 chars, lowercase and numbers only (no dashes)
```hcl
storage_account_name = "foundrysbxstg1"  # ✅ Valid
storage_account_name = "foundry-sbx-stg1"  # ❌ Invalid
```

---

**❌ Invalid ACR name**

```
Error: alpha numeric characters only are allowed
```

**Solution:** ACR names must be alphanumeric only (no dashes)
```hcl
acr_name = "foundrysbxacr1"  # ✅ Valid
acr_name = "foundry-sbx-acr1"  # ❌ Invalid
```

---

**❌ Undeclared variable warnings**

```
Warning: Value for undeclared variable "onprem_vnet_prefix"
```

**Solution:** Variable names in `terraform.tfvars` must match `variables.tf`:
```hcl
# ✅ Correct variable names
op_vnet_name    = "vnet-onprem-sim"
op_vnet_prefix  = "10.7.1.0/24"
vm_admin_username = "azureuser"
vm_size         = "Standard_B1s"

# ❌ Wrong variable names
onprem_vnet_name  = "..."
onprem_vm_admin   = "..."
```

---

## Cost & Monitoring

### Cost Breakdown

**Scenario 1: New Hub + VPN**
| Resource | Monthly Cost |
|----------|--------------|
| VPN Gateway (VpnGw1) | ~$150 |
| Public IP | ~$4 |
| VNet Peering | ~$10 |
| Storage Account | ~$20 |
| ACR (Basic) | ~$5 |
| **Total** | **~$250/month** |

**Scenario 2/3: No VPN**
| Resource | Monthly Cost |
|----------|--------------|
| VNet Peering | ~$10 |
| Storage Account | ~$20 |
| ACR (Basic) | ~$5 |
| **Total** | **~$30/month** |

### Cost Optimization Tips

1. **Development:** Use Scenario 2 (no VPN), add VPN only when needed
2. **Testing:** Delete VPN Gateway when not in use (saves ~$150/month)
   ```bash
   terraform destroy -target=azurerm_virtual_network_gateway.vpn
   terraform destroy -target=azurerm_public_ip.vpn_gateway
   ```
3. **Production:** Use VpnGw2/3 for better performance/reliability
4. **Scaling:** Consider ExpressRoute for > 10 users

### VPN Gateway Limits

| SKU | Max P2S Connections | Throughput |
|-----|---------------------|------------|
| VpnGw1 | 128 | 650 Mbps |
| VpnGw2 | 128 | 1 Gbps |
| VpnGw3 | 128 | 1.25 Gbps |
| VpnGw1AZ | 128 | 650 Mbps (zone-redundant) |

### Monitoring

**Key Metrics:**
- VPN Gateway: P2S connection count, bandwidth utilization
- VNet Peering: Bytes transferred
- Private Endpoints: Connection count

**Monitor with Azure CLI:**
```bash
# Check VPN connections
az network vnet-gateway list-vpn-client-sessions \
  --resource-group rg-foundry-sbx-net \
  --name vpngw-vnet-hub-weu

# Check gateway metrics
az monitor metrics list \
  --resource <vpn-gateway-id> \
  --metric "P2SConnectionCount"
```

---

## Common Operations

### Add VPN Gateway to Existing Hub

```bash
# 1. Generate certificates
./tools/generate_vpn_certificates.sh

# 2. Update terraform.tfvars
create_vpn_gateway = true
vpn_root_cert_data = "MIID..."

# 3. Apply (takes 30-45 min)
terraform apply
```

### Generate Additional Client Certificates

```bash
./tools/vpn_helper.sh
# Choose option 5: Generate new client certificate
```

Each device needs its own client certificate.

### Update VPN Root Certificate

```bash
# Azure Portal: VPN Gateway → Point-to-site configuration → Add certificate
# Or via Terraform: Update vpn_root_cert_data in terraform.tfvars
```

### Remove VPN Gateway (Save Costs)

```bash
terraform destroy -target=azurerm_virtual_network_gateway.vpn
terraform destroy -target=azurerm_public_ip.vpn_gateway
# Saves ~$150/month
```

---

## Next Steps

✅ **Network Deployed**  
➡️ [Deploy ACA Environment](../aca_env/)  
➡️ [Deploy Container Apps](../container_apps/)  
➡️ [Monitor Resources](../../tools/)  

## Additional Resources

- [Azure VPN Gateway Documentation](https://learn.microsoft.com/azure/vpn-gateway/)
- [Hub-Spoke Network Topology](https://learn.microsoft.com/azure/architecture/reference-architectures/hybrid-networking/hub-spoke)
- [Azure Container Apps VNet Integration](https://learn.microsoft.com/azure/container-apps/vnet-custom)
- [Private Link Documentation](https://learn.microsoft.com/azure/private-link/)

---

## Support

For issues or questions:
1. Check [Troubleshooting](#troubleshooting) section
2. Use helper scripts in `tools/` directory
3. Review Terraform outputs: `terraform output`
4. Check Azure Portal for resource status
