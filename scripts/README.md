# Scripts

## Purpose

This project uses third-party libraries and container images which may contain security vulnerabilities. To reduce security risks, dependencies are supposed to be regularly scanned and updated.

## Vulnerability Management

Dependencies are monitored using:
- Syft (SBOM generation)
- Grype (vulnerability scanning)


Simple helper scripts for SBOM and vulnerability scanning.

## What this folder contains

- `scan.sh`: Basic scan flow (build containers, generate SBOM, run vulnerability scan).
- `full_scan.sh`: Extended scan for each  flow with extra reporting logic.

## Requirements

- Syft
- Grype

## Install Syft and Grype

```bash
curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh
curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh
```

## Run the basic script

**From the `scripts` folder:**

```bash
chmod +x scan.sh
chmod +x full_scan.sh

./scan.sh
./full_scan.sh
```

**From the `document_management_system` folder:** 
- Make sure there is a `remediation_policy.json` file.

```json
{
"policy_name": "Dependency Remediation Policy",
    "remediation_timeframes_days": {
        "critical": 7, 
        "high": 30,
        "medium": 90,
        "low": 180
    },
    "library_update_review_days": 30
}
```

## Output files

The scripts save output in `../documentation/`:

### For `scan.sh`

- `../documentation/simple_scan/sbom.json`
- `../documentation/simple_scan/vulnerabilities.json`

### For `full_scan.sh`

- `../documentation/full_scan/sbom_report.json`
- `../documentation/simple_scan/security_report.json`


## Prerequisites for `full_scan.sh`

`full_scan.sh` scans each container image individually using Syft. For this to work, every service in `docker-compose-build-all.yaml` must have a `build.context` set. Without it, Syft cannot resolve the build files for that image.

Each service should look like this:

```yaml
build:
  context: .
  dockerfile: src/../Dockerfile
```
