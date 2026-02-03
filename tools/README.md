# Helper Tools

This directory contains helper scripts for managing Azure infrastructure and VPN connectivity.

## VPN Management Scripts

### generate_vpn_certificates.sh

Generates certificates required for Point-to-Site VPN authentication.

**Usage:**
```bash
./tools/generate_vpn_certificates.sh
```

**What it creates:**
- `~/vpn-certs/rootCA.crt` - Root certificate
- `~/vpn-certs/rootCA.key` - Root private key (keep secure!)
- `~/vpn-certs/rootCA.base64` - Root certificate for Azure (use in terraform.tfvars)
- `~/vpn-certs/client.crt` - Client certificate with TLS Client Authentication EKU
- `~/vpn-certs/client.key` - Client private key
- `~/vpn-certs/client.p12` - Client certificate bundle (for installation)

**Key Features:**
- Generates certificates with proper Extended Key Usage (`clientAuth`)
- Creates 4096-bit RSA keys for enhanced security
- Root certificate valid for 10 years, client for 1 year
- PKCS#12 bundle for easy certificate installation

---

### setup_vpn_client.sh

**Automated VPN client setup script** - downloads VPN config and configures OpenVPN.

**Usage:**
```bash
# After generating certificates and deploying with Terraform
./tools/setup_vpn_client.sh
```

**What it does:**
1. ✅ Verifies prerequisites (Azure CLI, OpenSSL, OpenVPN)
2. ✅ Checks certificates exist and have correct Extended Key Usage
3. ✅ Regenerates client cert if missing proper EKU
4. ✅ Authenticates to Azure (prompts if needed)
5. ✅ Downloads VPN client configuration package
6. ✅ Embeds certificates inline in VPN config
7. ✅ Disables file logging (shows output in terminal)
8. ✅ Validates TUN/TAP device availability
9. ✅ Creates `~/OpenVPN/connect.sh` helper script

**After running:**
```bash
# Quick connect
cd ~/OpenVPN && ./connect.sh

# Or manual connect
cd ~/OpenVPN/OpenVPN
sudo openvpn --config vpnconfig.ovpn --verb 3
```

---

### vpn_helper.sh

Interactive menu-driven VPN management tool.

**Usage:**
```bash
./tools/vpn_helper.sh
```

**Features:**
- 1️⃣ Check VPN Gateway status
- 2️⃣ Download VPN client configuration
- 3️⃣ List active VPN connections
- 4️⃣ Show VPN Gateway details
- 5️⃣ Generate additional client certificates
- 6️⃣ Test connectivity to Azure resources
- 7️⃣ Show expected VPN client routes
- 8️⃣ Exit

**Generate additional client certificates:**
Each device should have its own client certificate. Use option 5 to generate certificates for additional devices (laptop, phone, tablet, etc.).

---

## Monitoring Scripts

### monitor_onprem.sh

Monitors connectivity between Azure Container Apps and the on-premises simulation VM.

**Usage:**
```bash
./tools/monitor_onprem.sh
```

**What it monitors:**
- HTTP connectivity from ACA to on-prem VM (port 80)
- HTTPS connectivity from ACA to on-prem VM (port 443)
- Response times and status codes
- Logs output with timestamps

---

### monitor_storage.sh

Monitors connectivity from Azure Container Apps to Storage Account via Private Endpoint.

**Usage:**
```bash
./tools/monitor_storage.sh
```

**What it monitors:**
- Private endpoint DNS resolution
- Storage account accessibility via private IP
- Blob container listing (using managed identity)
- Response times and blob counts

---

## Other Tools

### generate_architecture_diagram.sh

Generates architecture diagram (if GraphViz/diagram tools are available).

**Usage:**
```bash
./tools/generate_architecture_diagram.sh
```

---

## Common Workflows

### Initial Setup

```bash
# 1. Generate VPN certificates
./tools/generate_vpn_certificates.sh

# 2. Add certificate to terraform.tfvars
cat ~/vpn-certs/rootCA.base64
# Copy output to: vpn_root_cert_data = "..."

# 3. Deploy infrastructure
cd terraform/network
terraform apply

# 4. Setup VPN client
cd /workspaces/enterprise-foundry-aca-setup
./tools/setup_vpn_client.sh

# 5. Connect to VPN
cd ~/OpenVPN && ./connect.sh
```

### Daily Use

```bash
# Connect to VPN
cd ~/OpenVPN && ./connect.sh

# In another terminal - test connectivity
ping 10.7.1.4
curl http://10.7.1.4

# Check VPN status
./tools/vpn_helper.sh  # Option 1

# Monitor resources
./tools/monitor_onprem.sh
./tools/monitor_storage.sh
```

### Generate Certificate for New Device

```bash
./tools/vpn_helper.sh
# Select option 5: Generate new client certificate
# Enter device name (e.g., "laptop", "phone")
# Copy the generated .p12 file to the device
```

---

## Troubleshooting

### VPN Connection Issues

**Problem:** `Cannot open TUN/TAP dev /dev/net/tun`

**Solution:**
```bash
# Check if device exists
ls -la /dev/net/tun

# If missing, rebuild dev container
# VS Code: F1 → Dev Containers: Rebuild Container

# On host (if needed)
sudo modprobe tun
```

---

**Problem:** Connection reset after certificate verification

**Solution:** Root certificate in Azure doesn't match the one that signed your client certificate.

```bash
# Update root certificate in Azure
./tools/setup_vpn_client.sh  # Will detect and fix

# Or manually update via Terraform
cd terraform/network
# Update vpn_root_cert_data in terraform.tfvars
terraform apply
```

---

**Problem:** No output when running OpenVPN

**Solution:** Output is being logged to file instead of terminal.

```bash
# Disable file logging
cd ~/OpenVPN/OpenVPN
sed -i 's/^log openvpn.log/#log openvpn.log/' vpnconfig.ovpn

# Then connect
sudo openvpn --config vpnconfig.ovpn --verb 3
```

---

## Security Notes

- 🔐 **Keep `rootCA.key` secure** - This can generate unlimited client certificates
- 🔐 **Each device should have its own client certificate** - Don't share .p12 files
- 🔐 **P12 files are password protected** - Use strong passwords
- 🔐 **Rotate certificates periodically** - Client certs valid for 1 year
- 🔐 **Revoke compromised certificates** - Remove from Azure VPN Gateway

---

## Files Created by Scripts

### Certificate Generation
- `~/vpn-certs/` - All VPN certificates and keys

### VPN Client Setup
- `~/VpnClient.zip` - Downloaded VPN client package
- `~/OpenVPN/` - Extracted VPN configuration
- `~/OpenVPN/OpenVPN/vpnconfig.ovpn` - OpenVPN configuration file
- `~/OpenVPN/connect.sh` - Quick connection script

---

## Requirements

All scripts require:
- Azure CLI (`az`)
- OpenSSL
- Bash shell
- Active Azure subscription

VPN scripts additionally require:
- OpenVPN client (`openvpn`)
- TUN/TAP kernel support
- NET_ADMIN capability (for containers)

These are automatically installed in the dev container via `postCreateCommand`.
