/**
 * Decode the payload of a JSON Web Token (JWT).
 *
 * @param {string} token - The JWT string.
 * @returns {Object|null} The decoded payload, or null if decoding fails.
 */

import { KEYCLOAK_CLIENT_ID, SESSION_KEY_ACCESS_TOKEN } from '@/utils/config'

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
  return !!sessionStorage.getItem(SESSION_KEY_ACCESS_TOKEN)
}

/* Check if the user has a specific role */
export function hasRole(role) {
  const token = sessionStorage.getItem(SESSION_KEY_ACCESS_TOKEN)
  if (!token) return false

  const payload = decodeJwtPayload(token)
  if (!payload) return false

  const clientRoles = payload?.resource_access?.[KEYCLOAK_CLIENT_ID]?.roles ?? []
  const realmRoles = payload?.realm_access?.roles ?? []

  return clientRoles.includes(role) || realmRoles.includes(role)
}
