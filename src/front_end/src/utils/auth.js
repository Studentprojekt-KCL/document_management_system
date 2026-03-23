/**
 * Decode the payload of a JSON Web Token (JWT).
 *
 * @param {string} token - The JWT string.
 * @returns {Object|null} The decoded payload, or null if decoding fails.
 */

const CLIENT_ID = import.meta.env.VITE_CLIENT_ID

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
