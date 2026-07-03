#!/usr/bin/env bash
# Rebuild the static site from all CSVs in lists/ and deploy it live to Netlify.
# Usage: ./deploy.sh
# First run: netlify will ask to create/link a NEW site — pick "Create & configure
# a new project" so it doesn't overwrite the shadow-french site.
set -euo pipefail
cd "$(dirname "$0")"

python3 build_static.py
netlify deploy --dir site --prod
