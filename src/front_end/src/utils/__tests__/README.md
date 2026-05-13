# Utils Tests

## API Utility - 15 tests

- apiFetch Wrapper
  - Calls fetch with `credentials: 'include'`
  - Passes through additional options (method, body)
  - Merges custom headers
  - Returns the fetch response
- authFetch
  - Confirmed as identity alias for apiFetch (no Bearer token logic)
- Endpoint Mapping (API_PATHS)
  - Exports search, classifications, classification, rerank, summarize routes
  - Exports authCheck, authMe, authRefresh, authLogout, codeExchange routes

## Auth Utility - 19 tests

- Role Verification (hasRole)
  - Calls getCurrentUser() API to fetch auth info
  - Returns false when unauthenticated or API unavailable
  - Checks client_roles and realm_roles from the user object
  - Returns true if role exists in either roles array
  - Enforces case-sensitive role matching
  - Handles missing or empty roles arrays
- Session Refresh
  - POSTs to /auth/refresh, returns boolean on success/failure/network error
- Logout
  - Sets logout-event in localStorage
  - Clears pkce_verifier and oidc_state from localStorage
  - Redirects to logout_url when provided
  - Falls back to "/" on any error or missing logout_url

## AuthClient Utility - 17 tests

- exchangeAuthorizationCode
  - POSTs code + code_verifier as URL-encoded form data to /auth/codeExchange
  - Returns `{ ok: true, data }` on success
  - Returns `{ ok: false, status, message }` on API error
  - Handles JSON parse failures and network errors gracefully
- isAuthenticated
  - GETs /auth/check and returns boolean based on `authenticated` flag
  - Returns false on non-ok response, network error, or parse failure
- getCurrentUser
  - GETs /auth/me and returns parsed user data
  - Returns null on non-ok response or network error

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

## Config Utility - 8 tests

- Keycloak Configuration
  - Bridges window.__ENV__.FRONTEND_AD_URL to module scope
  - Bridges window.__ENV__.FRONTEND_AD_REALM to module scope
  - Bridges window.__ENV__.FRONTEND_AD_CLIENT_ID to module scope
- Keycloak Route Builders
  - Generates OpenID Connect authorization endpoint via keycloakAuthUrl
  - Generates OpenID Connect logout endpoint via keycloakLogoutUrl
- Storage Key Constants
  - Exports SESSION_KEY_PKCE_VERIFIER
  - Exports SESSION_KEY_OIDC_STATE
  - Exports LOCAL_KEY_LOGOUT_EVENT

## PKCE Utility - 11 tests

- createPkcePair
  - Returns object with verifier and challenge strings
  - Verifier and challenge are unique, non-empty, and different from each other
  - Generates unique pairs on each call
  - Uses only URL-safe base64 characters (no +, /, or padding)
- generateState
  - Returns a unique non-empty URL-safe string
