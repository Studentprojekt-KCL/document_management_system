<script setup>
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

// Keycloak attributes
const KEYCLOAK_BASE = "https://ad.dms-lookup.com:8443";
const REALM = "master";
const CLIENT_ID = "dms-frontend";

const route = useRoute();
const router = useRouter();
const errorMsg = ref("");

onMounted(async () => {
  // Keycloak might return errors
  if (route.query.error) {
    errorMsg.value = `${route.query.error}: ${route.query.error_description || ""}`;
    return;
  }

  const code = route.query.code;
  const returnedState = route.query.state;

  if (!code) {
    errorMsg.value = "No authorization code found in callback URL.";
    return;
  }

  // Verify state
  const expectedState = sessionStorage.getItem("oidc_state");
  if (expectedState && returnedState !== expectedState) {
    errorMsg.value = "State mismatch. Please try again.";
    return;
  }
  // Verifier that is exchanged for tokens
  const verifier = sessionStorage.getItem("pkce_verifier");
  if (!verifier) {
    errorMsg.value = "Missing PKCE verifier. Please try again.";
    return;
  }
  // redirection url
  const redirectUri = `${window.location.origin}/auth/callback`;
  // Api address to get tokens
  const tokenUrl = `${KEYCLOAK_BASE}/realms/${REALM}/protocol/openid-connect/token`;

  try {
    const body = new URLSearchParams();
    body.set("grant_type", "authorization_code");
    body.set("client_id", CLIENT_ID);
    body.set("code", String(code));
    body.set("redirect_uri", redirectUri);
    body.set("code_verifier", verifier);

    const resp = await fetch(tokenUrl, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: body.toString(),
    });
    // response form token api
    const data = await resp.json();

    // error with response
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
        <button 
          @click="handleEntraIdLogin" 
          :disabled="isLoading"
          class="entra-btn"
        >
          <svg v-if="!isLoading" class="microsoft-icon" viewBox="0 0 23 23" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect width="11" height="11" fill="#F25022"/>
            <rect x="12" width="11" height="11" fill="#7FBA00"/>
            <rect y="12" width="11" height="11" fill="#00A4EF"/>
            <rect x="12" y="12" width="11" height="11" fill="#FFB900"/>
          </svg>
          <span v-if="isLoading">Signing in...</span>
          <span v-else>Sign in with Microsoft Entra ID</span>
        </button>

        <div class="divider">
          <span>Secure authentication</span>
        </div>

        <div class="info-text">
          <p class="text-sm text-secondary">
            Your organization uses Microsoft Entra ID for secure authentication.
            Click the button above to sign in with your company credentials.
          </p>
    
    if (!resp.ok) {
      errorMsg.value = `Token exchange failed: ${data.error || resp.status} ${data.error_description || ""}`;
      return;
    }

    // Store token(s) and data in sessionStorage
    if (data.access_token) sessionStorage.setItem("access_token", data.access_token);
    if (data.id_token) sessionStorage.setItem("id_token", data.id_token);

    // Cleanup old items
    sessionStorage.removeItem("pkce_verifier");
    sessionStorage.removeItem("oidc_state");

    // Go to protected page
    router.replace("/search");
  } catch (e) {
    errorMsg.value = `Unexpected error: ${String(e)}`;
  }
});
</script>

<template>
  <div style="padding: 2rem;">
    <h2>Signing you in…</h2>
    <p v-if="errorMsg" style="white-space: pre-wrap;"><b>Error:</b> {{ errorMsg }}</p>
  </div>
</template>