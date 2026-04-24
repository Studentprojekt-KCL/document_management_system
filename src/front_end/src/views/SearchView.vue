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
import { useAppState } from '@/composables/useAppState'
import SearchBar from '@/components/SearchBar.vue'
import SearchFiltersCard from '@/components/SearchFiltersCard.vue'
import SearchMatches from '@/components/SearchMatches.vue'
import SearchPreviewDrawer from '@/components/SearchPreviewDrawer.vue'
import { resolveDocumentExtension, resolveSecurityClass } from '@/composables/useSearchMetadata'
import { authFetch, API_PATHS } from '@/utils/api'

/* Reactive state variables for search results and UI state */
const {
  searchMatches: matches,
  searchAllMatches: allMatches,
  selectedFile,
  selectedMatch,
  lastQuery,
  isPreviewOpen,
  markStateChanged,
  stateReady
} = useAppState()

const error = ref('')
const isSearching = ref(false)

/* Filters so it can access matches */
const selectedFilters = ref({
  source: [],
  type: [],
  security: []
})

/* Performs a search when the SearchBar emits a search event */
const handleSearch = async (query) => {
  lastQuery.value = query
  markStateChanged()

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
    //const res = await authFetch(`${API_PATHS.search}?query=${encodeURIComponent(query)}`)
    const res = await authFetch(`${API_PATHS.search}?query=${encodeURIComponent(query)}`)

    if (!res.ok) {
      error.value = `Search failed: ${res.status} ${await res.text()}`
      return
    }

    const data = await res.json()
    console.log('Search response:', data)
    const resultArray = Array.isArray(data) ? data : data.results || data.matches || []

    allMatches.value = resultArray
    matches.value = resultArray
    markStateChanged()

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
  isPreviewOpen.value = true
  markStateChanged()
}

/* Closes the search preview drawer */
const closePreview = () => {
  isPreviewOpen.value = false
  markStateChanged()
}

/* Handle changes to search filters  */
const handleFilterChange = (filters) => {
  selectedFilters.value = filters
  // If no filters → show everything
  if (filters.source.length === 0 && filters.type.length === 0 && filters.security.length === 0) {
    matches.value = allMatches.value
    return
  }
  matches.value = allMatches.value.filter((match) => {
    const filetype = resolveDocumentExtension(match).toLowerCase()
    const securityClass = resolveSecurityClass(match).toLowerCase()
    // const source = (match.source || '').toLowerCase()

    // TYPE FILTER
    const typeMatch =
      filters.type.length === 0 ||
      filters.type.some((selected) => {
        // Split the group string from json file (e.g., ".docx|.doc|.odt") and check if filetype is in it
        const extensions = selected.split('|')
        return extensions.some((ext) => filetype === ext.toLowerCase())
      })

    // SOURCE FILTER
    //const sourceMatch = filters.source.length === 0 || filters.source.some((s) => source.includes(s.toLowerCase()))

    // SECURITY FILTER
    const securityMatch =
      filters.security.length === 0 || filters.security.some((selected) => securityClass === selected.toLowerCase())

    // add sourceMatch later
    // return typeMatch && sourceMatch && securityMatch
    return typeMatch && securityMatch
  })
  markStateChanged()
}
</script>

<template>
  <!-- Search View Section -->
  <section v-if="stateReady" class="search-view">
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
  <section v-else class="search-view">Loading Search state...</section>
</template>

<style scoped>
.search-view {
  padding: 1rem;
}
</style>
