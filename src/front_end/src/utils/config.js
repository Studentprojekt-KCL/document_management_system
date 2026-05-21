/**
 * Includes all Keycloak-related configuration and session/local storage key names
 * Used several times across, so centralized here to avoid duplication and ensure consistency.
 */

/* Keycloak / OIDC config from runtime environment */
export const FRONTEND_AD_URL = window.__ENV__.FRONTEND_AD_URL.replace(/\/$/, '')
export const FRONTEND_AD_CLIENT_ID = window.__ENV__.FRONTEND_AD_CLIENT_ID
export const FRONTEND_AD_AUDIENCE = window.__ENV__.FRONTEND_AD_AUDIENCE || ''

export const SESSION_KEY_PKCE_VERIFIER = 'pkce_verifier'
export const SESSION_KEY_OIDC_STATE = 'oidc_state'
export const LOCAL_KEY_LOGOUT_EVENT = 'logout-event'
