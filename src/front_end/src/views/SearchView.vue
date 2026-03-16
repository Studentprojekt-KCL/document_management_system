<script setup>
import { ref } from 'vue'
import SearchBar from '@/components/SearchBar.vue'
import SearchFiltersCard from '@/components/SearchFiltersCard.vue'
import SearchMatches from '@/components/SearchMatches.vue'
import SearchPreviewDrawer from '@/components/SearchPreviewDrawer.vue'
import { resolveFilename } from '@/composables/useSearchMetadata'

const matches = ref([])
const selectedFile = ref('')
const selectedMatch = ref(null)
const error = ref('')
const isSearching = ref(false)
const lastQuery = ref('')
const isPreviewOpen = ref(false)

// --- Search for matches ---
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
    // the endpoint is /search in main API.
    const res = await fetch(`/api/search?query=${encodeURIComponent(query)}`)

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

// --- Handle selecting a match ---
const selectMatch = (match) => {
  if (!match) return

  selectedMatch.value = match
  selectedFile.value = resolveFilename(match)

  isPreviewOpen.value = true
}

const closePreview = () => {
  isPreviewOpen.value = false
}

const handleFilterChange = (filter) => {
  console.log('Filter changed:', filter)
}
</script>

<template>
  <section class="search-view">
    <SearchBar @search="handleSearch" />
    <SearchFiltersCard @filter-change="handleFilterChange" />

    <SearchMatches :matches="matches" :loading="isSearching" :selected="selectedFile" :query="lastQuery" @select="selectMatch" />
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
