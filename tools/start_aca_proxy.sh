#!/bin/bash
# ============================================================================
# Azure Container App Proxy
# ============================================================================
# This script sets up a local proxy to the ACA file-upload app
# allowing access from the Windows host via port forwarding
# ============================================================================

set -e

ACA_HOSTNAME="aca-file-upload.jollyisland-290223e4.swedencentral.azurecontainerapps.io"
LOCAL_PORT=8080
REMOTE_PORT=80

echo "🔄 Starting ACA proxy..."
echo "   Local:  http://localhost:${LOCAL_PORT}"
echo "   Remote: http://${ACA_HOSTNAME}:${REMOTE_PORT}"
echo ""

# Check if socat is installed
if ! command -v socat &> /dev/null; then
    echo "❌ socat not found, installing..."
    sudo apt-get update && sudo apt-get install -y socat
fi

# Check if port is already in use
if lsof -Pi :${LOCAL_PORT} -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "⚠️  Port ${LOCAL_PORT} is already in use"
    echo "   Killing existing process..."
    sudo kill -9 $(lsof -ti:${LOCAL_PORT}) 2>/dev/null || true
    sleep 1
fi

# Start socat in background
echo "✅ Starting proxy on port ${LOCAL_PORT}..."
nohup socat TCP4-LISTEN:${LOCAL_PORT},fork,reuseaddr TCP4:${ACA_HOSTNAME}:${REMOTE_PORT} \
    > /tmp/aca-proxy.log 2>&1 &

SOCAT_PID=$!
echo "✅ Proxy started (PID: ${SOCAT_PID})"
echo ""
echo "📝 Access the app:"
echo "   From dev container: http://localhost:${LOCAL_PORT}"
echo "   From Windows host:  http://localhost:${LOCAL_PORT} (if port forwarded)"
echo ""
echo "📊 Logs: tail -f /tmp/aca-proxy.log"
echo "🛑 Stop: pkill -f 'socat.*${LOCAL_PORT}'"
