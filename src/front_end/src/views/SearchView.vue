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

import { ref, computed } from 'vue'
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'
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
const currentPage = ref(1)
const offset = computed(() => (currentPage.value - 1) * SEARCH_COUNT)

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

  if (resetPreview) {
    currentPage.value = 1
  }

  isSearching.value = true
  try {
    const params = new URLSearchParams({
      count: String(SEARCH_COUNT),
      offset: String(offset.value)
    })
    const payload = searchPayload(query, documentsOnly, file_type, source_system, security_class)

    const res = await authFetch(`${API_PATHS.search}?${params.toString()}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    if (!res.ok) {
      error.value = `Search failed: ${res.status} ${await res.text()}`
      return
    }

    const data = await res.json()
    const resultArray = Array.isArray(data) ? data : data.results || data.matches || []

    allMatches.value = resultArray
    matches.value = filterMatches(resultArray, selectedFilters.value)

    if (matches.value.length === 0 && currentPage.value === 1) {
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

const filterMatches = (results, filters) => {
  if (!filters.source.length && !filters.type.length && !filters.security.length) {
    return results
  }

  return results.filter((match) => {
    const filetype = resolveDocumentExtension(match).toLowerCase()
    const securityClass = resolveSecurityClass(match).toLowerCase()
    const source = resolveSource(match).toLowerCase()

    const typeMatch =
      filters.type.length === 0 ||
      filters.type.some((selected) => {
        const extensions = selected.split('|')
        return extensions.some((ext) => filetype === ext.toLowerCase())
      })

    const sourceMatch = filters.source.length === 0 || filters.source.some((selected) => source === selected.toLowerCase())

    const securityMatch =
      filters.security.length === 0 || filters.security.some((selected) => securityClass === selected.toLowerCase())

    return typeMatch && sourceMatch && securityMatch
  })
}

const searchWithFilters = async ({ query, documentsOnly, resetPreview = true, file_type, source_system, security_class }) => {
  await handleSearch({
    query,
    documentsOnly,
    resetPreview,
    ...searchParams(),
    file_type,
    source_system,
    security_class
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
  matches.value = filterMatches(allMatches.value, filters)
}

/* Sends down a new request to the backend if the user changes the filters */
const handleFilterChangeAndSearch = async (filters) => {
  selectedFilters.value = filters
  currentPage.value = 1

  if (lastQuery.value && lastQuery.value.trim()) {
    await searchWithFilters({
      query: lastQuery.value,
      documentsOnly: documentsOnlyMode.value,
      resetPreview: false,
      file_type: filters.type.join(' '),
      source_system: filters.source.join(' '),
      security_class: filters.security.join(' ')
    })
  }
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

const nextPage = async () => {
  currentPage.value++
  await searchWithFilters({
    query: lastQuery.value,
    documentsOnly: documentsOnlyMode.value,
    resetPreview: false,
    ...searchParams()
  })

  if (matches.value.length === 0) {
    currentPage.value--
  }
}

const previousPage = async () => {
  if (currentPage.value > 1) {
    currentPage.value--
    await searchWithFilters({
      query: lastQuery.value,
      documentsOnly: documentsOnlyMode.value,
      resetPreview: false,
      ...searchParams()
    })
  }
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

    <!-- Paging functionality? -->
    <div v-if="matches.length > 0" class="pagination">
      <div class="button-slot">
        <button v-if="currentPage > 1" @click="previousPage"><ChevronLeft /></button>
      </div>

      <span>Page {{ currentPage }}</span>

      <div class="button-slot">
        <button v-if="matches.length >= SEARCH_COUNT" @click="nextPage"><ChevronRight /></button>
      </div>
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

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1.5rem;
  padding: 1rem 0;
}

.button-slot {
  width: 40px;
  height: 40px;
  align-items: center;
  justify-content: center;
  display: flex;
}

.pagination button {
  padding: 0.5rem 1rem;
  border-radius: 10px;
  background: linear-gradient(135deg, #5b21b6 0%, #7c3aed 100%);
  color: #ffffff;
}
</style>
