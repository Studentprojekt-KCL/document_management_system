<script setup>
/**
 * ConnectedSourcesView
 * Displays all supported integrations and whether the user is connected.
 */

import { computed, ref } from 'vue'
import { FolderGit2, GitBranch, HardDrive, Cloud, ShieldCheck, Wifi } from 'lucide-vue-next'

/* HARDCODED SOURCES - In a real application, this would be fetched from backend */
const sources = ref([
  {
    id: 'github',
    name: 'GitHub',
    icon: FolderGit2,
    status: 'connected'
  },
  {
    id: 'gitlab',
    name: 'GitLab',
    icon: GitBranch,
    status: 'connected'
  },
  {
    id: 'smb',
    name: 'Shared Folders (SMB)',
    icon: HardDrive,
    status: 'disconnected'
  },
  {
    id: 'sharepoint',
    name: 'SharePoint',
    icon: Cloud,
    status: 'disconnected'
  }
])

const connectedCount = computed(() => sources.value.filter((source) => source.status === 'connected').length)

const isConnected = (source) => source.status === 'connected'

const connectSource = (sourceId) => {
  sources.value = sources.value.map((source) => {
    if (source.id !== sourceId) return source
    return {
      ...source,
      status: 'connected'
    }
  })
}
</script>

<template>
  <section class="connections-view">
    <div class="hero">
      <h1>Connected Sources</h1>
      <div class="hero-status">
        <Wifi class="hero-status-icon" />
        <span>{{ connectedCount }} / {{ sources.length }} connected</span>
      </div>
    </div>

    <ul class="sources-list">
      <li v-for="source in sources" :key="source.id" class="source-row">
        <div class="source-main">
          <component :is="source.icon" class="source-icon" />
          <h3>{{ source.name }}</h3>
        </div>

        <div class="source-right">
          <span v-if="source.status === 'connected'" class="status-pill" :class="{ connected: source.status === 'connected' }">
            <ShieldCheck class="status-icon" />
            Connected
          </span>

          <div class="source-actions">
            <button v-if="!isConnected(source)" class="btn-primary" @click="connectSource(source.id)">Connect</button>
          </div>
        </div>
      </li>
    </ul>
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
  color: #3730a3;
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
  color: #4f46e5;
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
  background: #4f46e5;
}
</style>
