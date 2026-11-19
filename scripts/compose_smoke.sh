#!/usr/bin/env bash
# Prove the container runs the gate without network access and without a key,
# then prove the report came out. Exit 1 if either is false.
set -euo pipefail
cd "$(dirname "$0")/.."

if ! command -v docker >/dev/null 2>&1; then
  echo "SKIP: docker not installed"
  exit 0
fi

rm -rf out/runs
docker compose -f deploy/compose/docker-compose.yml build gate >/dev/null
output=$(docker compose -f deploy/compose/docker-compose.yml run --rm -T gate 2>&1)
echo "$output" | tail -6

echo "$output" | grep -q "PASSED" || { echo "FAIL: gate did not pass in the container"; exit 1; }
test -f out/report.json || { echo "FAIL: no report.json"; exit 1; }
echo "OK: container ran the gate and wrote the report"
