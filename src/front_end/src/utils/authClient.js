/**
 * Frontend auth client for mainAPI cookie-based authentication.
 *
 * This file does not read or store access tokens in the frontend.
 * It only communicates with mainAPI using credentials: 'include'.
 */

// Temporary
const MAIN_API_BASE_URL = 'http://localhost:8000'

/**
 * Internal helper for auth-related API calls.
 *
 * @param {string} path
 * @param {RequestInit} options
 * @returns {Promise<Response>}
 */
//import { apiFetch, API_PATHS } from '@/utils/api'

async function authRequest(path, options = {}) {
  return fetch(`${MAIN_API_BASE_URL}${path}`, {
    credentials: 'include',
    ...options,
    headers: {
      ...(options.headers || {})
    }
  })
}

/**
 * Exchange OAuth authorization code + PKCE verifier for backend cookies.
 *
 * mainAPI performs the token exchange with Keycloak and stores tokens
 * in HTTP-only cookies.
 *
 * @param {Object} params
 * @param {string} params.code
 * @param {string} params.codeVerifier
 * @returns {Promise<{ ok: true, data: any } | { ok: false, status: number, message: string }>}
 */

export async function exchangeAuthorizationCode({ code, codeVerifier }) {
  try {
    //const response = await apiFetch(API_PATHS.codeExchange,
    const response = await authRequest('/auth/codeExchange', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: new URLSearchParams({
        code,
        code_verifier: codeVerifier
      })
    })

    let data = null
    try {
      data = await response.json()
    } catch {
      data = null
    }

    if (!response.ok) {
      return {
        ok: false,
        status: response.status,
        message: data?.message || 'Code exchange failed'
      }
    }

    return { ok: true, data }
  } catch (error) {
    return {
      ok: false,
      status: 0,
      message: `Network error: ${String(error)}`
    }
  }
}

/**
 * Check whether the current browser session is authenticated.
 *
 * @returns {Promise<boolean>}
 */
export async function isAuthenticated() {
  try {
    //const response = await apiFetch(API_PATHS.authCheck,
    const response = await authRequest('/auth/check', {
      method: 'GET'
    })

    const data = await response.json().catch(() => null)
    return data?.authenticated === true
  } catch (error) {
    console.error('Auth check failed:', error)
    return false
  }
}

/**
 * Fetch full auth check payload from backend.
 * Useful if you want access to returned user claims later.
 *
 * @returns {Promise<{ authenticated: boolean, user?: any }>}
 */

export async function getCurrentUser() {
  try {
    //const response = await apiFetch(API_PATHS.authMe,
    const response = await authRequest('/auth/me', {
      method: 'GET'
    })

    if (!response.ok) {
      return null
    }

    return await response.json()
  } catch (error) {
    console.error('Failed to fetch current user:', error)
    return null
  }
}
