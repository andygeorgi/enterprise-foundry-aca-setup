#!/bin/bash
################################################################################
# VPN Certificate Generator
# 
# This script generates the certificates needed for Point-to-Site VPN:
# - Root certificate (for Azure VPN Gateway)
# - Client certificate (for VPN client authentication)
################################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
CERT_DIR="${HOME}/vpn-certs"
ROOT_CERT_NAME="P2SRootCert"
CLIENT_CERT_NAME="P2SClientCert"
DAYS_VALID_ROOT=3650  # 10 years
DAYS_VALID_CLIENT=365 # 1 year

echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}Azure Point-to-Site VPN Certificate Generator${NC}"
echo -e "${GREEN}==================================================${NC}"
echo ""

# Create certificate directory
mkdir -p "${CERT_DIR}"
cd "${CERT_DIR}"

echo -e "${YELLOW}Certificate directory: ${CERT_DIR}${NC}"
echo ""

# Check if certificates already exist
if [ -f "rootCA.crt" ]; then
    echo -e "${YELLOW}Warning: Root certificate already exists!${NC}"
    read -p "Do you want to regenerate certificates? This will invalidate existing client certificates. (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}Aborted.${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}Step 1: Generating Root Certificate${NC}"
echo "--------------------------------------------"

# Generate root certificate private key
openssl genrsa -out rootCA.key 4096 2>/dev/null
echo "✓ Root private key generated (rootCA.key)"

# Generate root certificate
openssl req -x509 -new -nodes -key rootCA.key -sha256 -days ${DAYS_VALID_ROOT} \
  -out rootCA.crt \
  -subj "/C=US/ST=State/L=City/O=MyOrganization/CN=${ROOT_CERT_NAME}" 2>/dev/null
echo "✓ Root certificate generated (rootCA.crt)"

# Export root certificate in base64 format (without headers) for Azure
openssl x509 -in rootCA.crt -outform der | base64 -w 0 > rootCA.base64
echo "✓ Root certificate exported in base64 format (rootCA.base64)"

echo ""
echo -e "${GREEN}Step 2: Generating Client Certificate${NC}"
echo "--------------------------------------------"

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

# Generate client private key
openssl genrsa -out client.key 4096 2>/dev/null
echo "✓ Client private key generated (client.key)"

# Create certificate signing request (CSR) with config
openssl req -new -key client.key -out client.csr \
  -subj "/C=US/ST=State/L=City/O=MyOrganization/CN=${CLIENT_CERT_NAME}" \
  -config client_cert.cnf 2>/dev/null
echo "✓ Client CSR generated (client.csr)"

# Sign the client certificate with root CA including the v3 extensions
openssl x509 -req -in client.csr -CA rootCA.crt -CAkey rootCA.key \
  -CAcreateserial -out client.crt -days ${DAYS_VALID_CLIENT} -sha256 \
  -extensions v3_req -extfile client_cert.cnf 2>/dev/null
echo "✓ Client certificate signed with TLS Client Auth EKU (client.crt)"

# Prompt for P12 password
echo ""
echo -e "${YELLOW}Enter a password to protect the client certificate file:${NC}"
read -s -p "Password: " P12_PASSWORD
echo
read -s -p "Confirm password: " P12_PASSWORD_CONFIRM
echo

if [ "$P12_PASSWORD" != "$P12_PASSWORD_CONFIRM" ]; then
    echo -e "${RED}Passwords do not match!${NC}"
    exit 1
fi

# Create PKCS#12 file for easy import (includes private key and certificate)
openssl pkcs12 -export -out client.p12 -inkey client.key -in client.crt \
  -certfile rootCA.crt -password pass:"${P12_PASSWORD}" 2>/dev/null
echo "✓ Client certificate packaged (client.p12)"

# Clean up temporary files
rm -f client_cert.cnf

echo ""
echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}Certificate Generation Complete!${NC}"
echo -e "${GREEN}==================================================${NC}"
echo ""

echo "Files generated in ${CERT_DIR}:"
echo "  - rootCA.crt        : Root certificate"
echo "  - rootCA.key        : Root private key (keep secure!)"
echo "  - rootCA.base64     : Root certificate for Azure (use in Terraform)"
echo "  - client.crt        : Client certificate"
echo "  - client.key        : Client private key"
echo "  - client.p12        : Client certificate bundle (for VPN client)"
echo ""

echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Copy the root certificate data for Terraform:"
echo ""
echo "   ${GREEN}cat ${CERT_DIR}/rootCA.base64${NC}"
echo ""
echo "   Add this value to your terraform.tfvars file:"
echo "   ${GREEN}vpn_root_cert_data = \"<paste-the-certificate-here>\"${NC}"
echo ""
echo "2. After deploying the VPN Gateway, install the client certificate:"
echo ""
echo "   ${GREEN}# On macOS:${NC}"
echo "   security import ${CERT_DIR}/client.p12 -k ~/Library/Keychains/login.keychain"
echo ""
echo "   ${GREEN}# On Linux (save location for NetworkManager):${NC}"
echo "   echo ${CERT_DIR}/client.p12"
echo ""
echo "3. Download the VPN client configuration from Azure Portal or using:"
echo ""
echo "   ${GREEN}az network vnet-gateway vpn-client generate \\${NC}"
echo "   ${GREEN}  --resource-group rg-foundry-sbx-net \\${NC}"
echo "   ${GREEN}  --name vpngw-vnet-hub-weu \\${NC}"
echo "   ${GREEN}  --processor-architecture Amd64${NC}"
echo ""

echo -e "${RED}Important:${NC}"
echo "  - Keep rootCA.key secure and backed up!"
echo "  - The client.p12 file is protected with the password you entered"
echo "  - You can generate additional client certificates using rootCA.crt and rootCA.key"
echo ""

# Display the base64 certificate
echo -e "${YELLOW}Root Certificate Data (for Terraform):${NC}"
echo "--------------------------------------------"
cat rootCA.base64
echo ""
echo "--------------------------------------------"
echo ""

# Set restrictive permissions
chmod 600 rootCA.key client.key client.p12
chmod 644 rootCA.crt client.crt rootCA.base64

echo -e "${GREEN}Done! Certificate files have been secured with appropriate permissions.${NC}"
