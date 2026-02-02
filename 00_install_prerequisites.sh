#!/usr/bin/env bash
set -euo pipefail

# ======= Enterprise Foundry - Prerequisites Installation =======
# This script installs or upgrades:
#   - Azure CLI
#   - Terraform
# Supports Ubuntu/Debian-based systems (including WSL)

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

TERRAFORM_MIN_VERSION="1.5.0"

echo -e "${BOLD}${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║${NC}  ${BOLD}🔧 Prerequisites Installation Script${NC}                      ${CYAN}║${NC}"
echo -e "${BOLD}${CYAN}║${NC}  Installs/upgrades: Azure CLI, Terraform                    ${CYAN}║${NC}"
echo -e "${BOLD}${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to compare versions
version_gte() {
    printf '%s\n%s\n' "$2" "$1" | sort -V -C
}

# ==================== AZURE CLI ====================
echo -e "${BOLD}${CYAN}=== Azure CLI ===${NC}"

if command -v az &> /dev/null; then
    AZ_VERSION=$(az version --query '"azure-cli"' -o tsv 2>/dev/null || echo "unknown")
    echo -e "Current Azure CLI version: ${GREEN}$AZ_VERSION${NC}"
    read -p "Do you want to upgrade Azure CLI to the latest version? (y/N): " -n 1 -r
    echo
    INSTALL_AZ=false
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        INSTALL_AZ=true
    fi
else
    echo -e "${YELLOW}Azure CLI is not installed. Installing...${NC}"
    INSTALL_AZ=true
fi

if [ "$INSTALL_AZ" = true ]; then
    echo "Installing/upgrading Azure CLI..."
    
    # Install dependencies
    sudo apt-get update
    sudo apt-get install -y ca-certificates curl apt-transport-https lsb-release gnupg
    
    # Download and install Microsoft signing key
    sudo mkdir -p /etc/apt/keyrings
    curl -sLS https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor | sudo tee /etc/apt/keyrings/microsoft.gpg > /dev/null
    sudo chmod go+r /etc/apt/keyrings/microsoft.gpg
    
    # Add Azure CLI repository
    AZ_DIST=$(lsb_release -cs)
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/microsoft.gpg] https://packages.microsoft.com/repos/azure-cli/ $AZ_DIST main" | sudo tee /etc/apt/sources.list.d/azure-cli.list
    
    # Install Azure CLI
    sudo apt-get update
    sudo apt-get install -y azure-cli
    
    echo -e "${GREEN}✅ Azure CLI installed: $(az version --query '"azure-cli"' -o tsv)${NC}"
else
    echo -e "${GREEN}✅ Keeping current Azure CLI version${NC}"
fi

echo ""

# ==================== TERRAFORM ====================
echo -e "${BOLD}${CYAN}=== Terraform ===${NC}"

if command -v terraform &> /dev/null; then
    TF_VERSION=$(terraform version -json 2>/dev/null | grep -oP '"terraform_version":\s*"\K[^"]+' || terraform version | head -1 | grep -oP '\d+\.\d+\.\d+')
    echo -e "Current Terraform version: ${GREEN}$TF_VERSION${NC}"
    
    if version_gte "$TF_VERSION" "$TERRAFORM_MIN_VERSION"; then
        echo "Terraform $TF_VERSION meets minimum requirement ($TERRAFORM_MIN_VERSION)"
        read -p "Do you want to upgrade to the latest version? (y/N): " -n 1 -r
        echo
        INSTALL_TF=false
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            INSTALL_TF=true
        fi
    else
        echo -e "${YELLOW}Terraform $TF_VERSION is below minimum required version ($TERRAFORM_MIN_VERSION)${NC}"
        INSTALL_TF=true
    fi
else
    echo -e "${YELLOW}Terraform is not installed. Installing...${NC}"
    INSTALL_TF=true
fi

if [ "$INSTALL_TF" = true ]; then
    echo "Installing/upgrading Terraform..."
    
    # Install dependencies
    sudo apt-get install -y gnupg software-properties-common curl
    
    # Add HashiCorp GPG key
    curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg --yes
    
    # Add HashiCorp repository
    echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
    
    # Install Terraform
    sudo apt-get update
    sudo apt-get install -y terraform
    
    echo -e "${GREEN}✅ Terraform installed: $(terraform version | head -1)${NC}"
else
    echo -e "${GREEN}✅ Keeping current Terraform version${NC}"
fi

echo ""
echo -e "${BOLD}${CYAN}=== Installation Complete ===${NC}"
echo ""
echo -e "Azure CLI:  $(az version --query '"azure-cli"' -o tsv 2>/dev/null || echo 'not installed')"
echo -e "Terraform:  $(terraform version 2>/dev/null | head -1 | grep -oP '\d+\.\d+\.\d+' || echo 'not installed')"
echo ""
echo -e "${GREEN}Prerequisites are ready!${NC}"
