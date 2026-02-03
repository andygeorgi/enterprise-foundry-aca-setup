#!/bin/bash
################################################################################
# Local Testing Script - Run the app locally with Docker
################################################################################

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Starting File Upload App Locally${NC}"
echo -e "${GREEN}================================${NC}"

echo -e "${YELLOW}🐳 Starting Docker Compose...${NC}"
cd "$SCRIPT_DIR"
docker-compose up --build

echo -e "${BLUE}To stop the application, press Ctrl+C${NC}"
