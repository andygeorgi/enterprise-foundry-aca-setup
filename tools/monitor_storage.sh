#!/usr/bin/env bash
# Enterprise Foundry - Monitor storage private endpoint connectivity
# Usage: ./monitor_storage.sh

set -euo pipefail

# Configuration
RG_APP="${RG_APP:-rg-hexpert-sbx-app}"
APP_STORAGE="${APP_PE_TEST_NAME:-aca-pe-storage-test}"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color
BOLD='\033[1m'

clear
echo -e "${BOLD}${MAGENTA}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${MAGENTA}║${NC}  ${BOLD}📦 STORAGE PRIVATE ENDPOINT TEST${NC}                          ${MAGENTA}║${NC}"
echo -e "${BOLD}${MAGENTA}║${NC}  Container: ${YELLOW}$APP_STORAGE${NC}                      ${MAGENTA}║${NC}"
echo -e "${BOLD}${MAGENTA}║${NC}  Target: Storage Account via Private Endpoint              ${MAGENTA}║${NC}"
echo -e "${BOLD}${MAGENTA}╚════════════════════════════════════════════════════════════╝${NC}"
echo -e "${CYAN}Press Ctrl+C to stop${NC}\n"

# Stream logs and format output
az containerapp logs show -g "$RG_APP" -n "$APP_STORAGE" --follow 2>&1 | while IFS= read -r line; do
    # Extract timestamp and log from JSON
    if echo "$line" | grep -q '"Log"'; then
        timestamp=$(echo "$line" | grep -oP '"TimeStamp":\s*"\K[^"]+' | cut -d'.' -f1 | sed 's/T/ /')
        log_content=$(echo "$line" | grep -oP '"Log":\s*"\K[^"]+' | sed 's/^F //')
        
        # Skip if empty or package install messages
        [[ -z "$log_content" ]] && continue
        [[ "$log_content" == *"fetch"* ]] && continue
        [[ "$log_content" == *"Installing"* ]] && continue
        [[ "$log_content" == *"OK:"* ]] && continue
        
        # Format based on content
        if echo "$log_content" | grep -q 'blob.*FQDN=.*privIP=10\.'; then
            # Successfully resolving to private IP
            fqdn=$(echo "$log_content" | grep -oP 'FQDN=\K[^ ]+')
            priv_ip=$(echo "$log_content" | grep -oP 'privIP=\K[^ ]+')
            result_len=$(echo "$log_content" | grep -oP 'list_result_len=\K[0-9]+')
            
            if [[ "$result_len" -gt 100 ]]; then
                echo -e "${GREEN}✅ [${timestamp}] Storage: ${fqdn}${NC}"
                echo -e "${GREEN}   Private IP: ${priv_ip} | Response: ${result_len} bytes${NC}"
            else
                echo -e "${YELLOW}⚠️  [${timestamp}] Storage: ${fqdn}${NC}"
                echo -e "${YELLOW}   Private IP: ${priv_ip} | Response: ${result_len} bytes (small - check auth)${NC}"
            fi
        elif echo "$log_content" | grep -q 'Failed to connect'; then
            echo -e "${RED}❌ [${timestamp}] $log_content${NC}"
        elif echo "$log_content" | grep -q 'error\|Error\|ERROR'; then
            echo -e "${RED}❌ [${timestamp}] $log_content${NC}"
        elif echo "$log_content" | grep -q 'blob'; then
            echo -e "   [${timestamp}] $log_content"
        fi
    fi
done
