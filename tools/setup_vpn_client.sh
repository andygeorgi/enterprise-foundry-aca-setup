#!/bin/bash
################################################################################
# VPN Client Setup Script
# Automates the complete setup of OpenVPN client for Azure P2S VPN
################################################################################

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration - can be overridden via environment variables
CERT_DIR="${HOME}/vpn-certs"
VPN_DIR="${HOME}/OpenVPN"
RG_NAME="${RG_NAME:-rg-foundry-sbx-net}"
VPN_GW_NAME="${VPN_GW_NAME:-vpngw-vnet-hub-weu}"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Azure VPN Client Setup Script${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Step 1: Check prerequisites
echo -e "${YELLOW}Step 1: Checking prerequisites...${NC}"

if ! command -v az &> /dev/null; then
    echo -e "${RED}Error: Azure CLI not found. Please install it first.${NC}"
    exit 1
fi

if ! command -v openssl &> /dev/null; then
    echo -e "${RED}Error: OpenSSL not found. Installing...${NC}"
    sudo apt update && sudo apt install -y openssl
fi

if ! command -v openvpn &> /dev/null; then
    echo -e "${RED}OpenVPN not found. Installing...${NC}"
    sudo apt update && sudo apt install -y openvpn
fi

echo -e "${GREEN}✓ Prerequisites checked${NC}"
echo ""

# Step 2: Check if certificates exist
echo -e "${YELLOW}Step 2: Checking VPN certificates...${NC}"

if [ ! -f "$CERT_DIR/rootCA.crt" ] || [ ! -f "$CERT_DIR/client.crt" ]; then
    echo -e "${RED}Error: VPN certificates not found!${NC}"
    echo "Please run: ./tools/generate_vpn_certificates.sh first"
    exit 1
fi

# Verify client certificate has proper Extended Key Usage
if ! openssl x509 -in "$CERT_DIR/client.crt" -noout -text | grep -q "TLS Web Client Authentication"; then
    echo -e "${YELLOW}Warning: Client certificate missing proper Extended Key Usage${NC}"
    echo "Regenerating client certificate with correct EKU..."
    
    cd "$CERT_DIR"
    
    # Create OpenSSL config for client cert
    cat > client_cert.cnf << 'EOF'
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req

[req_distinguished_name]

[v3_req]
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = clientAuth
EOF

    # Backup old certificates
    [ -f client.crt ] && mv client.crt client.crt.old
    [ -f client.key ] && mv client.key client.key.old
    
    # Generate new client certificate
    openssl genrsa -out client.key 4096 2>/dev/null
    openssl req -new -key client.key -out client.csr \
        -subj "/C=US/ST=State/L=City/O=MyOrg/CN=P2SClient" \
        -config client_cert.cnf 2>/dev/null
    openssl x509 -req -in client.csr -CA rootCA.crt -CAkey rootCA.key \
        -CAcreateserial -out client.crt -days 365 -sha256 \
        -extensions v3_req -extfile client_cert.cnf 2>/dev/null
    
    # Clean up
    rm -f client_cert.cnf client.csr
    chmod 600 client.key
    
    echo -e "${GREEN}✓ Client certificate regenerated${NC}"
fi

echo -e "${GREEN}✓ Certificates verified${NC}"
echo ""

# Step 3: Check Azure login
echo -e "${YELLOW}Step 3: Checking Azure authentication...${NC}"

if ! az account show &> /dev/null; then
    echo -e "${YELLOW}Not logged in to Azure. Please login:${NC}"
    az login
fi

echo -e "${GREEN}✓ Azure authentication confirmed${NC}"
echo ""

# Step 4: Download VPN client configuration
echo -e "${YELLOW}Step 4: Downloading VPN client configuration...${NC}"

if [ -f "$VPN_DIR/vpnconfig.ovpn" ]; then
    echo -e "${YELLOW}VPN config already exists. Regenerate? (y/N):${NC}"
    read -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping download, using existing config"
    else
        rm -rf "$VPN_DIR"
    fi
fi

if [ ! -f "$VPN_DIR/vpnconfig.ovpn" ]; then
    echo "Generating VPN client package (this may take a minute)..."
    
    url=$(az network vnet-gateway vpn-client generate \
        --resource-group "$RG_NAME" \
        --name "$VPN_GW_NAME" \
        --processor-architecture Amd64 \
        -o tsv)
    
    if [ -z "$url" ]; then
        echo -e "${RED}Error: Failed to generate VPN client package${NC}"
        exit 1
    fi
    
    echo "Downloading VPN client package..."
    curl -sL -o /tmp/VpnClient.zip "$url"
    
    # Extract
    mkdir -p "$VPN_DIR"
    unzip -q /tmp/VpnClient.zip -d "$VPN_DIR"
    rm -f /tmp/VpnClient.zip
    
    echo -e "${GREEN}✓ VPN client configuration downloaded${NC}"
else
    echo -e "${GREEN}✓ Using existing VPN configuration${NC}"
fi
echo ""

# Step 5: Update VPN config with certificates
echo -e "${YELLOW}Step 5: Configuring VPN client with certificates...${NC}"

cd "$VPN_DIR"

# Check if we're in the right directory
if [ ! -f "OpenVPN/vpnconfig.ovpn" ]; then
    echo -e "${RED}Error: vpnconfig.ovpn not found in expected location${NC}"
    echo "Expected: $VPN_DIR/OpenVPN/vpnconfig.ovpn"
    exit 1
fi

cd OpenVPN

# Remove any existing cert/key sections
sed -i '/<cert>/,/<\/cert>/d' vpnconfig.ovpn
sed -i '/<key>/,/<\/key>/d' vpnconfig.ovpn
sed -i '/^cert /d' vpnconfig.ovpn
sed -i '/^key /d' vpnconfig.ovpn

# Disable file logging (show output in terminal instead)
sed -i 's/^log openvpn.log/#log openvpn.log/' vpnconfig.ovpn

# Add certificates inline
echo "" >> vpnconfig.ovpn
echo "<cert>" >> vpnconfig.ovpn
cat "$CERT_DIR/client.crt" >> vpnconfig.ovpn
echo "</cert>" >> vpnconfig.ovpn
echo "" >> vpnconfig.ovpn
echo "<key>" >> vpnconfig.ovpn
cat "$CERT_DIR/client.key" >> vpnconfig.ovpn
echo "</key>" >> vpnconfig.ovpn

echo -e "${GREEN}✓ VPN configuration updated with certificates${NC}"
echo ""

# Step 6: Check TUN/TAP device
echo -e "${YELLOW}Step 6: Checking TUN/TAP device...${NC}"

if [ ! -c /dev/net/tun ]; then
    echo -e "${RED}Error: /dev/net/tun device not found${NC}"
    echo "This usually means:"
    echo "  1. Running in a container without NET_ADMIN capability"
    echo "  2. TUN module not loaded on host"
    echo ""
    echo "Solutions:"
    echo "  - Rebuild dev container with NET_ADMIN capability"
    echo "  - Run VPN on host machine instead"
    echo "  - On host: sudo modprobe tun"
    exit 1
fi

echo -e "${GREEN}✓ TUN/TAP device available${NC}"
echo ""

# Step 7: Create helper script for connecting
echo -e "${YELLOW}Step 7: Creating connection helper script...${NC}"

cat > "$VPN_DIR/connect.sh" << 'CONNECT_SCRIPT'
#!/bin/bash
# Quick VPN connection script

cd "$(dirname "$0")/OpenVPN"

echo "Starting OpenVPN connection..."
echo "Press Ctrl+C to disconnect"
echo ""

sudo openvpn --config vpnconfig.ovpn --verb 3
CONNECT_SCRIPT

chmod +x "$VPN_DIR/connect.sh"

echo -e "${GREEN}✓ Connection helper script created${NC}"
echo ""

# Summary
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "VPN client is ready. To connect:"
echo ""
echo "  ${GREEN}cd $VPN_DIR && ./connect.sh${NC}"
echo ""
echo "Or manually:"
echo ""
echo "  ${GREEN}cd $VPN_DIR/OpenVPN${NC}"
echo "  ${GREEN}sudo openvpn --config vpnconfig.ovpn --verb 3${NC}"
echo ""
echo "Once connected, test with:"
echo ""
echo "  ${GREEN}ping 10.7.1.4${NC}          # On-prem VM"
echo "  ${GREEN}curl http://10.7.1.4${NC}   # nginx on VM"
echo "  ${GREEN}ip addr show tun0${NC}      # VPN interface"
echo "  ${GREEN}ip route | grep tun0${NC}   # VPN routes"
echo ""
echo -e "${YELLOW}Note: OpenVPN must run as root (sudo). Keep the terminal open while connected.${NC}"
echo ""
