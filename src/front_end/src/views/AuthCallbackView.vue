<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const KEYCLOAK_BASE = window.__ENV__.KEYCLOAK_BASE_URL
const REALM = window.__ENV__.KEYCLOAK_REALM
const CLIENT_ID = window.__ENV__.KEYCLOAK_CLIENT_ID

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

  const expectedState = sessionStorage.getItem('oidc_state')
  const verifier = sessionStorage.getItem('pkce_verifier')

  if (!expectedState || !verifier) {
    errorMsg.value = 'Missing PKCE data.'
    return
  }

  if (expectedState !== returnedState) {
    errorMsg.value = 'State mismatch.'
    return
  }

  if (alreadyProcessed) return
  alreadyProcessed = true

  // token exchange
  const redirectUri = `${window.location.origin}/auth/callback`
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

    const data = await resp.json()

    if (!resp.ok) {
      errorMsg.value = `Token exchange failed: ${data.error}`
      return
    }

    // store tokens
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    localStorage.setItem('id_token', data.id_token)

    // cleanup
    sessionStorage.removeItem('pkce_verifier')
    sessionStorage.removeItem('oidc_state')

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
