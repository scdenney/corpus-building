#!/bin/bash
# ============================================================================
# vllm_health_check.sh — poll a vLLM /health endpoint until ready
#
# Usage:
#   vllm_health_check.sh [--host HOST] [--port PORT] [--timeout SECONDS]
#                        [--pid PID]
#
# Defaults: host=127.0.0.1, port=8000, timeout=900 (covers ~13 min ZFS cold
# start on ALICE A100). Exits 0 when /health responds, 1 on timeout or if
# --pid is provided and that process dies.
#
# Reference: the `alice-vllm-deploy` skill ("Cold Start Timeline" section)
# documents why 900s is the recommended default.
# ============================================================================

set -euo pipefail

HOST="127.0.0.1"
PORT="8000"
TIMEOUT=900
VLLM_PID=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --host)    HOST="$2"; shift 2 ;;
        --port)    PORT="$2"; shift 2 ;;
        --timeout) TIMEOUT="$2"; shift 2 ;;
        --pid)     VLLM_PID="$2"; shift 2 ;;
        -h|--help)
            sed -n '3,14p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 2
            ;;
    esac
done

URL="http://${HOST}:${PORT}/health"
echo "Polling ${URL} (timeout ${TIMEOUT}s)..."

for i in $(seq 1 "${TIMEOUT}"); do
    if curl -s "${URL}" >/dev/null 2>&1; then
        echo "vLLM server ready after ${i}s"
        exit 0
    fi
    if [ -n "${VLLM_PID}" ] && ! kill -0 "${VLLM_PID}" 2>/dev/null; then
        echo "ERROR: process ${VLLM_PID} is no longer running" >&2
        exit 1
    fi
    sleep 1
done

echo "ERROR: vLLM server not ready after ${TIMEOUT}s" >&2
exit 1
