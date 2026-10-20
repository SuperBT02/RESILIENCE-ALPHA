#!/usr/bin/env bash
# SQL injection attempts: blocked by the WAF (403) and impossible in code
# (parameterised queries). Signal: spike of WAF blocks / 4xx.
set -euo pipefail
TARGET="$1"; DURATION="${2:-60}"
echo "SQL injection -> http://$TARGET/api/ for ${DURATION}s"
PAYLOADS=("1' OR '1'='1" "1; DROP TABLE transactions;--" "' UNION SELECT NULL--" "admin'--")
end=$(( $(date +%s) + DURATION ))
while [ "$(date +%s)" -lt "$end" ]; do
  for p in "${PAYLOADS[@]}"; do
    curl -s -o /dev/null -G "http://$TARGET/api/pay" --data-urlencode "sender_id=$p"
  done
  sleep 1
done
echo "Injection done (blocked at WAF if all goes well)."
# sqlmap variant:
# sqlmap -u "http://$TARGET/api/pay" --data='{"sender_id":"1","receiver_id":"2","amount":1}' --batch
