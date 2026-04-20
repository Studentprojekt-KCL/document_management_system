/**
 * Includes all Keycloak-related configuration and session/local storage key names
 * Used several times across, so centralized here to avoid duplication and ensure consistency.
 */

/* Keycloak / OIDC config from runtime environment */
export const KEYCLOAK_BASE = window.__ENV__.KEYCLOAK_BASE_URL
export const KEYCLOAK_REALM = window.__ENV__.KEYCLOAK_REALM
export const KEYCLOAK_CLIENT_ID = window.__ENV__.KEYCLOAK_CLIENT_ID

/* Keycloak OIDC endpoint builders */
export const keycloakAuthUrl = () => `${KEYCLOAK_BASE}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/auth`
export const keycloakTokenUrl = () => `${KEYCLOAK_BASE}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/token`
export const keycloakLogoutUrl = () => `${KEYCLOAK_BASE}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/logout`

/* SessionStorage key names */
export const SESSION_KEY_ACCESS_TOKEN = 'access_token'
export const SESSION_KEY_ID_TOKEN = 'id_token'
export const SESSION_KEY_PKCE_VERIFIER = 'pkce_verifier'
export const SESSION_KEY_OIDC_STATE = 'oidc_state'
export const SESSION_KEY_REFRESH_TOKEN = 'refresh_token'

/* LocalStorage key names */
export const LOCAL_KEY_LOGOUT_EVENT = 'logout-event'
