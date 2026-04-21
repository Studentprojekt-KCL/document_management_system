/**
 * Decode the payload of a JSON Web Token (JWT).
 *
 * @param {string} token - The JWT string.
 * @returns {Object|null} The decoded payload, or null if decoding fails.
 */
import {
  KEYCLOAK_CLIENT_ID,
  KEYCLOAK_BASE,
  KEYCLOAK_REALM,
  keycloakLogoutUrl,
  SESSION_KEY_ACCESS_TOKEN,
  SESSION_KEY_ID_TOKEN,
  SESSION_KEY_PKCE_VERIFIER,
  SESSION_KEY_OIDC_STATE,
  LOCAL_KEY_LOGOUT_EVENT
} from '@/utils/config'

/* Read the JSON Web Token */
function decodeJwtPayload(token) {
  try {
    const base64Url = token.split('.')[1]
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), '=')
    return JSON.parse(atob(padded))
  } catch {
    return null
  }
}

/** Returns true if the user currently has a valid access token in sessionStorage. */
export function isLoggedIn() {
  return !!localStorage.getItem(SESSION_KEY_ACCESS_TOKEN)
}

/* Check if the user has a specific role */
export function hasRole(role) {
  const token = localStorage.getItem(SESSION_KEY_ACCESS_TOKEN)
  if (!token) return false

  const payload = decodeJwtPayload(token)
  if (!payload) return false

  const clientRoles = payload?.resource_access?.[FRONTEND_AD_CLIENT_ID]?.roles ?? []
  const realmRoles = payload?.realm_access?.roles ?? []

  return clientRoles.includes(role) || realmRoles.includes(role)
}

// For authentication
export function getAccessToken() {
  return localStorage.getItem('access_token')
}

export function getRefreshToken() {
  return localStorage.getItem('refresh_token')
}

export function saveTokens({ access_token, id_token, refresh_token }) {
  if (access_token) {
    localStorage.setItem('access_token', access_token)
  }
  if (id_token) {
    localStorage.setItem('id_token', id_token)
  }
  if (refresh_token) {
    localStorage.setItem('refresh_token', refresh_token)
  }
}

// Token Expiery
export function isTokenExpired(token) {
  if (!token) return true
  const payload = decodeJwtPayload(token)
  if (!payload?.exp) return true
  return payload.exp * 1000 < Date.now()
}

// refresh Token
export async function refreshToken() {
  const refresh_token = getRefreshToken()

  const url = `${KEYCLOAK_BASE}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/token`

  const params = new URLSearchParams()
  params.append('grant_type', 'refresh_token')
  params.append('client_id', KEYCLOAK_CLIENT_ID)
  params.append('refresh_token', refresh_token)

  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: params
  })

  const data = await response.json()

  localStorage.setItem('access_token', data.access_token)
  localStorage.setItem('refresh_token', data.refresh_token)
  localStorage.setItem('id_token', data.id_token)

  return data
}

// logout functionality
export function logout() {
  const idToken = localStorage.getItem(SESSION_KEY_ID_TOKEN)
  const postLogoutRedirectUri = `${window.location.origin}/`

  localStorage.removeItem(SESSION_KEY_ACCESS_TOKEN)
  localStorage.removeItem(SESSION_KEY_ID_TOKEN)
  localStorage.removeItem(SESSION_KEY_PKCE_VERIFIER)
  localStorage.removeItem(SESSION_KEY_OIDC_STATE)

  localStorage.setItem(LOCAL_KEY_LOGOUT_EVENT, Date.now().toString())

  if (idToken) {
    const logoutUrl =
      keycloakLogoutUrl() +
      `?id_token_hint=${encodeURIComponent(idToken)}` +
      `&post_logout_redirect_uri=${encodeURIComponent(postLogoutRedirectUri)}` +
      `&client_id=${encodeURIComponent(KEYCLOAK_CLIENT_ID)}`

    window.location.assign(logoutUrl)
    return
  }
}
