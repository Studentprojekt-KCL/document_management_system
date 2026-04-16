<script setup>
/**
 * SettingsView.vue - User preferences and account settings.
 * Reads user profile from the JWT access token, displays session info,
 * and offers local UI preferences (theme, density, results-per-page).
 *
 * Preferences are persisted to localStorage — no backend needed yet.
 */

import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { User, Palette, Monitor, Clock, LogOut, Shield, Mail, Key } from 'lucide-vue-next'

const router = useRouter()

/* ── Decode JWT to get user profile ── */
const decodeJwtPayload = (token) => {
  try {
    const base64Url = token.split('.')[1]
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), '=')
    return JSON.parse(atob(padded))
  } catch {
    return null
  }
}

const token = sessionStorage.getItem('access_token')
const payload = token ? decodeJwtPayload(token) : null

const CLIENT_ID = window.__ENV__?.KEYCLOAK_CLIENT_ID ?? ''

/* User profile derived from JWT */
const userProfile = computed(() => {
  if (!payload) return { name: 'Unknown', email: '', username: '', roles: [] }
  const clientRoles = payload?.resource_access?.[CLIENT_ID]?.roles ?? []
  const realmRoles = (payload?.realm_access?.roles ?? []).filter(
    (r) => !['default-roles-master', 'offline_access', 'uma_authorization'].includes(r)
  )
  return {
    name: payload.name || payload.preferred_username || 'Unknown',
    email: payload.email || '',
    username: payload.preferred_username || '',
    roles: [...new Set([...clientRoles, ...realmRoles])]
  }
})

/* ── Session countdown ── */
const tokenExpiresAt = computed(() => (payload?.exp ? payload.exp * 1000 : 0))
const now = ref(Date.now())
let tickTimer = null

const sessionRemaining = computed(() => {
  const diff = tokenExpiresAt.value - now.value
  if (diff <= 0) return 'Expired'
  const minutes = Math.floor(diff / 60000)
  const seconds = Math.floor((diff % 60000) / 1000)
  if (minutes >= 60) {
    const hours = Math.floor(minutes / 60)
    return `${hours}h ${minutes % 60}m`
  }
  return `${minutes}m ${seconds}s`
})

const sessionHealth = computed(() => {
  const diff = tokenExpiresAt.value - now.value
  if (diff <= 0) return 'expired'
  if (diff < 5 * 60 * 1000) return 'warning'
  return 'ok'
})

/* ── Preferences persisted to localStorage ── */
const PREFS_KEY = 'dmis-user-prefs'
const defaultPrefs = {
  theme: 'light',
  density: 'comfortable',
  resultsPerPage: 10,
  openInNewTab: true,
  showAISummaryByDefault: false
}

const prefs = ref({ ...defaultPrefs, ...JSON.parse(localStorage.getItem(PREFS_KEY) || '{}') })

const savePrefs = () => {
  localStorage.setItem(PREFS_KEY, JSON.stringify(prefs.value))
}

const resetPrefs = () => {
  prefs.value = { ...defaultPrefs }
  savePrefs()
}

/* ── Sign out ── */
const handleSignOut = () => {
  localStorage.setItem('logout-event', Date.now().toString())
  sessionStorage.clear()
  router.push('/')
}

onMounted(() => {
  tickTimer = setInterval(() => {
    now.value = Date.now()
  }, 1000)
})

onUnmounted(() => {
  if (tickTimer) clearInterval(tickTimer)
})
</script>

<template>
  <section class="settings-view">
    <header class="view-header">
      <h1>System Settings</h1>
      <p class="subtitle">Manage your profile, preferences, and session.</p>
    </header>

    <div class="settings-grid">
      <!-- ── Profile Card ── -->
      <article class="settings-card">
        <div class="card-header">
          <div class="card-icon"><User :size="18" /></div>
          <h2>Profile</h2>
        </div>

        <div class="profile-block">
          <div class="avatar">{{ userProfile.name.charAt(0).toUpperCase() }}</div>
          <div class="profile-info">
            <p class="profile-name">{{ userProfile.name }}</p>
            <p class="profile-username">@{{ userProfile.username }}</p>
          </div>
        </div>

        <dl class="profile-details">
          <div class="detail-row">
            <dt><Mail :size="13" /> Email</dt>
            <dd>{{ userProfile.email || '—' }}</dd>
          </div>
          <div class="detail-row">
            <dt><Shield :size="13" /> Roles</dt>
            <dd>
              <span v-if="userProfile.roles.length === 0" class="muted">None</span>
              <span v-for="role in userProfile.roles" :key="role" class="role-chip">{{ role }}</span>
            </dd>
          </div>
        </dl>
      </article>

      <!-- ── Session Card ── -->
      <article class="settings-card">
        <div class="card-header">
          <div class="card-icon"><Clock :size="18" /></div>
          <h2>Session</h2>
        </div>

        <div class="session-block">
          <div class="session-stat">
            <span class="stat-label">Time remaining</span>
            <span :class="['stat-value', `health-${sessionHealth}`]">{{ sessionRemaining }}</span>
          </div>
          <p class="session-note">
            Your session will automatically refresh before it expires. If refresh fails, you will be signed out.
          </p>
        </div>

        <button class="action-btn danger" type="button" @click="handleSignOut">
          <LogOut :size="14" />
          Sign out of this device
        </button>
      </article>

      <!-- ── Appearance Card ── -->
      <article class="settings-card">
        <div class="card-header">
          <div class="card-icon"><Palette :size="18" /></div>
          <h2>Appearance</h2>
        </div>

        <div class="pref-group">
          <label class="pref-label">Theme</label>
          <div class="segment-control">
            <button
              v-for="opt in ['light', 'dark', 'system']"
              :key="opt"
              :class="['segment', { active: prefs.theme === opt }]"
              @click="
                () => {
                  prefs.theme = opt
                  savePrefs()
                }
              "
            >
              {{ opt }}
            </button>
          </div>
          <p class="pref-hint">Dark mode rendering is coming soon.</p>
        </div>

        <div class="pref-group">
          <label class="pref-label">Density</label>
          <div class="segment-control">
            <button
              v-for="opt in ['compact', 'comfortable', 'spacious']"
              :key="opt"
              :class="['segment', { active: prefs.density === opt }]"
              @click="
                () => {
                  prefs.density = opt
                  savePrefs()
                }
              "
            >
              {{ opt }}
            </button>
          </div>
        </div>
      </article>

      <!-- ── Search Preferences Card ── -->
      <article class="settings-card">
        <div class="card-header">
          <div class="card-icon"><Monitor :size="18" /></div>
          <h2>Search Preferences</h2>
        </div>

        <div class="pref-group">
          <label class="pref-label" for="rpp">Results per page</label>
          <select id="rpp" v-model.number="prefs.resultsPerPage" class="pref-select" @change="savePrefs">
            <option :value="10">10</option>
            <option :value="25">25</option>
            <option :value="50">50</option>
            <option :value="100">100</option>
          </select>
        </div>

        <div class="pref-group">
          <label class="toggle-row">
            <span>Open files in new tab</span>
            <input v-model="prefs.openInNewTab" type="checkbox" @change="savePrefs" />
          </label>
          <label class="toggle-row">
            <span>Auto-generate AI summary on preview</span>
            <input v-model="prefs.showAISummaryByDefault" type="checkbox" @change="savePrefs" />
          </label>
        </div>

        <button class="action-btn secondary" type="button" @click="resetPrefs">
          <Key :size="14" />
          Reset to defaults
        </button>
      </article>
    </div>
  </section>
</template>

<style scoped>
.settings-view {
  padding: 0.5rem;
}

.view-header {
  margin-bottom: 1.5rem;
}

.view-header h1 {
  margin: 0;
  font-size: 1.8rem;
}

.subtitle {
  margin: 0.25rem 0 0;
  color: #6b7280;
  font-size: 0.95rem;
}

.settings-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
  gap: 1rem;
}

.settings-card {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  padding: 1.25rem;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin-bottom: 1rem;
}

.card-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: linear-gradient(135deg, #5b21b6 0%, #7c3aed 100%);
  color: #ffffff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.card-header h2 {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 700;
  color: #1f2937;
}

/* ── Profile ── */
.profile-block {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  padding-bottom: 0.9rem;
  border-bottom: 1px solid #f1f5f9;
  margin-bottom: 0.9rem;
}

.avatar {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: linear-gradient(135deg, #5b21b6 0%, #7c3aed 100%);
  color: #ffffff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 1.4rem;
  font-weight: 700;
}

.profile-info {
  min-width: 0;
}

.profile-name {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 700;
  color: #1f2937;
}

.profile-username {
  margin: 0.1rem 0 0;
  font-size: 0.85rem;
  color: #6b7280;
}

.profile-details {
  margin: 0;
  display: grid;
  gap: 0.65rem;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.detail-row dt {
  font-size: 0.8rem;
  font-weight: 600;
  color: #6b7280;
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
}

.detail-row dd {
  margin: 0;
  font-size: 0.9rem;
  font-weight: 600;
  color: #1f2937;
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
  justify-content: flex-end;
}

.role-chip {
  background: #faf5ff;
  color: #6d28d9;
  border: 1px solid #e9d5ff;
  padding: 0.15rem 0.55rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: lowercase;
}

.muted {
  color: #94a3b8;
  font-weight: 500;
}

/* ── Session ── */
.session-block {
  padding: 0.85rem;
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  margin-bottom: 0.9rem;
}

.session-stat {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 0.5rem;
}

.stat-label {
  font-size: 0.8rem;
  color: #6b7280;
  font-weight: 600;
}

.stat-value {
  font-size: 1.15rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.stat-value.health-ok {
  color: #059669;
}
.stat-value.health-warning {
  color: #d97706;
}
.stat-value.health-expired {
  color: #dc2626;
}

.session-note {
  margin: 0;
  font-size: 0.8rem;
  color: #6b7280;
  line-height: 1.5;
}

/* ── Preferences ── */
.pref-group {
  margin-bottom: 1rem;
}

.pref-group:last-child {
  margin-bottom: 0;
}

.pref-label {
  display: block;
  font-size: 0.82rem;
  font-weight: 700;
  color: #475569;
  margin-bottom: 0.45rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.pref-hint {
  margin: 0.4rem 0 0;
  font-size: 0.75rem;
  color: #94a3b8;
}

.segment-control {
  display: inline-flex;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 9px;
  padding: 2px;
  gap: 2px;
}

.segment {
  border: none;
  background: transparent;
  padding: 0.4rem 0.85rem;
  border-radius: 7px;
  font-size: 0.82rem;
  font-weight: 600;
  color: #475569;
  cursor: pointer;
  text-transform: capitalize;
}

.segment.active {
  background: #ffffff;
  color: #7c3aed;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
}

.pref-select {
  padding: 0.5rem 0.7rem;
  border: 1px solid #d8dee7;
  border-radius: 8px;
  font-size: 0.9rem;
  font-weight: 500;
  color: #1f2937;
  background: #ffffff;
  cursor: pointer;
  font-family: inherit;
}

.pref-select:focus {
  outline: none;
  border-color: #7c3aed;
  box-shadow: 0 0 0 2px rgba(124, 58, 237, 0.12);
}

.toggle-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.6rem 0;
  border-bottom: 1px solid #f1f5f9;
  font-size: 0.88rem;
  color: #1f2937;
  cursor: pointer;
}

.toggle-row:last-child {
  border-bottom: none;
}

.toggle-row input[type='checkbox'] {
  width: 18px;
  height: 18px;
  cursor: pointer;
  accent-color: #7c3aed;
}

/* ── Action buttons ── */
.action-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  padding: 0.6rem 1rem;
  border-radius: 9px;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid transparent;
  margin-top: 0.5rem;
}

.action-btn.secondary {
  background: #f8fafc;
  border-color: #d8dee7;
  color: #475569;
}

.action-btn.secondary:hover {
  border-color: #7c3aed;
  color: #7c3aed;
  background: #faf5ff;
}

.action-btn.danger {
  background: #fef2f2;
  border-color: #fecaca;
  color: #b91c1c;
  width: 100%;
}

.action-btn.danger:hover {
  background: #fee2e2;
}

@media (max-width: 640px) {
  .settings-grid {
    grid-template-columns: 1fr;
  }
}
</style>
