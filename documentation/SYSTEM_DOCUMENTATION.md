# System documentation

## Security implementations

### Security & Dependency Management (ASVS V13.1)

Vulnerability remediation follows a risk-based policy defined in [`remediation_policy.json`](/remediation_policy.json):

| Severity | Timeframe | Rationale |
|----------|-----------|-----------|
| Critical | 7 days | Immediate patching required due to high exploitability |
| High | 30 days | Significant risk, prioritize after critical |
| Medium | 90 days | Moderate risk, address in regular updates |
| Low | 180 days | Low risk, include in standard maintenance cycles |
| Library updates (general) | 30 days | All dependency updates reviewed within 30 days |

### Changing security classifications

Only a user in the defined admin group DMISAPI_ADMIN_ROLES, can update security classifications.

### Rate limiting
<JEPPE>

### Input validation rules

#### Basic authentication input

All service connection using user supplied authentication is validated to have format "<USERNAME>:<PASSWORD>", where this string is validated. Any UTF-8 character is supported for username and password.
