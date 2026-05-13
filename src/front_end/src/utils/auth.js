import { LOCAL_KEY_LOGOUT_EVENT } from '@/utils/config'
import { apiFetch, API_PATHS } from '@/utils/api'

/* ADMIN roles checking */
export async function isAdmin() {
  try {
    const response = await apiFetch(API_PATHS.checkAdmin)
    if (!response.ok) {
      return false
    }
    const data = await response.json()
    return data.admin === true
  } catch (err) {
    console.error('failed admin check:', err)
    return false
  }
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
  localStorage.setItem(LOCAL_KEY_LOGOUT_EVENT, Date.now().toString())

  localStorage.removeItem('pkce_verifier')
  localStorage.removeItem('oidc_state')

  try {
    const response = await apiFetch(API_PATHS.authLogout, {
      method: 'POST',
      credentials: 'include'
    })

    if (!response.ok) {
      window.location.href = '/'
      return
    }

    const data = await response.json()

    if (data.logout_url) {
      window.location.href = data.logout_url
      return
    }

    window.location.href = '/'
  } catch (err) {
    console.error('Logout failed:', err)
    window.location.href = '/'
  }
}
