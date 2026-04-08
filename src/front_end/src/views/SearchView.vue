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
import { resolveFilename, TYPE_FILTERS } from '@/composables/useSearchMetadata'

/* Reactive state variables for search results and UI state */
const matches = ref([])
const allMatches = ref([])
const selectedFile = ref('')
const selectedMatch = ref(null)
const error = ref('')
const isSearching = ref(false)
const lastQuery = ref('')
const isPreviewOpen = ref(false)
const access_token = sessionStorage.getItem('access_token')
/* Base URL for API requests, configurable via environment variable */
const API_BASE_URL = import.meta.env.API_BASE_URL.replace(/\/$/, '')

/* Filters so it can access matches */
const selectedFilters = ref({
  source: [],
  type: [],
  security: []
})

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
    const res = await fetch(`${API_BASE_URL}/search?query=${encodeURIComponent(query)}`, {
    headers:{
      "Authorization": `Bearer ${access_token}`,
    },
  }
  )

    if (!res.ok) {
      error.value = `Search failed: ${res.status} ${await res.text()}`
      return
    }

    const data = await res.json()
    console.log('Search response:', data)
    const resultArray = Array.isArray(data) ? data : data.results || data.matches || []

    allMatches.value = resultArray
    matches.value = resultArray

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

/* Handle changes to search filters  */
// TODO: add source & security filtering.
const handleFilterChange = (filters) => {
  selectedFilters.value = filters
  console.log('Filter changed:', filters)
  // If no filters → show everything
  if (filters.source.length === 0 && filters.type.length === 0 && filters.security.length === 0) {
    matches.value = allMatches.value
    return
  }
  matches.value = allMatches.value.filter((match) => {
    const filename = (match.filename || match.name || '').toLowerCase()
    // const securityClass = resolveSecurityClass(match).toLowerCase()
    // const source = (match.source || '').toLowerCase()

    // TYPE FILTER
    const typeMatch =
      filters.type.length === 0 ||
      filters.type.some((filterLabel) => {
        // Find the TYPE_KEYWORDS entry that matches the selected filter
        const keywordsEntry = Object.entries(TYPE_FILTERS).find(([docType]) => docType === filterLabel)

        if (!keywordsEntry) return false

        const [, keywords] = keywordsEntry

        // Only match filename against the keywords for this filter
        return keywords.some((kw) => filename.endsWith(kw))
      })

    // SOURCE FILTER
    // const sourceMatch = filters.source.length === 0 || filters.source.some((s) => source.includes(s.toLowerCase()))

    // SECURITY FILTER
    // const securityMatch =
    //  filters.security.length === 0 || filters.security.some((selected) => securityClass === selected.toLowerCase())

    // add sourceMatch and secuirtyMatch later
    // return typeMatch && sourceMatch && secuirtyMatch
    return typeMatch //&& securityMatch
  })
}
</script>

<template>
  <!-- Search View Section -->
  <section class="search-view">
    <!-- Search Bar Component -->
    <SearchBar :loading="isSearching" @search="handleSearch" />

    <!-- Search Filters Component -->
    <SearchFiltersCard :selectedFilters="selectedFilters" @update:filters="handleFilterChange" />

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
