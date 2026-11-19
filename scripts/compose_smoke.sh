#!/usr/bin/env bash
# Prove the container runs the gate without network access and without a key,
# then prove the report came out. Exit 1 if either is false.
set -euo pipefail
cd "$(dirname "$0")/.."

if ! command -v docker >/dev/null 2>&1; then
  echo "SKIP: docker not installed"
  exit 0
fi

# The bind mount must exist and belong to us before the container writes into it.
export DOCKER_UID="$(id -u)" DOCKER_GID="$(id -g)"
mkdir -p out
rm -rf out/runs out/report.html out/report.json

docker compose -f deploy/compose/docker-compose.yml build smoke >/dev/null
if ! output=$(docker compose -f deploy/compose/docker-compose.yml run --rm -T smoke 2>&1); then
  echo "$output" | tail -25
  echo "FAIL: the container exited non-zero"
  exit 1
fi
echo "$output" | tail -6

echo "$output" | grep -q "PASSED" || { echo "FAIL: gate did not pass in the container"; exit 1; }
echo "$output" | grep -q "report:" || { echo "FAIL: container did not write a report"; exit 1; }
test -f out/report.json || { echo "FAIL: no report.json"; exit 1; }
echo "OK: container ran the gate and wrote the report"
