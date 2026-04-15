<script setup>
/**
 * LoginView.vue - View for handling user login with placeholder for Microsoft Entra ID.
 * Includes PKCE (Proof Key for Code Exchange) for secure authentication.
 */

import { ref } from 'vue'

const isLoading = ref(false)

// Keycloak configuration from environment variables.
const KEYCLOAK_BASE = window.__ENV__.KEYCLOAK_BASE_URL
const REALM = window.__ENV__.KEYCLOAK_REALM
const CLIENT_ID = window.__ENV__.KEYCLOAK_CLIENT_ID

/* Used for getting the token */
function base64UrlEncode(buffer) {
  return btoa(String.fromCharCode(...new Uint8Array(buffer)))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/g, '')
}

// SHA-256 hashing function for PKCE challenge generation.
async function sha256(input) {
  const data = new TextEncoder().encode(input)
  return await crypto.subtle.digest('SHA-256', data)
}

// Generates a random string of specified byte length, used for PKCE verifier and state.
function randomString(bytesLen = 32) {
  const bytes = new Uint8Array(bytesLen)
  crypto.getRandomValues(bytes)
  return base64UrlEncode(bytes)
}

// Creates a PKCE pair (verifier and challenge) for secure OAuth authentication. 
async function createPkcePair() {
  const verifier = randomString(64)
  const challenge = base64UrlEncode(await sha256(verifier))
  return { verifier, challenge }
}

// Initiates the Entra ID login flow using PKCE. 
const handleEntraIdLogin = async () => {
  const { verifier, challenge } = await createPkcePair()

  sessionStorage.setItem('pkce_verifier', verifier)

  const state = randomString(32)
  sessionStorage.setItem('oidc_state', state)

  const redirectUri = `${window.location.origin}/auth/callback`

  const authUrl =
    `${KEYCLOAK_BASE}/realms/${REALM}/protocol/openid-connect/auth` +
    `?client_id=${encodeURIComponent(CLIENT_ID)}` +
    `&redirect_uri=${encodeURIComponent(redirectUri)}` +
    `&response_type=code` +
    `&scope=openid` +
    `&state=${encodeURIComponent(state)}` +
    `&code_challenge=${encodeURIComponent(challenge)}` +
    `&code_challenge_method=S256`

  window.location.assign(authUrl)
}
</script>

<template>
  <div class="login-container">
    <div class="login-card">
      <div class="login-header">
        <h1>Document Management System</h1>
        <p class="text-secondary">Sign in with your company account</p>
      </div>

      <div class="login-content">
        <button @click="handleEntraIdLogin" :disabled="isLoading" class="entra-btn">
          <svg v-if="!isLoading" class="microsoft-icon" viewBox="0 0 23 23" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect width="11" height="11" fill="#F25022" />
            <rect x="12" width="11" height="11" fill="#7FBA00" />
            <rect y="12" width="11" height="11" fill="#00A4EF" />
            <rect x="12" y="12" width="11" height="11" fill="#FFB900" />
          </svg>
          <span v-if="isLoading">Signing in...</span>
          <span v-else>Sign in with Microsoft Entra ID</span>
        </button>

        <div class="divider">
          <span>Secure authentication</span>
        </div>

        <div class="info-text">
          <p class="text-sm text-secondary">
            Your organization uses Microsoft Entra ID for secure authentication. Click the button above to sign in with your company
            credentials.
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 2rem;
}

.login-card {
  background: white;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  max-width: 480px;
  width: 100%;
  overflow: hidden;
}

.login-header {
  background: linear-gradient(135deg, #5b21b6 0%, #7c3aed 100%);
  color: white;
  padding: 3rem 2rem;
  text-align: center;
}

.login-header h1 {
  font-size: 1.75rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
  color: white;
}

.login-header p {
  color: rgba(255, 255, 255, 0.9);
  font-size: 1rem;
}

.login-content {
  padding: 3rem 2rem;
}

.entra-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  padding: 1rem 1.5rem;
  background: white;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 600;
  color: #1f2937;
  cursor: pointer;
  transition: all 0.2s ease;
}

.entra-btn:hover:not(:disabled) {
  border-color: #7c3aed;
  box-shadow: 0 4px 12px rgba(124, 58, 237, 0.15);
  transform: translateY(-1px);
}

.entra-btn:active:not(:disabled) {
  transform: translateY(0);
}

.entra-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.microsoft-icon {
  width: 21px;
  height: 21px;
  flex-shrink: 0;
}

.divider {
  display: flex;
  align-items: center;
  margin: 2rem 0;
  color: #9ca3af;
  font-size: 0.875rem;
}

.divider::before,
.divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: #e5e7eb;
}

.divider span {
  padding: 0 1rem;
}

.info-text {
  text-align: center;
  line-height: 1.6;
}
</style>
