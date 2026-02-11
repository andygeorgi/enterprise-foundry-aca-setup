#!/bin/bash
################################################################################
# Generate .env file from Terraform outputs for tools scripts
# Sources values from network, aca_env, and container_apps Terraform modules
################################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_NET_DIR="$SCRIPT_DIR/../terraform/network"
TERRAFORM_ACA_DIR="$SCRIPT_DIR/../terraform/aca_env"
TERRAFORM_APPS_DIR="$SCRIPT_DIR/../terraform/container_apps"

echo "Generating tools/.env file from Terraform outputs..."

# ── Network module ──────────────────────────────────────────────────────────

RG_NET=""
RG_APP=""
VPN_GW_NAME=""
VPN_GW_PUBLIC_IP=""
ONPREM_VM_IP=""

if [ -d "$TERRAFORM_NET_DIR" ] && [ -f "$TERRAFORM_NET_DIR/terraform.tfstate" ]; then
    cd "$TERRAFORM_NET_DIR"
    RG_NET=$(terraform output -raw rg_net_name 2>/dev/null | tr -d '\r' || echo "")
    RG_APP=$(terraform output -raw rg_app_name 2>/dev/null | tr -d '\r' || echo "")
    ONPREM_VM_IP=$(terraform output -raw onprem_vm_private_ip 2>/dev/null | tr -d '\r' || echo "")
    VPN_GW_PUBLIC_IP=$(terraform output -raw vpn_gateway_public_ip 2>/dev/null | tr -d '\r' || echo "")

    # Extract VPN gateway name from the resource ID
    VPN_GW_ID=$(terraform output -raw vpn_gateway_id 2>/dev/null | tr -d '\r' || echo "")
    if [ -n "$VPN_GW_ID" ]; then
        VPN_GW_NAME=$(echo "$VPN_GW_ID" | awk -F'/' '{print $NF}')
    fi
else
    echo "Warning: network terraform state not found, network values will be empty"
fi

# Fallback: read from network tfvars if outputs are empty
if [ -z "$RG_NET" ] && [ -f "$TERRAFORM_NET_DIR/terraform.tfvars" ]; then
    RG_NET=$(grep -E '^rg_net\s*=' "$TERRAFORM_NET_DIR/terraform.tfvars" | sed 's/.*=\s*"\(.*\)"/\1/' | tr -d '\r' || echo "")
    RG_APP=$(grep -E '^rg_app\s*=' "$TERRAFORM_NET_DIR/terraform.tfvars" | sed 's/.*=\s*"\(.*\)"/\1/' | tr -d '\r' || echo "")
fi

# ── Container Apps module ───────────────────────────────────────────────────

ACR_NAME=""
ACA_ENV_NAME=""
APP_FILE_UPLOAD_NAME=""
APP_ONPREM_NAME=""
APP_PE_STORAGE_NAME=""
FILE_UPLOAD_FQDN=""
ACA_STATIC_IP=""

if [ -f "$TERRAFORM_APPS_DIR/terraform.tfvars" ]; then
    ACR_NAME=$(grep -E '^acr_name\s*=' "$TERRAFORM_APPS_DIR/terraform.tfvars" | sed 's/.*=\s*"\(.*\)"/\1/' | tr -d '\r' || echo "")
    ACA_ENV_NAME=$(grep -E '^aca_env_name\s*=' "$TERRAFORM_APPS_DIR/terraform.tfvars" | sed 's/.*=\s*"\(.*\)"/\1/' | tr -d '\r' || echo "")
    APP_FILE_UPLOAD_NAME=$(grep -E '^app_file_upload_name\s*=' "$TERRAFORM_APPS_DIR/terraform.tfvars" | sed 's/.*=\s*"\(.*\)"/\1/' | tr -d '\r' || echo "")
    APP_ONPREM_NAME=$(grep -E '^app_onprem_name\s*=' "$TERRAFORM_APPS_DIR/terraform.tfvars" | sed 's/.*=\s*"\(.*\)"/\1/' | tr -d '\r' || echo "")
    APP_PE_STORAGE_NAME=$(grep -E '^app_pe_storage_name\s*=' "$TERRAFORM_APPS_DIR/terraform.tfvars" | sed 's/.*=\s*"\(.*\)"/\1/' | tr -d '\r' || echo "")
fi

# Get FQDNs from container_apps terraform outputs
if [ -d "$TERRAFORM_APPS_DIR" ] && [ -f "$TERRAFORM_APPS_DIR/terraform.tfstate" ]; then
    cd "$TERRAFORM_APPS_DIR"
    FILE_UPLOAD_FQDN=$(terraform output -json file_upload_app 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('fqdn',''))" 2>/dev/null | tr -d '\r' || echo "")
fi

# Get ACA environment static IP
if [ -d "$TERRAFORM_ACA_DIR" ] && [ -f "$TERRAFORM_ACA_DIR/terraform.tfstate" ]; then
    cd "$TERRAFORM_ACA_DIR"
    ACA_ENV_ID=$(terraform output -raw aca_env_id 2>/dev/null | tr -d '\r' || echo "")
    if [ -n "$ACA_ENV_ID" ] && [ -n "$RG_APP" ] && [ -n "$ACA_ENV_NAME" ]; then
        ACA_STATIC_IP=$(az containerapp env show --name "$ACA_ENV_NAME" --resource-group "$RG_APP" --query properties.staticIp -o tsv 2>/dev/null | tr -d '\r' || echo "")
    fi
fi

# ── Write .env file ────────────────────────────────────────────────────────

ENV_FILE="$SCRIPT_DIR/.env"

cat > "$ENV_FILE" << EOF
# Tools Environment Variables
# Auto-generated from Terraform outputs on $(date)

# ── Resource Groups ──
RG_NET=$RG_NET
RG_APP=$RG_APP

# ── VPN Gateway ──
VPN_GW_NAME=$VPN_GW_NAME
VPN_GW_PUBLIC_IP=$VPN_GW_PUBLIC_IP

# ── On-Prem VM ──
ONPREM_VM_IP=$ONPREM_VM_IP

# ── Azure Container Registry ──
ACR_NAME=$ACR_NAME

# ── ACA Environment ──
ACA_ENV_NAME=$ACA_ENV_NAME
ACA_STATIC_IP=$ACA_STATIC_IP

# ── Container App Names ──
APP_FILE_UPLOAD_NAME=$APP_FILE_UPLOAD_NAME
APP_ONPREM_NAME=$APP_ONPREM_NAME
APP_PE_STORAGE_NAME=$APP_PE_STORAGE_NAME

# ── Container App FQDNs ──
FILE_UPLOAD_FQDN=$FILE_UPLOAD_FQDN
EOF

echo "✓ .env file created at: $ENV_FILE"
echo ""
echo "Contents:"
cat "$ENV_FILE"
