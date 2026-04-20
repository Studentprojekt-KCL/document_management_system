<script setup>
/**
 * The App.vue component serves as the main component for the frontend application.
 * Handles global layout and synchronization of logout events across tabs.
 */

import { computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import MainLayout from '@/layouts/MainLayout.vue'
import router from './router'
import { LOCAL_KEY_LOGOUT_EVENT } from '@/utils/config'

/* Determine if the current route is a public or error page. */
const route = useRoute()
const isPublicOrErrorPage = computed(() => ['/', '/401', '/403', '/404'].includes(route.path))

/* Synchronize logout across multiple tabs for storage events. */
const syncLogout = (event) => {
  if (event.key === LOCAL_KEY_LOGOUT_EVENT) {
    sessionStorage.clear()
    router.push('/')
  }
}

/* Event listeners for storage events to handle logout synchronization. */
onMounted(() => {
  window.addEventListener('storage', syncLogout)
})

onUnmounted(() => {
  window.removeEventListener('storage', syncLogout)
})
</script>

<template>
  <!-- Layout based on the current state (error, not authenticated, or public page etc.). -->
  <div v-if="isPublicOrErrorPage">
    <router-view />
  </div>
  <!-- For all other routes, use the main layout. -->
  <MainLayout v-else>
    <router-view />
  </MainLayout>
</template>
