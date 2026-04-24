<script setup>
/**
 * TheHeader Component
 * Application header displaying logo, logout (and notification) buttons.
 * Handles user authentication through Keycloak.
 *
 * @component
 * @example usage:
 * <TheHeader />
 */
import { Bell, LogOut } from 'lucide-vue-next'
import { logout } from '@/utils/auth'
import { useRoute, useRouter } from 'vue-router'
import { useAppState } from '@/composables/useAppState'

/* Logo redirects to search page, page reloads if already on search page */
const router = useRouter()
const route = useRoute()
const { clearBackendAndLocalState } = useAppState()

const navigateToSearch = async () => {
  await clearBackendAndLocalState()
  if (route.name === 'Search') {
    window.location.reload()
    return
  }
  router.push('/search')
}

/* Handles user logout by clearing local storage and redirecting to login page. */
const handleLogout = () => {
  logout()
}
</script>

<template>
  <!--- Main Header container-->
  <header class="header">
    <img src="@/assets/newLogo.png" alt="Logo" class="logo-image" @click="navigateToSearch" />

    <!--- Spacer to push actions to the right -->
    <div class="spacer"></div>

    <!--- Header actions (notifications, logout) -->
    <div class="header-actions">
      <button class="notification-btn" title="Notifications" @click="handleNotification">
        <Bell size="20" />
      </button>
      <button class="logout-btn" title="Logout" @click="handleLogout">
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
  width: 190px;
  height: auto;
  object-fit: contain;
  border-radius: 10px;
  margin-left: 1.3rem;
  cursor: pointer;
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
.logout-btn {
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
