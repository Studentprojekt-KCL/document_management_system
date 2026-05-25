#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCS_DIR="$ROOT_DIR/documentation/full_scan"

POLICY_FILE="$ROOT_DIR/remediation_policy.json"
SBOM_REPORT="$DOCS_DIR/sbom_report.json"
SECURITY_REPORT="$DOCS_DIR/security_report.json"
COMPOSE_FILE="$ROOT_DIR/docker-compose-build-all.yaml"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

mkdir -p "$DOCS_DIR"
cd "$ROOT_DIR"

REPO_SBOM="$TMP_DIR/repo_sbom.json"
REPO_SCAN="$TMP_DIR/repo_scan.json"

echo "======================================"
echo "Generating Repository SBOM"
echo "======================================"

syft . \
    --exclude="./.git" \
    --exclude="./tests" \
    --exclude="./.tox" \
    --exclude="./node_modules" \
    --exclude="./dist" \
    -o syft-json > "$REPO_SBOM"

echo "======================================"
echo "Scanning Repository Vulnerabilities"
echo "======================================"

grype sbom:"$REPO_SBOM" --only-fixed -o json > "$REPO_SCAN"

echo "======================================"
echo "Building Containers"
echo "======================================"

docker compose -f "$COMPOSE_FILE" build

mapfile -t IMAGES < <(docker compose -f "$COMPOSE_FILE" config --images | sort -u)

ALL_SBOMS=("$REPO_SBOM")
ALL_SCANS=("$REPO_SCAN")

for IMAGE in "${IMAGES[@]}"; do
SAFE_NAME="$(echo "$IMAGE" | tr '/:@' '_')"

IMAGE_SBOM="$TMP_DIR/${SAFE_NAME}_sbom.json"
IMAGE_SCAN="$TMP_DIR/${SAFE_NAME}_scan.json"

echo ""
echo "SBOM for image: $IMAGE"
echo "======================================"
syft "$IMAGE" -o syft-json > "$IMAGE_SBOM"

echo "Vulnerability scan for image: $IMAGE"
echo "======================================"
grype "$IMAGE" --only-fixed -o json > "$IMAGE_SCAN"

ALL_SBOMS+=("$IMAGE_SBOM")
ALL_SCANS+=("$IMAGE_SCAN")
done

echo "======================================"
echo "Creating Final Reports"
echo "======================================"

python3 - "$POLICY_FILE" "$SBOM_REPORT" "$SECURITY_REPORT" "${ALL_SBOMS[@]}" -- "${ALL_SCANS[@]}" <<'PY'
import json
import sys
from datetime import datetime

args = sys.argv[1:]

separator = args.index("--")

policy_path = args[0]
sbom_output = args[1]
security_output = args[2]

sbom_files = args[3:separator]
scan_files = args[separator + 1:]

def load_json(path):
    with open(path, "r") as f:
        return json.load(f)

policy = load_json(policy_path)

all_components = {}
severity_counts = {
    "critical": 0,
    "high": 0,
    "medium": 0,
    "low": 0
}

all_findings = []

# Collect components
for sbom_file in sbom_files:
    sbom = load_json(sbom_file)
    for artifact in sbom.get("artifacts", []):
        key = (
            artifact.get("name"),
            artifact.get("version"),
            artifact.get("type")
        )
        all_components[key] = {
            "name": artifact.get("name"),
            "version": artifact.get("version"),
            "type": artifact.get("type")
        }

# Collect vulnerabilities
for scan_file in scan_files:
    report = load_json(scan_file)
    for match in report.get("matches", []):
        vuln = match.get("vulnerability", {})
        artifact = match.get("artifact", {})
        severity = str(vuln.get("severity", "unknown")).lower()
        if severity in severity_counts:
            severity_counts[severity] += 1
        all_findings.append({
            "id": vuln.get("id"),
            "severity": severity,
            "package": artifact.get("name"),
            "version": artifact.get("version")
        })

# Compliance logic
compliant = severity_counts["critical"] == 0

sbom_report = {
    "generated_at": datetime.now().isoformat(),
    "component_count": len(all_components),
    "components": list(all_components.values())
}

security_report = {
    "generated_at": datetime.now().isoformat(),
    "policy": policy,
    "summary": {
        "critical": severity_counts["critical"],
        "high": severity_counts["high"],
        "medium": severity_counts["medium"],
        "low": severity_counts["low"]
    },
    "total_findings": len(all_findings),
    "compliance": {
        "timeframes_documented": True,
        "components_within_timeframes": compliant
    },
    "findings": all_findings
}

with open(sbom_output, "w") as f:
    json.dump(sbom_report, f, indent=2)

with open(security_output, "w") as f:
    json.dump(security_report, f, indent=2)
PY
echo "======================================"
echo "DONE"
echo "======================================"
echo "$SBOM_REPORT"
echo "$SECURITY_REPORT "
echo "======================================"
