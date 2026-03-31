/**
 * Decode the payload of a JSON Web Token (JWT).
 *
 * @param {string} token - The JWT string.
 * @returns {Object|null} The decoded payload, or null if decoding fails.
 */

const KEYCLOAK_BASE = import.meta.env.KEYCLOAK_BASE_URL
const REALM = import.meta.env.KEYCLOAK_REALM
const CLIENT_ID = import.meta.env.KEYCLOAK_CLIENT_ID

const TOKEN_URL = `${KEYCLOAK_BASE}/realms/${REALM}/protocol/openid-connect/token`

function storeTokens(data) {
  if (data.access_token) {
    sessionStorage.setItem('access_token', data.access_token)
  }

  if (data.refresh_token) {
    sessionStorage.setItem('refresh_token', data.refresh_token)
  }

  if (data.id_token) {
    sessionStorage.setItem('id_token', data.id_token)
  }

  if (data.expires_in) {
    const expiresAt = Date.now() + data.expires_in * 1000
    sessionStorage.setItem('expires_at', expiresAt.toString())
  }
}

function clearAuth() {
  sessionStorage.removeItem('access_token')
  sessionStorage.removeItem('refresh_token')
  sessionStorage.removeItem('id_token')
  sessionStorage.removeItem('expires_at')
  sessionStorage.removeItem('pkce_verifier')
  sessionStorage.removeItem('oidc_state')

  localStorage.setItem('logout_event', Date.now().toString())
}

/* Generic Token Request */

async function requestToken(params) {
  const body = new URLSearchParams(params)

  const response = await fetch(TOKEN_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded'
    },
    body: body.toString()
  })

  const data = await response.json()

  if (!response.ok) {
    throw new Error(`${data.error || response.status} ${data.error_description || ''}`)
  }

  storeTokens(data)
  return data
}

/* Exchange authorization code for tokens (login) */
export async function exchangeCodeForToken(code, verifier, redirectUri) {
  return await requestToken({
    grant_type: 'authorization_code',
    client_id: CLIENT_ID,
    code,
    redirect_uri: redirectUri,
    code_verifier: verifier
  })
}

/*Refresh access token using refresh token */
export async function refreshTokenRequest(refreshToken) {
  try {
    const data = await requestToken({
      grant_type: 'refresh_token',
      client_id: CLIENT_ID,
      refresh_token: refreshToken
    })

    return data.access_token
  } catch (error) {
    console.error('Refresh failed:', error)

    // If refresh fails → force logout
    clearAuth()
    window.location.href = '/' // send user to login page 

    return null
  }
}

/* Get a valid access token (refresh if needed) */
let refreshPromise = null
export async function getValidToken() {
  const accessToken = sessionStorage.getItem('access_token')
  const refreshToken = sessionStorage.getItem('refresh_token')
  const expiresAt = sessionStorage.getItem('expires_at')

  if (!accessToken || !refreshToken) {
    return null
  }

  // Refresh if token expires within 10 seconds
  const isExpiringSoon = expiresAt && Date.now() + 10000 > parseInt(expiresAt)
  if (isExpiringSoon) {
    if (!refreshPromise) {
      refreshPromise = refreshTokenRequest(refreshToken).finally(() => {
        refreshPromise = null
      })
    }
    await refreshPromise
  }
  return accessToken
}

/* Authenticated fetch wrapper */

export async function authFetch(url, options = {}) {
  const token = await getValidToken()

  if (!token) {
    clearAuth()
    window.location.href = '/'
    return null
  }

  return fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      Authorization: `Bearer ${token}`
    }
  })
}

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
