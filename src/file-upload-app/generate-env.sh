#!/bin/bash
# Generate .env file from Terraform outputs

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="$SCRIPT_DIR/../../terraform/ai_services"

echo "Generating .env file from Terraform outputs..."

# Check if terraform directory exists
if [ ! -d "$TERRAFORM_DIR" ]; then
    echo "Error: Terraform directory not found: $TERRAFORM_DIR"
    exit 1
fi

cd "$TERRAFORM_DIR"

# Check if terraform state exists
if [ ! -f "terraform.tfstate" ]; then
    echo "Error: Terraform state not found. Run 'terraform apply' first."
    exit 1
fi

# Get outputs
DOCINTEL_ENDPOINT=$(terraform output -raw docintel_endpoint 2>/dev/null || echo "")

if [ -z "$DOCINTEL_ENDPOINT" ]; then
    echo "Error: Could not get docintel_endpoint from terraform outputs"
    exit 1
fi

# Create .env file
ENV_FILE="$SCRIPT_DIR/.env"

cat > "$ENV_FILE" << EOF
# File Upload App Environment Variables
# Auto-generated from Terraform outputs on $(date)

# Azure Document Intelligence Endpoint
AZURE_DOCINTEL_ENDPOINT=$DOCINTEL_ENDPOINT

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
