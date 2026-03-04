<script setup>
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

// Keycloak attributes

const KEYCLOAK_BASE = import.meta.env.VITE_KEYCLOAK_BASE;
const REALM = import.meta.env.VITE_REALM;
const CLIENT_ID = import.meta.env.VITE_CLIENT_ID;

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