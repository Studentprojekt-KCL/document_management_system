import { LOCAL_KEY_LOGOUT_EVENT } from '@/utils/config'
import { apiFetch, API_PATHS } from '@/utils/api'
import { clearAppState } from '@/utils/state'
import { getCurrentUser } from '@/utils/authClient'

export async function hasRole(role) {
  const authInfo = await getCurrentUser()
  if (!authInfo?.authenticated) return false

  const clientRoles = authInfo.user?.client_roles ?? []
  const realmRoles = authInfo.user?.realm_roles ?? []

  return clientRoles.includes(role) || realmRoles.includes(role)
}

export async function refreshSession() {
  try {
    const response = await apiFetch(API_PATHS.authRefresh, {
      method: 'POST'
    })

    return response.ok
  } catch (err) {
    console.error('Error refreshing session:', err)
    return false
  }
}

export async function logout() {
  try {
    await clearAppState()
  } catch (error) {
    console.error('error:', error)
  }
  localStorage.setItem(LOCAL_KEY_LOGOUT_EVENT, Date.now().toString())
  window.location.assign(API_PATHS.authLogout)
  localStorage.removeItem('pkce_verifier')
  localStorage.removeItem('oidc_state')
  
}
