// Global test setup — runs before every test file
window.__ENV__ = {
  /* API */
  FRONTEND_DMISAPI_BASE_URL: '/api/',
  /* Keycloak (new naming) */
  FRONTEND_AD_URL: 'https://keycloak.test',
  FRONTEND_AD_REALM: 'master',
  FRONTEND_AD_CLIENT_ID: 'dms-frontend'
}
