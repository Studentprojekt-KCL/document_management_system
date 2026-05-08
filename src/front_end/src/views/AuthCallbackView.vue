<script setup>
/**
 * AuthCallbackView.vue - Handles the OAuth callback from Keycloak.
 * This view handles the redirection from Keycloak after the user has authenticated.
 */
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { exchangeAuthorizationCode, isAuthenticated } from '@/utils/authClient'
import { SESSION_KEY_PKCE_VERIFIER, SESSION_KEY_OIDC_STATE } from '@/utils/config'

const route = useRoute()
const router = useRouter()
const errorMsg = ref('')

onMounted(async () => {
  const code = route.query.code
  const returnedState = route.query.state

  if (route.query.error) {
    errorMsg.value = `${route.query.error}: ${route.query.error_description || ''}`
    return
  }

  if (!code) {
    errorMsg.value = 'No authorization code'
    return
  }

  const expectedState = localStorage.getItem(SESSION_KEY_OIDC_STATE)
  if (!expectedState || returnedState !== expectedState) {
    errorMsg.value = 'State mismatch. Please try again.'
    return
  }

  const verifier = localStorage.getItem(SESSION_KEY_PKCE_VERIFIER)
  if (!verifier) {
    errorMsg.value = 'Missing PKCE verifier. Please try again.'
    return
  }

  const result = await exchangeAuthorizationCode({
    code,
    codeVerifier: verifier
  })

  if (!result.ok) {
    errorMsg.value = `Login failed: ${result.message}`
    return
  }

  const authed = await isAuthenticated()
  if (!authed) {
    errorMsg.value = 'Login succeeded, but session cookie was not available afterward.'
    return
  }

  router.replace('/search')
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
