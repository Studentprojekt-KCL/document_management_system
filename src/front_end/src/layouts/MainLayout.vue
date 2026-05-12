<script setup>
/**
 * MainLayout Component
 * Defines the overall layout of the application.
 *
 * Layout structure:
 * Header (top)
 * ├── Sidebar (left)
 * └── Content (router-view)
 * Footer (bottom)
 *
 * @component
 * @example usage:
 * <MainLayout />
 */

import TheHeader from '@/components/TheHeader.vue'
import TheSidebar from '@/components/TheSidebar.vue'
import TheFooter from '@/components/TheFooter.vue'
</script>

<template>
  <div class="layout">
    <!-- Global header -->
    <TheHeader />

    <div class="main">
      <!-- Navigation sidebar -->
      <TheSidebar />

      <!-- Dynamic page content -->
      <main class="content">
        <router-view />
      </main>
    </div>

    <!-- Global footer -->
    <TheFooter />
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
}
</style>
