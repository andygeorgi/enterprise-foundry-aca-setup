#!/bin/bash
# ============================================================================
# Stop Azure Container App Proxy
# ============================================================================

set -e

LOCAL_PORT=8080

echo "🛑 Stopping ACA proxy on port ${LOCAL_PORT}..."

if lsof -Pi :${LOCAL_PORT} -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    pkill -f "socat.*${LOCAL_PORT}" || true
    echo "✅ Proxy stopped"
else
    echo "ℹ️  No proxy running on port ${LOCAL_PORT}"
fi
