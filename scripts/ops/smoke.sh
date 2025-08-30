#!/usr/bin/env bash
set -euo pipefail
base="${1:-http://127.0.0.1:8001}"

curl -fsS "$base/health" >/dev/null

miami_count=$(curl -fsS "$base/markets?q=miami&state=FL&limit=5" | jq '.count')
[[ "$miami_count" -ge 1 ]]

keystone_count=$(curl -fsS "$base/markets?lat=28.1&lon=-82.6&radius_miles=25&limit=200" | jq '.count')
snap_count=$(curl -fsS "$base/markets?q=miami&state=FL&accepts_snap=true&limit=50" | jq '.count')

echo "OK: /health + queries (miami_count=${miami_count}, keystone_count=${keystone_count}, miami_snap=${snap_count})."
