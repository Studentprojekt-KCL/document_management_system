<script setup>
/**
 * AuthCallbackView.vue - Handles the OAuth callback from Keycloak.
 * This view handles the redirection from Keycloak after the user has authenticated.
 */
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { exchangeCodeForToken } from '../utils/auth'

/* State variables */
const route = useRoute()
const router = useRouter()
const errorMsg = ref('')

/**
 * On mount, handle the OAuth callback from Keycloak
 * Different errors can occur during the authentication process.
 */
onMounted(async () => {
  try {
    if (route.query.error) {
      errorMsg.value = `${route.query.error}: ${route.query.error_description || ''}`
      return
    }

    const code = route.query.code
    const returnedState = route.query.state

    if (!code) {
      errorMsg.value = 'No authorization code found.'
      return
    }

    const expectedState = sessionStorage.getItem('oidc_state')
    if (expectedState && returnedState !== expectedState) {
      errorMsg.value = 'State mismatch.'
      return
    }

    const verifier = sessionStorage.getItem('pkce_verifier')
    if (!verifier) {
      errorMsg.value = 'Missing PKCE verifier.'
      return
    }

    const redirectUri = `${window.location.origin}/auth/callback`

    await exchangeCodeForToken(code, verifier, redirectUri)

    sessionStorage.removeItem('pkce_verifier')
    sessionStorage.removeItem('oidc_state')

    router.replace('/search')
  } catch (e) {
    errorMsg.value = `Token exchange failed: ${e.message}`
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
