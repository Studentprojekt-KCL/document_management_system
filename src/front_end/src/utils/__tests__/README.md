# Utils Tests

## Auth Utility - 19 tests

- Role Verification
- Validates presence and formatting of JWT access tokens.
- Cross-references target roles against Keycloak client configurations.
- Defaults to realm-level role validation if client validation fails.
- Enforces case-sensitive role matching.
- Rejects empty, missing, or malformed JWT payload structures.
- Authentication State
- Confirms active login status strictly via token existence.

## API Utility - 13 tests

- authFetch Wrapper
  - Injects Authorization: Bearer header sourced from localStorage
  - Relays extended fetch configuration options (method, body)
  - Merges native configuration headers with Authorization override
  - Transmits Bearer null if access_token is absent
- saveClassification Method
  - Constructs and transmits POST request to /search_engine/classification
  - Configures Content-Type: application/json header
  - Encodes payload with unique_pointer and target classification
  - Parses and returns JSON on successful response
  - Resolves to empty object if response lacks JSON payload
  - Throws exceptions on non-ok status codes
  - Throws exceptions on network transit failure
- Endpoint Mapping (API_PATHS)
  - Exports classification route
  - Exports search route
  - Exports classifications route
  - Exports rerank route

## AuthSync Utility - 15 tests

- Tab Identification
  - Generates and exports unique non-empty TAB_ID string
- Leader Election & Storage
  - Writes local TAB_ID and current timestamp to localStorage via setLeader
  - Parses and returns leader object via getLeader
  - Returns null on missing or malformed JSON in localStorage
  - Affirms timestamps are current at time of write
  - Returns true from tryBecomeLeader if no leader exists
  - Returns true from tryBecomeLeader if existing leader timestamp is stale
  - Returns false from tryBecomeLeader if existing leader timestamp is valid
  - Confirms active tab leadership status via isLeader
- Activity Broadcasting
  - Updates timestamp via broadcastActivity to current execution time
  - Retrieves most recent cross-tab activity via getLastActivity
  - Defaults to current time if no activity record exists
- Logout Broadcasting
  - Mutates logout-event key in localStorage to trigger cross-tab synchronization

## Config Utility - 12 tests

- Keycloak Configuration
  - Bridges window.__ENV__.FRONTEND_AD_URL to module scope
  - Bridges window.__ENV__.FRONTEND_AD_REALM to module scope
  - Bridges window.__ENV__.FRONTEND_AD_CLIENT_ID to module scope
- Keycloak Route Builders
  - Generates OpenID Connect authorization endpoint via keycloakAuthUrl
  - Generates OpenID Connect token endpoint via keycloakTokenUrl
  - Generates OpenID Connect logout endpoint via keycloakLogoutUrl
- Storage Key Constants
  - Exports SESSION_KEY_ACCESS_TOKEN
  - Exports SESSION_KEY_ID_TOKEN
  - Exports SESSION_KEY_PKCE_VERIFIER
  - Exports SESSION_KEY_OIDC_STATE
  - Exports SESSION_KEY_REFRESH_TOKEN
  - Exports LOCAL_KEY_LOGOUT_EVENT
