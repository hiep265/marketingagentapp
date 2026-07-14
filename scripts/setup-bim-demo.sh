#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

COMPOSE="${COMPOSE:-docker-compose}"
if ! $COMPOSE ps >/dev/null 2>&1; then
  COMPOSE="sudo docker-compose"
fi

$COMPOSE up -d --build bim-neo4j bim-ingest-service

echo "Waiting for BIM ingest service..."
for _ in $(seq 1 60); do
  if curl -fsS http://127.0.0.1:8095/healthz >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

curl -fsS \
  -H 'content-type: application/json' \
  -H 'x-api-key: bim-dev-key' \
  -d '{"path":"/workspace/sample-bim/demo_office.ifc","replace":true}' \
  http://127.0.0.1:8095/projects/demo-office/ingest

echo
echo "BIM demo is ready. Try project_id=demo-office."
