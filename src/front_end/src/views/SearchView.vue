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
import { resolveDocumentExtension, resolveSecurityClass, resolveSource } from '@/composables/useSearchMetadata'
import { authFetch, API_PATHS } from '@/utils/api'

/* Reactive state variables for search results and UI state */
const matches = ref([])
const allMatches = ref([])
const selectedFile = ref('')
const selectedMatch = ref(null)
const lastQuery = ref('')
const isPreviewOpen = ref(false)

const error = ref('')
const isSearching = ref(false)
const documentsOnlyMode = ref(true)

/* Number of search results to fetch, possible to change. */
const SEARCH_COUNT = 20
const SEARCH_OFFSET = 0

/* Filters so it can access matches */
const selectedFilters = ref({
  source: [],
  type: [],
  security: []
})

const searchPayload = (query, documentsOnly, file_type, source_system, security_class) => {
  const payload = {
    content: query
  }
  if (documentsOnly) {
    payload.documents_only = 'true'
  }
  if (file_type) {
    payload.file_type = file_type.split('|').join(' ')
  }
  if (source_system) {
    payload.source_system = source_system
  }
  if (security_class) {
    payload.security_class = security_class
  }
  return payload
}

/* Performs a search when the SearchBar emits a search event and includes filter parameters if any */
const handleSearch = async ({ query, documentsOnly, file_type, source_system, security_class, resetPreview = true }) => {
  documentsOnlyMode.value = documentsOnly
  lastQuery.value = query

  error.value = ''
  if (resetPreview) {
    matches.value = []
    selectedFile.value = ''
    selectedMatch.value = null
    isPreviewOpen.value = false
  }

  if (!query || !query.trim()) {
    error.value = 'Please enter a search term.'
    return
  }

  isSearching.value = true
  try {
    const params = new URLSearchParams({
      count: String(SEARCH_COUNT),
      offset: String(SEARCH_OFFSET)
    })
    const payload = searchPayload(query, documentsOnly, file_type, source_system, security_class)

    const res = await authFetch(`${API_PATHS.search}?${params.toString()}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    console.log(res)
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

const searchParams = () => ({
  file_type: selectedFilters.value.type.join(' '),
  source_system: selectedFilters.value.source.join(' '),
  security_class: selectedFilters.value.security.join(' ')
})

const searchWithFilters = async ({ query, documentsOnly }) => {
  await handleSearch({
    query,
    documentsOnly,
    ...searchParams()
  })
}

/* Should send down a new request to the backend if the user press the button */
const handleDocumentsOnlyChange = (documentsOnly) => {
  documentsOnlyMode.value = documentsOnly
  if (lastQuery.value && lastQuery.value.trim()) {
    searchWithFilters({
      query: lastQuery.value,
      documentsOnly
    })
  }
}

/* Handles selection of a search result match, updating state and opening the preview drawer */
const selectMatch = (match) => {
  if (!match) return

  selectedMatch.value = match
  isPreviewOpen.value = true
}

/* Closes the search preview drawer */
const closePreview = () => {
  isPreviewOpen.value = false
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
    const source = resolveSource(match).toLowerCase()

    // TYPE FILTER
    const typeMatch =
      filters.type.length === 0 ||
      filters.type.some((selected) => {
        // Split the group string from json file (e.g., ".docx .doc .odt") and check if filetype is in it
        const extensions = selected.split('|')
        return extensions.some((ext) => filetype === ext.toLowerCase())
      })

    // SOURCE FILTER
    const sourceMatch = filters.source.length === 0 || filters.source.some((selected) => source === selected.toLowerCase())

    // SECURITY FILTER
    const securityMatch =
      filters.security.length === 0 || filters.security.some((selected) => securityClass === selected.toLowerCase())

    return typeMatch && sourceMatch && securityMatch
  })
}

/* Sends down a new request to the backend if the user changes the filters */
const handleFilterChangeAndSearch = async (filters) => {
  selectedFilters.value = filters
  if (lastQuery.value && lastQuery.value.trim()) {
    await handleSearch({
      query: lastQuery.value,
      documentsOnly: documentsOnlyMode.value,
      file_type: filters.type.join(' '),
      source_system: filters.source.join(' '),
      security_class: filters.security.join(' '),
      resetPreview: false
    })
  }
  // Apply filter AFTER server results are loaded
  handleFilterChange(filters)
}

// searching a second time automatically to update the security levels
const refreshCurrentSearch = async () => {
  // prevents empty search.
  if (!lastQuery.value || !lastQuery.value.trim()) return

  await searchWithFilters({
    query: lastQuery.value,
    documentsOnly: documentsOnlyMode.value,
    resetPreview: false
  })
}
</script>

<template>
  <!-- Search View Section -->
  <section class="search-view">
    <div class="search-static">
      <!-- Search Bar Component -->
      <SearchBar :loading="isSearching" @search="searchWithFilters" @documents-only-change="handleDocumentsOnlyChange" />

      <!-- Search Filters Component -->
      <SearchFiltersCard
        :selectedFilters="selectedFilters"
        :documentsOnly="documentsOnlyMode"
        @update:filters="handleFilterChangeAndSearch"
      />
    </div>

    <!-- Search Matches Component -->
    <div class="search-results-scroll">
      <SearchMatches
        :matches="matches"
        :loading="isSearching"
        :selected="selectedFile"
        :query="lastQuery"
        @select="selectMatch"
        @update-security="refreshCurrentSearch"
      />
    </div>

    <!-- Search Preview Drawer Component -->
    <SearchPreviewDrawer
      :open="isPreviewOpen"
      :selected-file="selectedFile"
      :selected-match="selectedMatch"
      :matches="matches"
      @close="closePreview"
      @update-security="refreshCurrentSearch"
    />
  </section>
</template>

<style scoped>
.search-view {
  display: flex;
  flex-direction: column;
  padding: 1rem;
  box-sizing: border-box;
}

.search-static {
  position: sticky;
  top: 0;
  z-index: 10;
  background: #f5f6fa;
  padding-bottom: 1rem;
}

.search-results-scroll {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
</style>
