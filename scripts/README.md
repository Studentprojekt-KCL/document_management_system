# Scripts

## Purpose

This project uses third-party libraries and container images which may contain security vulnerabilities. To reduce security risks, dependencies are supposed to be regularly scanned and updated.

## Vulnerability Management

Dependencies are monitored using:
- Syft (SBOM generation)
- Grype (vulnerability scanning)


## This folder contains

Simple helper scripts for SBOM and vulnerability scanning.

- `scan.sh`: Basic scan flow for the repo (build containers, generate SBOM, run vulnerability scan).
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
- Make sure there is a `remediation_policy.json` file containing remediation timeframes. Eg.

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

## Security & Dependency Management (ASVS V13.1)

Vulnerability remediation follows a risk-based policy defined in [`remediation_policy.json`](/remediation_policy.json):

| Severity | Timeframe | Rationale |
|----------|-----------|-----------|
| Critical | 7 days | Immediate patching required due to high exploitability |
| High | 30 days | Significant risk, prioritize after critical |
| Medium | 90 days | Moderate risk, address in regular updates |
| Low | 180 days | Low risk, include in standard maintenance cycles |
| Library updates (general) | 30 days | All dependency updates reviewed within 30 days |

Run `./full_scan.sh` to generate compliance reports in `../documentation/full_scan/`:
- `security_report.json` — vulnerability findings with compliance status
- `sbom_report.json` — full software bill of materials

## Prerequisites for `full_scan.sh`

`full_scan.sh` scans each container image individually using Syft. For this to work, every service in `docker-compose-build-all.yaml` must have a `build.context` set. Without it Syft can't resolve the build files for that image.

Each service should look like this:

```yaml
build:
  context: .
  dockerfile: src/../Dockerfile
```

## NOTE
We do install the newest packages during build time, but some of their sub-dependencies or even subsub-dependencies may still be old or vulnerable. With help of Syft and Grype scans it is possible to review the reports.