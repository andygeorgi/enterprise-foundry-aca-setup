#!/bin/bash
################################################################################
# Build and Push Container Image to Azure Container Registry
################################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration - load from .env if available, allow env var overrides
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/.env" ]; then
    set -a
    source "$SCRIPT_DIR/.env"
    set +a
fi

ACR_NAME="${ACR_NAME:?Error: ACR_NAME not set. Run ./generate-env.sh first.}"
IMAGE_NAME="${IMAGE_NAME:-file-upload-app}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
RESOURCE_GROUP="${RESOURCE_GROUP:?Error: RESOURCE_GROUP not set. Run ./generate-env.sh first.}"

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Building and Pushing Container Image${NC}"
echo -e "${GREEN}================================${NC}"

# Get ACR login server
ACR_LOGIN_SERVER=$(az acr show --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" --query loginServer -o tsv)
FULL_IMAGE_NAME="${ACR_LOGIN_SERVER}/${IMAGE_NAME}:${IMAGE_TAG}"

echo -e "${YELLOW}📦 Building image using ACR agent pool (self-hosted in VNet)...${NC}"
echo -e "${YELLOW}   Image: ${FULL_IMAGE_NAME}${NC}"

# Use ACR build with agent pool (runs on self-hosted agents in your VNet)
# This allows building for private ACR without enabling public access
az acr build \
  --registry "$ACR_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --image "${IMAGE_NAME}:${IMAGE_TAG}" \
  --file "$SCRIPT_DIR/Dockerfile" \
  --platform linux/amd64 \
  --agent-pool acr-agent-pool \
  "$SCRIPT_DIR"

echo -e "${GREEN}✅ Successfully built and pushed image: ${FULL_IMAGE_NAME}${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo -e "To deploy this image to Azure Container Apps, run:"
echo -e "${YELLOW}./deploy.sh${NC}"
