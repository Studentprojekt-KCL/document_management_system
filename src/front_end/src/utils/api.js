/**
 * API utilities.
 * Base URL, each endpoint path, and authFetch wrapper for authenticated API calls.
 * Used several times across, so centralized here to avoid duplication and ensure consistency.
 */

/* Base URL for all backend API calls, trailing slash stripped. */
export const FRONTEND_DMISAPI_BASE_URL = window.__ENV__.FRONTEND_DMISAPI_BASE_URL.replace(/\/$/, '')

/* API path */
export const API_PATHS = {
  search: `${FRONTEND_DMISAPI_BASE_URL}/search_engine/search`,
  summarize: `${FRONTEND_DMISAPI_BASE_URL}/stochastic-analyzer/summarize`,
  rerank: `${FRONTEND_DMISAPI_BASE_URL}/search_engine/find_matching`,
  classifications: `${FRONTEND_DMISAPI_BASE_URL}/search_engine/classifications`,
  classification: `${FRONTEND_DMISAPI_BASE_URL}/search_engine/classification`,
  connectedSourceSystems: `${FRONTEND_DMISAPI_BASE_URL}/connector/connected_source_systems`,
  documentsOnly: `${FRONTEND_DMISAPI_BASE_URL}/search_engine/file_types_documents_only`,
  allFileTypes: `${FRONTEND_DMISAPI_BASE_URL}/search_engine/file_types`,
  merge: `${FRONTEND_DMISAPI_BASE_URL}/stochastic-analyzer/merge`,
  mdToPDF: `${FRONTEND_DMISAPI_BASE_URL}/stochastic-analyzer/md-to-pdf`,

  /* Connected source system auth endpoints */
  authUserUrl: `${FRONTEND_DMISAPI_BASE_URL}/connector/get_auth_user_urls`,
  authUser: `${FRONTEND_DMISAPI_BASE_URL}/connector/auth_user`,

  /* General auth endpoints */
  authCheck: `${FRONTEND_DMISAPI_BASE_URL}/auth/check`,
  authMe: `${FRONTEND_DMISAPI_BASE_URL}/auth/me`,
  authRefresh: `${FRONTEND_DMISAPI_BASE_URL}/auth/refresh`,
  authLogout: `${FRONTEND_DMISAPI_BASE_URL}/auth/logout`,
  codeExchange: `${FRONTEND_DMISAPI_BASE_URL}/auth/codeExchange`,
  checkAdmin: `${FRONTEND_DMISAPI_BASE_URL}/auth/checkAdmin`,

  /* code exchange for 3rd parties */
  sessionCallback: `${FRONTEND_DMISAPI_BASE_URL}/connector/session/callback`
}

/**
 * Shared fetch wrapper for backend API calls.
 * Uses cookie-based auth via credentials: 'include'.
 *
 * @param {string} url
 * @param {RequestInit} [options]
 * @returns {Promise<Response>}
 */
export function apiFetch(url, options = {}) {
  return fetch(url, {
    credentials: 'include',
    ...options,
    headers: {
      ...(options.headers ?? {})
    }
  })
}
/*
export async function apiFetch(url, options = {}) {
  const requestOptions = {
    credentials: 'include',
    ...options,
    headers: {
      ...(options.headers ?? {})
    }
  }

  let response = await fetch(url, requestOptions)

  if (response.status !== 401 || url === API_PATHS.authRefresh || url === API_PATHS.authLogout) {
    return response
  }

  const refreshResponse = await fetch(API_PATHS.authRefresh, {
    method: 'POST',
    credentials: 'include'
  })

  if (!refreshResponse.ok) {
    window.location.href = '/login'
    return response
  }

  response = await fetch(url, requestOptions)
  return response
}
*/

/* causes all previos authFetch calls into apiFetch */
export const authFetch = apiFetch
