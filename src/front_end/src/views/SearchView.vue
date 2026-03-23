<script setup>
/**
 * The SearchView view
 * Main interface for searching documents, showing results, and previewing file details.
 * Integrates SearchBar, SearchFiltersCard, SearchMatches, and SearchPreviewDrawer components.
 * Handles search logic, state management for matches and selected file, and interactions between components.
 *
 * @view
 * @example usage:
 * <SearchView />
 * This view is rendered at the /search route of the application.
 */

import { ref } from 'vue'
import SearchBar from '@/components/SearchBar.vue'
import SearchFiltersCard from '@/components/SearchFiltersCard.vue'
import SearchMatches from '@/components/SearchMatches.vue'
import SearchPreviewDrawer from '@/components/SearchPreviewDrawer.vue'
import { resolveFilename } from '@/composables/useSearchMetadata'

/* Reactive state variables for search results and UI state */
const matches = ref([])
const selectedFile = ref('')
const selectedMatch = ref(null)
const error = ref('')
const isSearching = ref(false)
const lastQuery = ref('')
const isPreviewOpen = ref(false)

/* Base URL for API requests, configurable via environment variable */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL.replace(/\/$/, '')

/* Performs a search when the SearchBar emits a search event */
const handleSearch = async (query) => {
  lastQuery.value = query

  error.value = ''
  matches.value = []
  selectedFile.value = ''
  selectedMatch.value = null
  isPreviewOpen.value = false

  if (!query || !query.trim()) {
    error.value = 'Please enter a search term.'
    return
  }

  isSearching.value = true
  try {
    const res = await fetch(`${API_BASE_URL}/search?query=${encodeURIComponent(query)}`)

    if (!res.ok) {
      error.value = `Search failed: ${res.status} ${await res.text()}`
      return
    }

    const data = await res.json()
    console.log('Search response:', data)
    matches.value = Array.isArray(data) ? data : data.results || data.matches || []

    if (matches.value.length === 0) {
      error.value = 'No matching files found.'
      return
    }
  } catch (e) {
    error.value = `Search error: ${String(e)}`
  } finally {
    isSearching.value = false
  }
}

/* Handles selection of a search result match, updating state and opening the preview drawer */
const selectMatch = (match) => {
  if (!match) return

  selectedMatch.value = match
  selectedFile.value = resolveFilename(match)

  isPreviewOpen.value = true
}

/* Closes the search preview drawer */
const closePreview = () => {
  isPreviewOpen.value = false
}

/* Handle changes to search filters (currently just logs the change) */
const handleFilterChange = (filter) => {
  console.log('Filter changed:', filter)
}
</script>

<template>
  <!-- Search View Section -->
  <section class="search-view">
    <!-- Search Bar Component -->
    <SearchBar @search="handleSearch" />

    <!-- Search Filters Component -->
    <SearchFiltersCard @filter-change="handleFilterChange" />

    <!-- Search Matches Component -->
    <SearchMatches :matches="matches" :loading="isSearching" :selected="selectedFile" :query="lastQuery" @select="selectMatch" />

    <!-- Search Preview Drawer Component -->
    <SearchPreviewDrawer
      :open="isPreviewOpen"
      :selected-file="selectedFile"
      :selected-match="selectedMatch"
      :matches="matches"
      @close="closePreview"
    />
  </section>
</template>

<style scoped>
.search-view {
  padding: 1rem;
}
</style>
