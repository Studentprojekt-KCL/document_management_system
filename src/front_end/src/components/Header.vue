<script setup>
import { Bell, LogOut } from 'lucide-vue-next';

// Keycloak attributes
const KEYCLOAK_BASE = import.meta.env.VITE_KEYCLOAK_BASE
const REALM = import.meta.env.VITE_REALM
const CLIENT_ID = import.meta.env.VITE_CLIENT_ID

const handleLogout = () => {
  const idToken = sessionStorage.getItem('id_token')
  const postLogoutRedirectUri = `${window.location.origin}/`

  sessionStorage.removeItem('access_token')
  sessionStorage.removeItem('id_token')
  sessionStorage.removeItem('pkce_verifier')
  sessionStorage.removeItem('oidc_state')

  if (idToken) {
    const logoutUrl =
      `${KEYCLOAK_BASE}/realms/${REALM}/protocol/openid-connect/logout` +
      `?id_token_hint=${encodeURIComponent(idToken)}` +
      `&post_logout_redirect_uri=${encodeURIComponent(postLogoutRedirectUri)}` +
      `&client_id=${encodeURIComponent(CLIENT_ID)}`

  window.location.assign(logoutUrl)
  return
  }
}
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
