#!/bin/bash
# ============================================================================
# Stop Azure Container App Proxy
# ============================================================================

set -e

# Configuration: Must match start_aca_proxy.sh
declare -a PORTS=(
    "8080"
    "8081"
)

echo "🛑 Stopping ACA proxies..."
echo ""

STOPPED=false

for PORT in "${PORTS[@]}"; do
    if lsof -Pi :${PORT} -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        pkill -f "socat.*${PORT}" || true
        echo "✅ Proxy stopped on port ${PORT}"
        STOPPED=true
    else
        echo "ℹ️  No proxy running on port ${PORT}"
    fi
done

echo ""
if [ "$STOPPED" = true ]; then
    echo "✅ All active proxies stopped"
else
    echo "ℹ️  No proxies were running"
fi
