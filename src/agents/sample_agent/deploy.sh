#!/bin/bash
################################################################################
# Deploy Container App to Azure Container Apps
################################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration - update these based on your terraform.tfvars
ACR_NAME="${ACR_NAME:-foundrysbxacr1}"
IMAGE_NAME="${IMAGE_NAME:-sample-agent}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
RESOURCE_GROUP="${RESOURCE_GROUP:-rg-foundry-sbx-app1}"
ACA_ENV_NAME="${ACA_ENV_NAME:-cae-foundry-sbx}"
APP_NAME="${APP_NAME:-aca-sample-agent}"

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Deploying to Azure Container Apps${NC}"
echo -e "${GREEN}================================${NC}"

# Get ACR details
echo -e "${YELLOW}🔍 Getting ACR details...${NC}"
ACR_LOGIN_SERVER=$(az acr show --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" --query loginServer -o tsv)
FULL_IMAGE_NAME="${ACR_LOGIN_SERVER}/${IMAGE_NAME}:${IMAGE_TAG}"

# Get managed identity for ACR pull
echo -e "${YELLOW}🔍 Getting managed identity...${NC}"
IDENTITY_ID=$(az identity show --name "id-aca-acr-pull" --resource-group "$RESOURCE_GROUP" --query id -o tsv)
IDENTITY_CLIENT_ID=$(az identity show --name "id-aca-acr-pull" --resource-group "$RESOURCE_GROUP" --query clientId -o tsv)

# Check if app exists
APP_EXISTS=$(az containerapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" 2>/dev/null || echo "")

if [ -z "$APP_EXISTS" ]; then
    echo -e "${YELLOW}📦 Creating new container app: ${APP_NAME}${NC}"
    
    az containerapp create \
        --name "$APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --environment "$ACA_ENV_NAME" \
        --image "$FULL_IMAGE_NAME" \
        --target-port 8080 \
        --ingress internal \
        --min-replicas 1 \
        --max-replicas 3 \
        --cpu 0.5 \
        --memory 1.0Gi \
        --registry-server "$ACR_LOGIN_SERVER" \
        --registry-identity "$IDENTITY_ID" \
        --user-assigned "$IDENTITY_ID" \
        --env-vars \
            PORT=8080 \
            UPLOAD_FOLDER=/app/uploads \
            MAX_CONTENT_LENGTH=16777216
else
    echo -e "${YELLOW}🔄 Updating existing container app: ${APP_NAME}${NC}"
    
    az containerapp update \
        --name "$APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --image "$FULL_IMAGE_NAME"
fi

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
echo -e "${GREEN}================================${NC}"

# Get the app FQDN
echo ""
echo -e "${BLUE}Getting app details...${NC}"
APP_FQDN=$(az containerapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" --query properties.configuration.ingress.fqdn -o tsv)

echo ""
echo -e "${GREEN}Container App Details:${NC}"
echo -e "  Name: ${YELLOW}${APP_NAME}${NC}"
echo -e "  FQDN: ${YELLOW}${APP_FQDN}${NC}"
echo -e "  URL:  ${YELLOW}https://${APP_FQDN}${NC}"
echo ""
echo -e "${BLUE}Note: The app uses internal ingress. Access from within the VNet or via VPN.${NC}"
