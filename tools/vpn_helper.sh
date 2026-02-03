#!/bin/bash
################################################################################
# VPN Connection Helper Script
# Quick commands for managing Azure Point-to-Site VPN connection
################################################################################

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration - can be overridden via environment variables
RG_NAME="${RG_NAME:-rg-foundry-sbx-net}"
VPN_GW_NAME="${VPN_GW_NAME:-vpngw-vnet-hub-weu}"

show_menu() {
    echo -e "${GREEN}================================${NC}"
    echo -e "${GREEN}Azure P2S VPN Helper${NC}"
    echo -e "${GREEN}================================${NC}"
    echo ""
    echo "1. Check VPN Gateway status"
    echo "2. Download VPN client configuration"
    echo "3. List active VPN connections"
    echo "4. Show VPN Gateway details"
    echo "5. Generate new client certificate"
    echo "6. Test connectivity to Azure resources"
    echo "7. Show VPN client routes"
    echo "8. Exit"
    echo ""
    read -p "Enter your choice [1-8]: " choice
    echo ""
}

check_vpn_status() {
    echo -e "${YELLOW}Checking VPN Gateway status...${NC}"
    az network vnet-gateway show \
        --resource-group "$RG_NAME" \
        --name "$VPN_GW_NAME" \
        --query '{Name:name, ProvisioningState:provisioningState, SKU:sku.name, VpnType:vpnType}' \
        -o table
}

download_vpn_config() {
    echo -e "${YELLOW}Generating VPN client configuration package...${NC}"
    echo "This may take a few moments..."
    
    url=$(az network vnet-gateway vpn-client generate \
        --resource-group "$RG_NAME" \
        --name "$VPN_GW_NAME" \
        --processor-architecture Amd64 \
        -o tsv)
    
    echo ""
    echo -e "${GREEN}VPN client configuration URL:${NC}"
    echo "$url"
    echo ""
    echo "Download this ZIP file and extract it to configure your VPN client."
    echo ""
    read -p "Do you want to download it now using curl? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        curl -L -o ~/VpnClient.zip "$url"
        echo -e "${GREEN}Downloaded to ~/VpnClient.zip${NC}"
    fi
}

list_vpn_connections() {
    echo -e "${YELLOW}Active P2S VPN connections:${NC}"
    az network vnet-gateway list-vpn-client-sessions \
        --resource-group "$RG_NAME" \
        --name "$VPN_GW_NAME" \
        -o table 2>/dev/null || echo "No active connections or error retrieving data."
}

show_vpn_details() {
    echo -e "${YELLOW}VPN Gateway details:${NC}"
    az network vnet-gateway show \
        --resource-group "$RG_NAME" \
        --name "$VPN_GW_NAME" \
        --query '{
            Name: name,
            Location: location,
            ProvisioningState: provisioningState,
            SKU: sku.name,
            VpnType: vpnType,
            ActiveActive: activeActive,
            EnableBgp: enableBgp,
            VpnClientAddressPool: vpnClientConfiguration.vpnClientAddressPool.addressPrefixes[0],
            VpnClientProtocols: vpnClientConfiguration.vpnClientProtocols,
            PublicIP: ipConfigurations[0].publicIpAddress
        }' \
        -o json | jq '.'
}

generate_client_cert() {
    echo -e "${YELLOW}Generating new client certificate...${NC}"
    
    CERT_DIR="${HOME}/vpn-certs"
    
    if [ ! -f "$CERT_DIR/rootCA.crt" ] || [ ! -f "$CERT_DIR/rootCA.key" ]; then
        echo -e "${RED}Error: Root certificate not found!${NC}"
        echo "Please run ./tools/generate_vpn_certificates.sh first to create the root certificate."
        return 1
    fi
    
    read -p "Enter client name (e.g., laptop, desktop, phone): " client_name
    client_name=${client_name:-client-$(date +%s)}
    
    cd "$CERT_DIR"
    
    # Create OpenSSL config for client cert with proper Extended Key Usage
    cat > "${client_name}_cert.cnf" << 'EOF'
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req

[req_distinguished_name]

[v3_req]
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = clientAuth
EOF
    
    # Generate client private key
    openssl genrsa -out "${client_name}.key" 4096 2>/dev/null
    echo "✓ Client private key generated"
    
    # Create CSR with config
    openssl req -new -key "${client_name}.key" -out "${client_name}.csr" \
        -subj "/C=US/ST=State/L=City/O=MyOrganization/CN=${client_name}" \
        -config "${client_name}_cert.cnf" 2>/dev/null
    echo "✓ Client CSR generated"
    
    # Sign with root CA including v3 extensions
    openssl x509 -req -in "${client_name}.csr" -CA rootCA.crt -CAkey rootCA.key \
        -CAcreateserial -out "${client_name}.crt" -days 365 -sha256 \
        -extensions v3_req -extfile "${client_name}_cert.cnf" 2>/dev/null
    echo "✓ Client certificate signed with TLS Client Auth EKU"
    
    # Create P12 bundle
    read -s -p "Enter password for P12 file: " p12_pass
    echo
    openssl pkcs12 -export -out "${client_name}.p12" -inkey "${client_name}.key" \
        -in "${client_name}.crt" -certfile rootCA.crt -password pass:"${p12_pass}" 2>/dev/null
    
    # Clean up temporary config file
    rm -f "${client_name}_cert.cnf"
    
    echo ""
    echo -e "${GREEN}Client certificate generated successfully!${NC}"
    echo "Files created in $CERT_DIR:"
    echo "  - ${client_name}.crt (certificate)"
    echo "  - ${client_name}.key (private key)"
    echo "  - ${client_name}.p12 (bundle for installation)"
    echo ""
    echo "To install on macOS:"
    echo "  security import $CERT_DIR/${client_name}.p12 -k ~/Library/Keychains/login.keychain"
}

test_connectivity() {
    echo -e "${YELLOW}Testing connectivity to Azure resources...${NC}"
    echo ""
    
    # Get VM IP from Terraform output
    echo "Fetching resource IPs from Terraform..."
    cd /workspaces/enterprise-foundry-aca-setup/terraform/network
    
    vm_ip=$(terraform output -raw onprem_vm_private_ip 2>/dev/null || echo "")
    
    if [ -z "$vm_ip" ]; then
        echo -e "${RED}Could not retrieve VM IP from Terraform output.${NC}"
        echo "Have you deployed the infrastructure with 'terraform apply'?"
        return 1
    fi
    
    echo ""
    echo "Test 1: Ping on-prem simulation VM ($vm_ip)"
    ping -c 3 "$vm_ip" 2>/dev/null && echo -e "${GREEN}✓ Success${NC}" || echo -e "${RED}✗ Failed${NC}"
    
    echo ""
    echo "Test 2: HTTP connection to nginx on VM"
    curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" "http://$vm_ip" 2>/dev/null && echo -e "${GREEN}✓ Success${NC}" || echo -e "${RED}✗ Failed${NC}"
    
    echo ""
    echo "Test 3: DNS resolution of private endpoints"
    echo "Sandbox VNet gateway: 10.7.0.1"
    ping -c 2 10.7.0.1 2>/dev/null && echo -e "${GREEN}✓ Success${NC}" || echo -e "${RED}✗ Failed${NC}"
}

show_routes() {
    echo -e "${YELLOW}VPN client should receive these routes when connected:${NC}"
    echo ""
    echo "Destination         Gateway          Interface"
    echo "------------------------------------------------"
    echo "10.0.0.0/16         VPN Gateway      vpn0"
    echo "10.7.0.0/26         VPN Gateway      vpn0"
    echo "10.7.1.0/24         VPN Gateway      vpn0"
    echo ""
    echo "To verify routes on your system:"
    echo ""
    echo "Linux:"
    echo "  ip route show | grep vpn"
    echo ""
    echo "macOS:"
    echo "  netstat -nr | grep utun"
    echo ""
    echo "Windows:"
    echo "  route print | findstr \"10.0 10.7\""
}

# Main loop
while true; do
    show_menu
    
    case $choice in
        1)
            check_vpn_status
            ;;
        2)
            download_vpn_config
            ;;
        3)
            list_vpn_connections
            ;;
        4)
            show_vpn_details
            ;;
        5)
            generate_client_cert
            ;;
        6)
            test_connectivity
            ;;
        7)
            show_routes
            ;;
        8)
            echo -e "${GREEN}Goodbye!${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid choice. Please try again.${NC}"
            ;;
    esac
    
    echo ""
    read -p "Press Enter to continue..."
    clear
done
