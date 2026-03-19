<script setup>
/**
MainLayout Component
Defines the overall layout of the application.
Includes the header, sidebar, main content area, and footer. 
@example usage:
<MainLayout />
*/

import TheHeader from '@/components/TheHeader.vue'
import TheSidebar from '@/components/TheSidebar.vue'
import TheFooter from '@/components/TheFooter.vue'
</script>

<template>
  <div class="layout">
    <TheHeader />

    <div class="main">
      <TheSidebar />

      <div class="content">
        <router-view />
      </div>
    </div>

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
  overflow-y: auto;
}
</style>
