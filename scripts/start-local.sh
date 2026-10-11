#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [ ! -d node_modules ]; then npm ci; fi
npm run build
if [ -f .local/runtime.env ]; then
  set -a
  source .local/runtime.env
  set +a
fi
if [ -x .local/venv/bin/python ]; then
  exec .local/venv/bin/python backend/server.py
fi
exec python3 backend/server.py
