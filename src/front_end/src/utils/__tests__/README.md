# Utils Tests

## PKCE Utility - 11 tests

- createPkcePair
  - Returns object with verifier and challenge strings
  - Verifier and challenge are unique, non-empty, and different from each other
  - Generates unique pairs on each call
  - Uses only URL-safe base64 characters (no +, /, or padding)
- generateState
  - Returns a unique non-empty URL-safe string
