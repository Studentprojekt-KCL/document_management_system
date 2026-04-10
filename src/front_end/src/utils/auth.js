/**
 * Decode the payload of a JSON Web Token (JWT).
 *
 * @param {string} token - The JWT string.
 * @returns {Object|null} The decoded payload, or null if decoding fails.
 */

// use env variables from .env
const CLIENT_ID = window.__ENV__.KEYCLOAK_CLIENT_ID
const BASE_URL = window.__ENV__.KEYCLOAK_BASE_URL
const REALM = window.__ENV__.KEYCLOAK_REALM

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

/* Check if the user has a specific role */
export function hasRole(role) {
  const token = sessionStorage.getItem('access_token')
  if (!token) return false

  const payload = decodeJwtPayload(token)
  if (!payload) return false

  const clientRoles = payload?.resource_access?.[CLIENT_ID]?.roles ?? []
  const realmRoles = payload?.realm_access?.roles ?? []

  return clientRoles.includes(role) || realmRoles.includes(role)
}

// For authentication
export function getAccessToken() {
  return sessionStorage.getItem('access_token')
}

export function getRefreshToken() {
  return sessionStorage.getItem('refresh_token')
}

export function saveTokens({ access_token, id_token, refresh_token }) {
  if (access_token) {
    sessionStorage.setItem('access_token', access_token)
  }
  if(id_token){
    sessionStorage.setItem('id_token', id_token)
  }
  if (refresh_token) {
    sessionStorage.setItem('refresh_token', refresh_token)
  }
}

// Token Expiery
export function isTokenExpired(token){
  if(!token) return true
  const payload = decodeJwtPayload(token)
  if(!payload?.exp) return true
  return payload.exp * 1000 < Date.now()
}

// refresh Token
export async function refreshToken(){
  const refresh_token = getRefreshToken()
  const url = `${BASE_URL}/realms/${REALM}/protocol/openid-connect/token`

  const params = new URLSearchParams()
  params.append('grant_type', 'refresh_token')
  params.append('client_id', CLIENT_ID)
  params.append('refresh_token', refresh_token)

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded'
    },
    body: params
  })
  const data = await response.json()
  
  // call the save_tokens function
  saveTokens({
    access_token: data.access_token,
    id_token: data.ide_token,
    refresh_token: data.refresh_token
  })
  return data
}

// logout functionality
export function logout() {
  const idToken = sessionStorage.getItem('id_token')
  const postLogoutRedirectUri = `${window.location.origin}/`

  // 1. clear frontend session
  sessionStorage.removeItem('access_token')
  sessionStorage.removeItem('refresh_token')
  sessionStorage.removeItem('id_token')
  sessionStorage.removeItem('pkce_verifier')
  sessionStorage.removeItem('oidc_state')

  // 2. notify other tabs
  localStorage.setItem('logout-event', Date.now().toString())

  // 3. build logout URL (ALWAYS works)
  let logoutUrl =
    `${BASE_URL}/realms/${REALM}/protocol/openid-connect/logout` +
    `?post_logout_redirect_uri=${encodeURIComponent(postLogoutRedirectUri)}` +
    `&client_id=${encodeURIComponent(CLIENT_ID)}`

  if (idToken) {
    logoutUrl += `&id_token_hint=${encodeURIComponent(idToken)}`
  }

  // 4. redirect to Keycloak
  window.location.assign(logoutUrl)
}