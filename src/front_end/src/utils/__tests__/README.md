# Utils Tests

## Auth Test

- Returns false when no token, empty token, or malformed token
- Checks client roles against the correct Keycloak client ID
- Checks realm roles as fallback
- Returns true when role exists in either client or realm roles
- Returns false when role exists in neither
- Handles missing resource_access and realm_access structures
- Handles completely empty JWT payload
- Role matching is case-sensitive
- Correctly distinguishes between "user" and "admin" roles