/**
 * PKCE (Proof Key for Code Exchange) util for the OAuth2 authorization flow.
 * Extracted here from loginview.vue so the crypto logic is reusable.
 */

function base64UrlEncode(buffer) {
  return btoa(String.fromCharCode(...new Uint8Array(buffer)))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/g, '')
}

/* SHA-256 hashing function for PKCE challenge generation. */
async function sha256(input) {
  const data = new TextEncoder().encode(input)
  return await crypto.subtle.digest('SHA-256', data)
}

/* Generates a random string of specified byte length, used for PKCE verifier and state. */
function randomString(bytesLen = 32) {
  const bytes = new Uint8Array(bytesLen)
  crypto.getRandomValues(bytes)
  return base64UrlEncode(bytes)
}

/**
 * Creates a PKCE pair (verifier and challenge) for secure OAuth authentication.
 * @returns {{ verifier: string, challenge: string }}
 */
export async function createPkcePair() {
  const verifier = randomString(64)
  const challenge = base64UrlEncode(await sha256(verifier))
  return { verifier, challenge }
}

/**
 * Generates a random state string for CSRF prevention.
 * @returns {string}
 */
export function generateState() {
  return randomString(32)
}
