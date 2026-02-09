#!/bin/bash
# Generate .env file from Terraform outputs

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_AI_DIR="$SCRIPT_DIR/../../terraform/ai_services"
TERRAFORM_APPS_DIR="$SCRIPT_DIR/../../terraform/container_apps"

echo "Generating .env file from Terraform outputs..."

# Check if terraform directory exists
if [ ! -d "$TERRAFORM_AI_DIR" ]; then
    echo "Error: Terraform ai_services directory not found: $TERRAFORM_AI_DIR"
    exit 1
fi

cd "$TERRAFORM_AI_DIR"

# Check if terraform state exists
if [ ! -f "terraform.tfstate" ]; then
    echo "Error: Terraform state not found in ai_services. Run 'terraform apply' first."
    exit 1
fi

# Get outputs
DOCINTEL_ENDPOINT=$(terraform output -raw docintel_endpoint 2>/dev/null || echo "")
FOUNDRY_NAME=$(terraform output -raw foundry_name 2>/dev/null || echo "")
FOUNDRY_PROJECT_NAME=$(terraform output -raw foundry_project_name 2>/dev/null || echo "")

if [ -z "$DOCINTEL_ENDPOINT" ]; then
    echo "Warning: Could not get docintel_endpoint from terraform outputs"
fi

# Construct the AI project endpoint if foundry info is available
AZURE_AI_PROJECT_ENDPOINT=""
if [ -n "$FOUNDRY_NAME" ] && [ -n "$FOUNDRY_PROJECT_NAME" ]; then
    AZURE_AI_PROJECT_ENDPOINT="https://${FOUNDRY_NAME}.cognitiveservices.azure.com/api/projects/${FOUNDRY_PROJECT_NAME}"
fi

# Get ACR and resource group from container_apps tfvars
ACR_NAME=""
RESOURCE_GROUP=""
if [ -f "$TERRAFORM_APPS_DIR/terraform.tfvars" ]; then
    ACR_NAME=$(grep -E '^acr_name\s*=' "$TERRAFORM_APPS_DIR/terraform.tfvars" | sed 's/.*=\s*"\(.*\)"/\1/' || echo "")
    RESOURCE_GROUP=$(grep -E '^rg_app\s*=' "$TERRAFORM_APPS_DIR/terraform.tfvars" | sed 's/.*=\s*"\(.*\)"/\1/' || echo "")
else
    echo "Warning: container_apps/terraform.tfvars not found, ACR_NAME and RESOURCE_GROUP will be empty"
fi

# Create .env file
ENV_FILE="$SCRIPT_DIR/.env"

cat > "$ENV_FILE" << EOF
# File Upload App Environment Variables
# Auto-generated from Terraform outputs on $(date)

# Azure Infrastructure
ACR_NAME=$ACR_NAME
RESOURCE_GROUP=$RESOURCE_GROUP

# Azure Document Intelligence Endpoint
AZURE_DOCINTEL_ENDPOINT=$DOCINTEL_ENDPOINT

# Azure AI Foundry Configuration
AZURE_AI_PROJECT_ENDPOINT=$AZURE_AI_PROJECT_ENDPOINT
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4.1

# Upload Configuration (optional)
UPLOAD_FOLDER=./uploads
MAX_CONTENT_LENGTH=16777216
HEALTH_PORT=8081

# Note: AZURE_CLIENT_ID is not needed when using DefaultAzureCredential locally
# It will use your Azure CLI credentials
EOF

echo "✓ .env file created at: $ENV_FILE"
echo ""
echo "Contents:"
cat "$ENV_FILE"
