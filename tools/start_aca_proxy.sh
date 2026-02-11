#!/bin/bash
# ============================================================================
# Azure Container App Proxy
# ============================================================================
# This script sets up local proxies to ACA apps
# allowing access from the Windows host via port forwarding
# ============================================================================

set -e

# Load environment variables from .env
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/.env" ]; then
    set -a
    source "$SCRIPT_DIR/.env"
    set +a
else
    echo "❌ .env not found. Run ./tools/generate-env.sh first."
    exit 1
fi

ACA_STATIC_IP="${ACA_STATIC_IP:?Error: ACA_STATIC_IP not set. Run ./tools/generate-env.sh first.}"
FILE_UPLOAD_FQDN="${FILE_UPLOAD_FQDN:?Error: FILE_UPLOAD_FQDN not set. Run ./tools/generate-env.sh first.}"

# Configuration: proxy definitions built from .env
# ACA internal ingress requires HTTPS (port 443) with SNI
# Forward to ACA static IP directly (not FQDN) to avoid DNS loop
# Format: "local_port:remote_ip:remote_port"
declare -a PROXIES=(
    "443:${ACA_STATIC_IP}:443"
)

echo "🔄 Starting ACA proxies..."
echo ""

# Check if socat is installed
if ! command -v socat &> /dev/null; then
    echo "❌ socat not found, installing..."
    sudo apt-get update && sudo apt-get install -y socat
fi

declare -a PIDS=()
declare -a PORTS=()

# Loop through each proxy configuration
for proxy in "${PROXIES[@]}"; do
    IFS=':' read -r LOCAL_PORT REMOTE_HOST REMOTE_PORT <<< "$proxy"
    
    echo "📍 Setting up proxy: localhost:${LOCAL_PORT} -> ${REMOTE_HOST}:${REMOTE_PORT}"
    
    # Check if port is already in use
    if lsof -Pi :${LOCAL_PORT} -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo "   ⚠️  Port ${LOCAL_PORT} is already in use, killing existing process..."
        sudo kill -9 $(lsof -ti:${LOCAL_PORT}) 2>/dev/null || true
        sleep 1
    fi
    
    # Start socat in background (sudo needed for privileged ports like 443)
    LOG_FILE="/tmp/aca-proxy-${LOCAL_PORT}.log"
    sudo nohup socat TCP4-LISTEN:${LOCAL_PORT},fork,reuseaddr TCP4:${REMOTE_HOST}:${REMOTE_PORT} \
        > ${LOG_FILE} 2>&1 &
    
    PID=$!
    PIDS+=($PID)
    PORTS+=($LOCAL_PORT)
    
    echo "   ✅ Proxy started (PID: ${PID})"
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ All proxies started successfully"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📝 Access URLs:"
for port in "${PORTS[@]}"; do
    echo "   http://localhost:${port}"
done
echo ""
echo "📊 View logs:"
for port in "${PORTS[@]}"; do
    echo "   tail -f /tmp/aca-proxy-${port}.log"
done
echo ""
echo "🛑 Stop all: ./tools/stop_aca_proxy.sh"
