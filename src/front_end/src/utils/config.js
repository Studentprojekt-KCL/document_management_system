/**
 * Generic OIDC config.
 * Works with Keycloak, Microsoft Entra ID, or another OIDC-compliant provider.
 */

export const FRONTEND_OIDC_ISSUER_URL = window.__ENV__.FRONTEND_OIDC_ISSUER_URL.replace(/\/$/, '')
export const FRONTEND_OIDC_CLIENT_ID = window.__ENV__.FRONTEND_OIDC_CLIENT_ID

export const SESSION_KEY_PKCE_VERIFIER = 'oidc_pkce_verifier'
export const SESSION_KEY_OIDC_STATE = 'oidc_state'
export const LOCAL_KEY_LOGOUT_EVENT = 'logout-event'

let cachedMetadata = null

export async function getOidcMetadata() {
  if (cachedMetadata) {
    return cachedMetadata
  }

  const response = await fetch(`${FRONTEND_OIDC_ISSUER_URL}/.well-known/openid-configuration`)

  if (!response.ok) {
    throw new Error('Failed to load OIDC metadata')
  }

  cachedMetadata = await response.json()
  return cachedMetadata
}
