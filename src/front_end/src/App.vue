<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import MainLayout from '@/layouts/MainLayout.vue'

const route = useRoute()
const isPublicOrErrorPage = computed(() => ['/', '/401', '/403', '/404'].includes(route.path))
</script>

<template>
  <div v-if="isPublicOrErrorPage">
    <router-view />
  </div>
  <MainLayout v-else>
    <router-view />
  </MainLayout>
</template>