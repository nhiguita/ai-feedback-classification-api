#!/usr/bin/env bash
# Send each example request to a running API and save the real response next to it.
# Usage: start the API (uvicorn app.main:app --port 8000), then: bash examples/run_examples.sh [base_url]
set -euo pipefail

BASE_URL="${1:-http://localhost:8000}"
DIR="$(cd "$(dirname "$0")" && pwd)"

for request in "$DIR"/*.request.json; do
  name="$(basename "$request" .request.json)"
  curl -s -X POST "$BASE_URL/api/v1/feedback/analyze" \
    -H "Content-Type: application/json" \
    --data @"$request" | python3 -m json.tool > "$DIR/$name.response.json"
  echo "$name: $(tr -d '\n ' < "$DIR/$name.response.json")"
done
