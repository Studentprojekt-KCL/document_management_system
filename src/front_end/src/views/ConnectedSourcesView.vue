<script setup>
/**
 * ConnectedSourcesView
 * Displays all supported integrations and whether the user is connected.
 * Fetches available sources, active sessions, and auth endpoints.
 * Allows users to connect new sources via session-based or basic auth.
 */

import { computed, ref } from 'vue'
import { ShieldCheck, Wifi } from 'lucide-vue-next'
import { authFetch, API_PATHS } from '@/utils/api'
import ConnectModal from '@/components/ConnectModal.vue'

const sources = ref([])
const sourceAuthEntries = ref([])
const activeSessions = ref({})
const showModal = ref(false)
const selectedSource = ref(null)
const modalLoading = ref(false)
const modalError = ref('')

const normalizeAuthMethod = (method) => {
  if (!method) return 'unknown'
  return String(method).toLowerCase()
}

const normalizeSourceName = (source) => String(source || '').toLowerCase()

const mapNormalizeSources = (sessions) => {
  if (!sessions || typeof sessions !== 'object') return {}

  return Object.fromEntries(
    Object.entries(sessions).map(([serviceName, isActive]) => [normalizeSourceName(serviceName), Boolean(isActive)])
  )
}

const getAuthEndpoint = (source) => {
  const sourceName = normalizeSourceName(source)
  return sourceAuthEntries.value.find((entry) => normalizeSourceName(entry?.name) === sourceName) || null
}

const resolveAuthEndpointUrl = (endpoint) => {
  if (!endpoint) return ''
  if (endpoint.startsWith('http')) return endpoint
  if (endpoint.startsWith('/api/')) return endpoint

  const fixedEndpoint = endpoint.replace('/auth_user&', '/auth_user?')

  if (fixedEndpoint.startsWith('/auth_user?')) {
    return `${API_PATHS.authUser}?${fixedEndpoint.split('?')[1]}`
  }

  return fixedEndpoint
}

const fetchSources = async () => {
  try {
    const res = await authFetch(API_PATHS.connectedSourceSystems)

    if (!res.ok) {
      console.error(`Failed to fetch source systems: ${res.statusText}`)
      return
    }
    const data = await res.json()
    sources.value = data
  } catch (error) {
    console.error(`Error fetching source systems: ${error}`)
  }
}

const fetchAuthUserUrls = async () => {
  try {
    const res = await authFetch(API_PATHS.authUserUrl)

    if (!res.ok) {
      console.error(`Failed to fetch auth user URLs: ${res.statusText}`)
      sourceAuthEntries.value = []
      return
    }
    const data = await res.json()
    sourceAuthEntries.value = Array.isArray(data) ? data : []
    console.log('Auth user URLs:', data)
  } catch (error) {
    console.error(`Error fetching auth user URLs: ${error}`)
    sourceAuthEntries.value = []
  }
}

const fetchActiveSessions = async () => {
  try {
    const res = await authFetch(API_PATHS.activeSessions)

    if (!res.ok) {
      console.error(`Failed to fetch active sessions: ${res.statusText}`)
      activeSessions.value = {}
      return
    }

    const data = await res.json()
    activeSessions.value = mapNormalizeSources(data)
    console.log('Active sessions:', data)
  } catch (error) {
    console.error(`Error fetching active sessions: ${error}`)
    activeSessions.value = {}
  }
}
fetchSources()
fetchAuthUserUrls()
fetchActiveSessions()

const connectedCount = computed(() => sources.value.filter((source) => isConnected(source)).length)
const selectedSourceAuthEntry = computed(() => getAuthEndpoint(selectedSource.value))
const selectedSourceAuthMethod = computed(() => normalizeAuthMethod(selectedSourceAuthEntry.value?.authentication_method))

const isConnected = (source) => Boolean(activeSessions.value[normalizeSourceName(source)])

const connectSource = (source) => {
  document.cookie = `source=${encodeURIComponent(source)}; path=/; max-age=3600; Secure; SameSite=Lax`

  const authEntry = getAuthEndpoint(source)
  const method = normalizeAuthMethod(authEntry?.authentication_method)
  const targetUrl = resolveAuthEndpointUrl(authEntry?.endpoint)

  if (method === 'ba' || method === 'session') {
    selectedSource.value = source
    modalError.value = ''
    showModal.value = true
    return
  }

  if (!targetUrl) {
    selectedSource.value = source
    modalError.value = 'No authentication endpoint found.'
    showModal.value = true
    return
  }

  window.location.assign(targetUrl)
}

const closeConnectModal = () => {
  showModal.value = false
  selectedSource.value = null
  modalError.value = ''
  modalLoading.value = false
}

const handleConnect = async ({ source, endpoint, method, username, password }) => {
  if (!source) return

  const resolvedMethod = normalizeAuthMethod(method)
  const targetUrl = resolveAuthEndpointUrl(endpoint)

  if (!targetUrl) {
    modalError.value = 'Missing authentication endpoint for this source.'
    return
  }

  if (resolvedMethod === 'session') {
    window.location.assign(targetUrl)
    return
  }

  if (resolvedMethod === 'ba') {
    modalLoading.value = true
    modalError.value = ''

    try {
      const credentials = btoa(`${username}:${password}`)

      const response = await authFetch(targetUrl, {
        method: 'GET',
        headers: {
          'X-Connector-Authorization': `Basic ${credentials}`
        }
      })

      if (!response.ok) {
        modalError.value = 'Authentication failed. Check credentials and try again.'
        return
      }

      await fetchActiveSessions()
      closeConnectModal()
    } catch (error) {
      modalError.value = `Connection failed: ${String(error)}`
    } finally {
      modalLoading.value = false
    }
  }
}
</script>

<template>
  <section class="connections-view">
    <div class="hero">
      <h1>Connected Sources</h1>
      <div class="hero-status">
        <Wifi class="hero-status-icon" />
        <span>{{ connectedCount }} / {{ sources.length }} Connected</span>
      </div>
    </div>

    <ul class="sources-list">
      <li v-for="source in sources" :key="source" class="source-row">
        <div class="source-main">
          <h3>{{ source }}</h3>
        </div>

        <div class="source-right">
          <span v-if="isConnected(source)" class="status-pill" :class="{ connected: isConnected(source) }">
            <ShieldCheck class="status-icon" />
            Connected
          </span>

          <div class="source-actions">
            <button v-if="!isConnected(source)" class="btn-primary" @click="connectSource(source)">Connect</button>
          </div>
        </div>
      </li>
    </ul>
    <ConnectModal
      :open="showModal"
      :source-name="selectedSource || ''"
      :loading="modalLoading"
      :error-message="modalError"
      :auth-method="selectedSourceAuthMethod"
      :auth-endpoint="selectedSourceAuthEntry?.endpoint || ''"
      @close="closeConnectModal"
      @connect="handleConnect"
    />
  </section>
</template>

<style scoped>
.connections-view {
  padding: 2rem;
}

.hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 2rem;
}

.hero-status {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  background: #eef2ff;
  border: 1px solid #c7d2fe;
  padding: 0.5rem 0.75rem;
  border-radius: 999px;
  font-weight: 600;
}

.hero-status-icon {
  width: 16px;
  height: 16px;
}

.sources-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.source-row {
  border-radius: 14px;
  background: #ffffff;
  padding: 1rem 1.1rem;
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.05);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.source-main {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex: 1;
}

.source-details {
  min-width: 0;
}

.source-icon {
  width: 20px;
  height: 20px;
  background: #7c3aed;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  border-radius: 999px;
  padding: 0.3rem 0.6rem;
  font-size: 0.75rem;
  font-weight: 600;
  border: 1px solid transparent;
}

.status-icon {
  width: 14px;
  height: 14px;
}

.status-pill.connected {
  background: #dcfce7;
  color: #166534;
  border-color: #bbf7d0;
}

.source-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  justify-content: flex-end;
}

.source-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.btn-primary {
  border-radius: 10px;
  padding: 0.45rem 0.75rem;
  font-size: 0.85rem;
  font-weight: 600;
  border: 0;
  cursor: pointer;
  color: #ffffff;
  background: #7c3aed;
}
</style>
