/* This file is used to set up the testing environment for Vitest.
It can be used to define global variables, mock APIs, or perform any necessary configuration before tests are run. */

window.__ENV__ = {
  API_BASE_URL: '/api/',
  KEYCLOAK_BASE_URL: 'https://keycloak.test',
  KEYCLOAK_REALM: 'master',
  KEYCLOAK_CLIENT_ID: 'dms-frontend'
}
