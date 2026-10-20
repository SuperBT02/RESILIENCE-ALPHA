#!/usr/bin/env bash
# Attack launcher — USE ONLY AGAINST YOUR OWN LAB on the RESILIENCE-G<n> network.
#   ./run.sh <bruteforce|injection|flood|chaos> <host-ip>
set -euo pipefail
SCENARIO="${1:-}"; TARGET="${2:-}"
DIR="$(cd "$(dirname "$0")" && pwd)"
[ -z "$SCENARIO" ] && { echo "Usage: $0 <bruteforce|injection|flood|chaos> <host-ip>"; exit 1; }
echo ">>> [$(date -Is)] start attack '$SCENARIO' on ${TARGET:-local}"
case "$SCENARIO" in
  bruteforce) "$DIR/bruteforce.sh" "$TARGET" ;;
  injection)  "$DIR/injection.sh" "$TARGET" ;;
  flood)      "$DIR/flood.sh" "$TARGET" ;;
  chaos)      "$DIR/chaos.sh" "${2:-stop}" ;;
  *) echo "Unknown scenario"; exit 1 ;;
esac
echo ">>> [$(date -Is)] end attack '$SCENARIO'"
