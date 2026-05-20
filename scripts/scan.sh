#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCS_DIR="$ROOT_DIR/documentation/simple_scan"
COMPOSE_FILE="$ROOT_DIR/docker-compose-build-all.yaml"

mkdir -p "$DOCS_DIR"
cd "$ROOT_DIR"

echo "======================================"
echo "Build containers"
echo "======================================"

docker compose -f "$COMPOSE_FILE" build

echo "======================================"
echo "Generate SBOM (ALL dependencies)"
echo "======================================"

syft . \
  --exclude="./.git" \
  --exclude="./tests" \
  --exclude="./.tox" \
  --exclude="./node_modules" \
  --exclude="./dist" \
  -o syft-json > "$DOCS_DIR/sbom.json"

echo "======================================"
echo "Vulnerability scan"
echo "======================================"

grype sbom:"$DOCS_DIR/sbom.json" \
-o json > "$DOCS_DIR/vulnerabilities.json"

echo "======================================"
echo "DONE"
echo "======================================"
echo "$DOCS_DIR/sbom.json"
echo "$DOCS_DIR/vulnerabilities.json"
echo "======================================"

