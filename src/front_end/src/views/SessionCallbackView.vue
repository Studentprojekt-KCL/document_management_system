<script setup>
/*
Callback for 3rd parties allows us to reroute them to backend with the code for exchange.
*/
import { onMounted, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { API_PATHS, apiFetch } from '@/utils/api'

const router = useRouter()
const route = useRoute()
const errorMSG = ref('')

onMounted(async () => {
  const code = route.query.code
  const state = route.query.state

  if (!code || !state) {
    await router.push('/login')
    return
  }
  try {
    const response = await apiFetch(API_PATHS.sessionCallback, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: new URLSearchParams({
        code,
        state
      })
    })
    if (!response.ok) {
      errorMSG.value = 'Session Callback Failed'
      return
    }
    router.replace('/connections')
  } catch (err) {
    errorMSG.value = `Session callback failed: ${String(err)}`
  }
})
</script>

<template>
  <div>Signing in...</div>
</template>
