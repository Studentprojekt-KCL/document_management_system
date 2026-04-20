<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  KEYCLOAK_CLIENT_ID,
  keycloakTokenUrl,
  SESSION_KEY_ACCESS_TOKEN,
  SESSION_KEY_ID_TOKEN,
  SESSION_KEY_PKCE_VERIFIER,
  SESSION_KEY_OIDC_STATE
} from '@/utils/config'

const route = useRoute()
const router = useRouter()
const errorMsg = ref('')

onMounted(async () => {
  let alreadyProcessed = false

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

  /* Check state to prevent CSRF attacks */
  const expectedState = localStorage.getItem(SESSION_KEY_OIDC_STATE)
  if (expectedState && returnedState !== expectedState) {
    errorMsg.value = 'State mismatch. Please try again.'
    return
  }

  /* Verifier that is exchanged for tokens */
  const verifier = localStorage.getItem(SESSION_KEY_PKCE_VERIFIER)
  if (!verifier) {
    errorMsg.value = 'Missing PKCE verifier. Please try again.'
    return
  }

  if (alreadyProcessed) return
  alreadyProcessed = true

  // token exchange
  const redirectUri = `${window.location.origin}/auth/callback`

  try {
    const body = new URLSearchParams()
    body.set('grant_type', 'authorization_code')
    body.set('client_id', KEYCLOAK_CLIENT_ID)
    body.set('code', String(code))
    body.set('redirect_uri', redirectUri)
    body.set('code_verifier', verifier)

    const resp = await fetch(keycloakTokenUrl(), {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: body.toString()
    })

    const data = await resp.json()

    if (!resp.ok) {
      errorMsg.value = `Token exchange failed: ${data.error}`
      return
    }

    /* Store token(s) and data in sessionStorage */
    if (data.access_token) localStorage.setItem(SESSION_KEY_ACCESS_TOKEN, data.access_token)
    if (data.id_token) localStorage.setItem(SESSION_KEY_ID_TOKEN, data.id_token)

    /* Cleanup old items */
    localStorage.removeItem(SESSION_KEY_PKCE_VERIFIER)
    localStorage.removeItem(SESSION_KEY_OIDC_STATE)

    router.replace('/search')
  } catch (e) {
    errorMsg.value = `Unexpected error: ${String(e)}`
  }
})
</script>

<template>
  <section>
    <h2>Signing you in…</h2>
    <p v-if="errorMsg">{{ errorMsg }}</p>
  </section>
</template>
