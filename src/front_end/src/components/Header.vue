<script setup>
import { Bell, LogOut } from 'lucide-vue-next';

const handleNotification = () => {
  console.log('Notification clicked');
  // Add your notification logic here
};

const handleLogout = () => {
  console.log('Logout clicked');
  // Add your logout logic here
};
</script>

<template>
  <header class="header">
    <img src="@/assets/logo.png" alt="NexusUSI Logo" class="logo-image" />
    <div class="spacer"></div>
    <div class="header-actions">
      <button @click="handleNotification" class="notification-btn" title="Notifications">
        <Bell size="20" />
      </button>
      <button @click="handleLogout" class="logout-btn" title="Logout">
        <LogOut size="20" />
      </button>
    </div>
  </header>
</template>

<style scoped>
.header {
  background: #ffffff;
  border-bottom: 1px solid #e5e7eb;
  padding: 1rem 1.5rem;
  display: flex;
  align-items: center;
  height: 100px;
}

.logo-image {
  width: 140px;
  height: auto;
  object-fit: contain;
}

.spacer {
  flex: 1;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.notification-btn,
.logout-btn{
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6b7280;
  transition: color 0.2s ease;
  border-radius: 6px;
}

.notification-btn:hover,
.logout-btn:hover,
.menu-btn:hover {
  color: #1f2937;
  background-color: #f3f4f6;
}
</style>
