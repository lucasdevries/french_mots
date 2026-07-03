#!/usr/bin/env bash
# Rebuild and preview the site locally (free, no deploy).
# Usage: ./run.sh   -> http://localhost:8002
set -euo pipefail
cd "$(dirname "$0")"

python3 build_static.py
open "http://localhost:8002" 2>/dev/null || true
cd site && python3 -m http.server 8002
