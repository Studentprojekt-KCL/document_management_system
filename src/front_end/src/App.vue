<script setup>
/**
 * The App.vue component serves as the main component for the frontend application.
 * Handles global layout and synchronization of logout events across tabs.
 */

import { computed } from 'vue'
import { useRoute } from 'vue-router'
import MainLayout from '@/layouts/MainLayout.vue'
// new import
import { useAuthSession } from '@/composables/useAuthSession'

/* Determine if the current route is a public or error page. */
const route = useRoute()
const isPublicOrErrorPage = computed(() => ['/', '/401', '/403', '/404'].includes(route.path))

useAuthSession()
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
