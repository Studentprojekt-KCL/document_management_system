<script setup>
/**
 * SearchMatches Component
 * Displays a list of search results (matches) based on the query.
 * Each match shows the file title, type, and date, and allows the user to select it for preview.
 *
 * @component
 * @example usage in SearchView.vue:
 * <SearchMatches :matches="matches" :loading="isSearching" :selected="selectedFile" :query="lastQuery" @select="selectMatch" />
 */

import { computed } from 'vue'
import { Calendar, FileText, ExternalLink } from 'lucide-vue-next'
import { useSearchMetadata } from '@/composables/useSearchMetadata'

/* Props received from parent component (SearchView) */
const props = defineProps({
  matches: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  selected: { type: String, default: '' },
  query: { type: String, default: '' }
})

/* Emit to parent (SearchView) component when a match is selected */
const emit = defineEmits(['select'])

/* Custom composable to normalize matches, resolve match dates, and resolve sources for display */
const { normalizeMatches, resolveDateOnly, resolveSource, resolveDocumentType, resolveSecurityClass } = useSearchMetadata(props)

/* Computed property to normalize matches for consistent display */
const normalizedMatches = computed(() => normalizeMatches(props.matches))

/* Computed property to generate a user-friendly label for the number of search results */
const resultsLabel = computed(() => {
  const count = normalizedMatches.value.length
  if (count === 0) {
    return `No results found for "${props.query}"`
  }
  return `Found ${count} result${count === 1 ? '' : 's'} for "${props.query}"`
})
</script>

<template>
  <!-- Container for search results with conditional states for loading and no results -->
  <div class="results-shell">
    <p v-if="loading" class="state-text">Searching…</p>
    <p v-else-if="query" class="results-count">{{ resultsLabel }}</p>

    <!-- List of search result matches with titles, types, dates and source -->
    <ul class="results-list">
      <li v-for="item in normalizedMatches" :key="item.filename" class="result-item">
        <button class="result-card" :class="{ active: selected === item.filename }" @click="emit('select', item.rawMatch)">
          <div class="result-main">
            <div class="result-content">
              <h3 class="result-title">{{ item.title }}</h3>

              <div class="meta-row">
                <span><FileText :size="13" /> {{ resolveDocumentType(item.rawMatch) }}</span>
                <span><Calendar :size="13" /> {{ resolveDateOnly(item.rawMatch) }}</span>
                <span><ExternalLink :size="13" /> {{ resolveSource(item.rawMatch) }}</span>
              </div>
            </div>
            <span class="security-badge" :class="`security-${(resolveSecurityClass(item.rawMatch) || 'unknown').toLowerCase()}`">{{
              resolveSecurityClass(item.rawMatch) || 'Unknown'
            }}</span>
          </div>
        </button>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.results-count {
  margin: 0;
  margin-top: 1rem;
  color: #94a3b8;
  text-transform: uppercase;
  font-weight: 700;
}

.state-text {
  margin: 0;
  color: var(--color-text-secondary);
  padding: 0.7rem 0;
}

.results-list {
  margin-top: 1rem;
  list-style: none;
  display: grid;
  gap: 0.75rem;
}

.result-item {
  margin: 0;
}

.result-card {
  width: 100%;
  background: #ffffff;
  border: 1px solid #e6ebf2;
  border-radius: 16px;
  text-align: left;
  padding: 1.05rem 1rem;
}

.result-card:hover {
  border-color: #d8e1f0;
}

.result-card.active {
  background: #f6f8fc;
  border-color: #d7e0ec;
}

.result-main {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.8rem;
}

.result-content {
  min-width: 0;
}

.result-title {
  font-size: 1.1rem;
  line-height: 1.25;
  color: #0f172a;
}

.meta-row {
  margin-top: 0.5rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  color: #9aa7bb;
  font-size: 0.84rem;
}

.meta-row span {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
}

.security-badge {
  flex-shrink: 0;
  align-self: flex-start;
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 0.2rem 0.55rem;
  border-radius: 6px;
  border: 1px solid;
}

.security-public {
  color: #16a34a;
  background: #f0fdf4;
  border-color: #bbf7d0;
}

.security-internal {
  color: #2563eb;
  background: #eff6ff;
  border-color: #bfdbfe;
}

.security-sensitive {
  color: #aa7560;
  background: #fff7ed;
  border-color: #fed7aa;
}

.security-confidential {
  color: #dc2626;
  background: #fef2f2;
  border-color: #fecaca;
}
</style>
