#!/usr/bin/env bash
# Brute force on /auth/login -> spike of 401s detected by the ML engine.
set -euo pipefail
TARGET="$1"; DURATION="${2:-90}"
echo "Brute force -> http://$TARGET/auth/login for ${DURATION}s"
end=$(( $(date +%s) + DURATION )); i=0
while [ "$(date +%s)" -lt "$end" ]; do
  i=$((i+1))
  curl -s -o /dev/null -X POST "http://$TARGET/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"alice_merchant\",\"password\":\"wrong-$i\"}" &
  [ $((i % 20)) -eq 0 ] && sleep 1
done
wait
echo "Brute force done ($i attempts)."
# hydra variant:
# hydra -l alice_merchant -P rockyou.txt "$TARGET" http-post-form \
#   "/auth/login:username=^USER^&password=^PASS^:Invalid credentials"
