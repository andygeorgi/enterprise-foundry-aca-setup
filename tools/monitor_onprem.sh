#!/usr/bin/env bash
# Enterprise Foundry - Monitor on-prem VM connectivity test
# Usage: ./monitor_onprem.sh

set -euo pipefail

# Configuration
RG_APP="${RG_APP:-rg-hexpert-sbx-app}"
APP_ONPREM="${APP_ONPREM_NAME:-aca-onprem-connectivity-test}"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

clear
echo -e "${BOLD}${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║${NC}  ${BOLD}🖥️  ON-PREM VM CONNECTIVITY TEST${NC}                          ${CYAN}║${NC}"
echo -e "${BOLD}${CYAN}║${NC}  Container: ${YELLOW}$APP_ONPREM${NC}            ${CYAN}║${NC}"
echo -e "${BOLD}${CYAN}║${NC}  Target: On-prem simulation VM (ports 80, 443)              ${CYAN}║${NC}"
echo -e "${BOLD}${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo -e "${CYAN}Press Ctrl+C to stop${NC}\n"

# Stream logs and format output
az containerapp logs show -g "$RG_APP" -n "$APP_ONPREM" --follow 2>&1 | while IFS= read -r line; do
    # Extract timestamp and log from JSON
    if echo "$line" | grep -q '"Log"'; then
        timestamp=$(echo "$line" | grep -oP '"TimeStamp":\s*"\K[^"]+' | cut -d'.' -f1 | sed 's/T/ /')
        log_content=$(echo "$line" | grep -oP '"Log":\s*"\K[^"]+' | sed 's/^F //')
        
        # Skip if empty or just package install messages
        [[ -z "$log_content" ]] && continue
        [[ "$log_content" == *"fetch"* ]] && continue
        [[ "$log_content" == *"Installing"* ]] && continue
        
        # Format based on content
        if echo "$log_content" | grep -q 'HTTP=OK'; then
            echo -e "${GREEN}✅ [${timestamp}] $log_content${NC}"
        elif echo "$log_content" | grep -q 'TCP=OK'; then
            echo -e "${YELLOW}⚠️  [${timestamp}] $log_content${NC}"
        elif echo "$log_content" | grep -q 'FAIL'; then
            echo -e "${RED}❌ [${timestamp}] $log_content${NC}"
        elif echo "$log_content" | grep -q 'onprem'; then
            echo -e "   [${timestamp}] $log_content"
        fi
    fi
done
