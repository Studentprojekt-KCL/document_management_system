<script setup>
import AppHeader from '@/components/AppHeader.vue'
import AppSidebar from '@/components/AppSidebar.vue'
import AppFooter from '@/components/AppFooter.vue'
</script>

<template>
  <div class="layout">
    <AppHeader />

    <div class="main">
      <AppSidebar />

      <div class="content">
        <router-view />
      </div>
    </div>

    <AppFooter />
  </div>
</template>

<style scoped>
.layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.main {
  display: flex;
  flex: 1;
}

.content {
  flex: 1;
  padding: 2rem;
  background: #f5f6fa;
  overflow-y: auto;
}
</style>
