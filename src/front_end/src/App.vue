<script setup>
import { computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import MainLayout from '@/layouts/MainLayout.vue'
import router from './router'

const route = useRoute()
const isPublicOrErrorPage = computed(() => ['/', '/401', '/403', '/404'].includes(route.path))

const syncLogout = (event) => {
  if (event.key === 'logout-event') {
    console.log('Logout event detected from another tab.  cleaning up...')
    sessionStorage.clear()

    router.push('/')
  }
}

onMounted(() => {
  window.addEventListener('storage', syncLogout)
})

onUnmounted(() => {
  window.removeEventListener('storage', syncLogout)
})
</script>

<template>
  <div v-if="isPublicOrErrorPage">
    <router-view />
  </div>
  <MainLayout v-else>
    <router-view />
  </MainLayout>
</template>
