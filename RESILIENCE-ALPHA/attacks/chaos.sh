#!/usr/bin/env bash
# Provoked failure (chaos engineering): the MOST RELIABLE scenario for the demo.
# Run ON the host PC (it acts on local Docker), not from the attacker PC.
set -euo pipefail
MODE="${1:-stop}"
case "$MODE" in
  stop)
    echo "Hard-stopping the payment container..."
    docker stop resilience_payment
    echo "payment stopped. The remediation engine must restart it on its own." ;;
  corrupt)
    echo "Corrupting data (deleting transactions)..."
    docker exec resilience_db psql -U "${DB_USER:-resilience_admin}" -d "${DB_NAME:-payment_si}" -c "DELETE FROM transactions;"
    echo "Rows deleted." ;;
  *) echo "Usage: chaos.sh [stop|corrupt]"; exit 1 ;;
esac
