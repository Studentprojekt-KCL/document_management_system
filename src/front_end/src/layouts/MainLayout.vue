<script setup>
import Header from "@/components/Header.vue"
import Sidebar from "@/components/Sidebar.vue"
import Footer from "@/components/Footer.vue"
</script>

<template>
  <div class="layout">
    <Header />

    <div class="main">
      <Sidebar />

      <div class="content">
        <router-view />
      </div>
    </div>

    <Footer />
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
