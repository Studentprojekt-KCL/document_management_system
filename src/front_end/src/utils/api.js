/**
 * API utilities.
 * Base URL, each endpoint path, and authFetch wrapper for authenticated API calls.
 * Used several times across, so centralized here to avoid duplication and ensure consistency.
 */

import { SESSION_KEY_ACCESS_TOKEN } from '@/utils/config'

/* Base URL for all backend API calls, trailing slash stripped. */
export const API_BASE_URL = window.__ENV__.API_BASE_URL.replace(/\/$/, '')

/* API path */
export const API_PATHS = {
  search: `${API_BASE_URL}/search_engine/search`,
  summarize: `${API_BASE_URL}/stochastic-analyzer/summarize`,
  classifications: `${API_BASE_URL}/stochastic-analyzer/classifications`,
  connectedSourceSystems: `${API_BASE_URL}/connector/connected_source_systems`
}

/**
 * Fetch wrapper that automatically attaches the Bearer token from sessionStorage.
 *
 * @param {string} url
 * @param {RequestInit} [options]
 * @returns {Promise<Response>}
 */
export function authFetch(url, options = {}) {
  const token = sessionStorage.getItem(SESSION_KEY_ACCESS_TOKEN)
  return fetch(url, {
    ...options,
    headers: {
      ...(options.headers ?? {}),
      Authorization: `Bearer ${token}`
    }
  })
}
