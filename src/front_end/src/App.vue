<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import MainLayout from "@/layouts/MainLayout.vue"

const route = useRoute()
const isLoginPage = computed(() => route.path === '/')
</script>

<template>
  <div v-if="isLoginPage">
    <router-view />
  </div>
  <div v-else-if="route.path === '/404'">
    <router-view />
  </div>
  <MainLayout v-else>
    <router-view />
  </MainLayout>
</template>
