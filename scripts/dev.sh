#!/usr/bin/env bash
# Dev helpers for MaoMaoNotify. Usage: scripts/dev.sh <up|down|server|logs>
set -euo pipefail
cd "$(dirname "$0")/.."

case "${1:-}" in
  up)     docker compose up -d ;;
  down)   docker compose down ;;
  logs)   docker compose logs -f "${2:-server}" ;;
  server) cd server && uv run uvicorn app.main:app --reload ;;
  *)      echo "usage: $0 <up|down|server|logs>" >&2; exit 1 ;;
esac
