<script setup>
/**
 * AuthCallbackView.vue - Handles the OAuth callback from Keycloak.
 * This view handles the redirection from Keycloak after the user has authenticated.
 */
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

/* Keycloak attributes */
const KEYCLOAK_BASE = window.__ENV__.KEYCLOAK_BASE_URL
const REALM = window.__ENV__.KEYCLOAK_REALM
const CLIENT_ID = window.__ENV__.KEYCLOAK_CLIENT_ID

const route = useRoute()
const router = useRouter()
const errorMsg = ref('')

/**
 * On mount, handle the OAuth callback from Keycloak
 * Different errors can occur during the authentication process.
 */
onMounted(async () => {
  if (route.query.error) {
    errorMsg.value = `${route.query.error}: ${route.query.error_description || ''}`
    return
  }

  /* Authorization code returned by Keycloak */
  const code = route.query.code
  const returnedState = route.query.state
  if (!code) {
    errorMsg.value = 'No authorization code found in callback URL.'
    return
  }

  /* Check state to prevent CSRF attacks */
  const expectedState = sessionStorage.getItem('oidc_state')
  if (expectedState && returnedState !== expectedState) {
    errorMsg.value = 'State mismatch. Please try again.'
    return
  }

  /* Verifier that is exchanged for tokens */
  const verifier = sessionStorage.getItem('pkce_verifier')
  if (!verifier) {
    errorMsg.value = 'Missing PKCE verifier. Please try again.'
    return
  }
  /* Redirection URL */
  const redirectUri = `${window.location.origin}/auth/callback`
  /* API address to get tokens */
  const tokenUrl = `${KEYCLOAK_BASE}/realms/${REALM}/protocol/openid-connect/token`

  try {
    const body = new URLSearchParams()
    body.set('grant_type', 'authorization_code')
    body.set('client_id', CLIENT_ID)
    body.set('code', String(code))
    body.set('redirect_uri', redirectUri)
    body.set('code_verifier', verifier)

    const resp = await fetch(tokenUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: body.toString()
    })

    /* Response from token API */
    const data = await resp.json()

    if (!resp.ok) {
      errorMsg.value = `Token exchange failed: ${data.error || resp.status} ${data.error_description || ''}`
      return
    }

    /* Store token(s) and data in sessionStorage */
    if (data.access_token) sessionStorage.setItem('access_token', data.access_token)
    if (data.id_token) sessionStorage.setItem('id_token', data.id_token)

    /* Cleanup old items */
    sessionStorage.removeItem('pkce_verifier')
    sessionStorage.removeItem('oidc_state')

    router.replace('/search')
  } catch (e) {
    errorMsg.value = `Unexpected error: ${String(e)}`
  }
})
</script>

<template>
  <section class="auth-callback-view">
    <h2>Signing you in…</h2>
    <p class="error-message" v-if="errorMsg"><b>Error:</b> {{ errorMsg }}</p>
  </section>
</template>

<style scoped>
.auth-callback-view {
  padding: 2rem;
}
.error-message {
  white-space: pre-wrap;
}
</style>
