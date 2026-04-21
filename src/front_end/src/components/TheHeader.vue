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
import {
  FRONTEND_AD_CLIENT_ID,
  keycloakLogoutUrl,
  SESSION_KEY_ACCESS_TOKEN,
  SESSION_KEY_ID_TOKEN,
  SESSION_KEY_PKCE_VERIFIER,
  SESSION_KEY_OIDC_STATE,
  LOCAL_KEY_LOGOUT_EVENT
} from '@/utils/config'

/* Handles user logout by clearing local storage and redirecting to login page. */
const handleLogout = () => {
  logout()
  const idToken = sessionStorage.getItem(SESSION_KEY_ID_TOKEN)
  const postLogoutRedirectUri = `${window.location.origin}/`

  sessionStorage.removeItem(SESSION_KEY_ACCESS_TOKEN)
  sessionStorage.removeItem(SESSION_KEY_ID_TOKEN)
  sessionStorage.removeItem(SESSION_KEY_PKCE_VERIFIER)
  sessionStorage.removeItem(SESSION_KEY_OIDC_STATE)

  localStorage.setItem(LOCAL_KEY_LOGOUT_EVENT, Date.now().toString())

  if (idToken) {
    const logoutUrl =
      keycloakLogoutUrl() +
      `?id_token_hint=${encodeURIComponent(idToken)}` +
      `&post_logout_redirect_uri=${encodeURIComponent(postLogoutRedirectUri)}` +
      `&client_id=${encodeURIComponent(FRONTEND_AD_CLIENT_ID)}`

    window.location.assign(logoutUrl)
    return
  }
}
</script>

<template>
  <!--- Main Header container-->
  <header class="header">
    <img src="@/assets/newLogo.png" alt="Logo" class="logo-image" />

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
