<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import DefaultLayout from "@/layouts/DefaultLayout.vue"

const route = useRoute()
const isLoginPage = computed(() => route.path === '/')
</script>

<template>
  <div v-if="isLoginPage">
    <router-view />
  </div>
  <DefaultLayout v-else>
    <router-view />
  </DefaultLayout>
</template>
