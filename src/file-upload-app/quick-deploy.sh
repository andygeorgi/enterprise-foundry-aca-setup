#!/bin/bash
################################################################################
# Quick Deploy Script - File Upload App
# Combines build and deploy into one command
################################################################################

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  File Upload App - Quick Deploy       ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${BLUE}Step 1/2: Building and pushing image to ACR...${NC}"
./build.sh

echo ""
echo -e "${BLUE}Step 2/2: Deploying to Azure Container Apps...${NC}"
./deploy.sh

echo ""
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Deployment Complete! 🎉               ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
