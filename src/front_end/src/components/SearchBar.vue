<script setup>
/**
 * SearchBar Component
 * A simple search input component that emits a search event with the user's query.
 *
 * @component
 * @example usage in SearchView.vue:
 * <SearchBar @search="handleSearch" />
 */

import { computed, ref } from 'vue'
import { Search } from 'lucide-vue-next'

/* Props received from SearchView */
const props = defineProps({
  loading: { type: Boolean, default: false }
})

/* Emit to parent component (SearchView) when a search is performed */
const emit = defineEmits(['search', 'documents-only-change'])

/* Notify parent when user toggles between documents-only and all files mode */
const toggleDocumentsOnly = () => {
  documentsOnly.value = !documentsOnly.value
  emit('documents-only-change', documentsOnly.value)
}

/* Handle search action when user clicks the search button or presses Enter */
const handleSearch = () => {
  const query = searchQuery.value.trim()
  if (!query) {
    return
  }

  emit('search', { query, documentsOnly: documentsOnly.value })
  searchQuery.value = ''
}

/* Disable search button if query is empty or currently searching */
const isSearchDisabled = computed(() => !searchQuery.value.trim() || props.loading)

/* Documents Only button True by defult, user can click to disable it and search all files, when enabled it will only search documents */
const documentsOnly = ref(true)

/* Search query state */
const searchQuery = ref('')
</script>

<template>
  <!-- Search Bar Form -->
  <form class="search-input-wrap" @submit.prevent="handleSearch">
    <Search class="search-icon" />
    <input
      v-model="searchQuery"
      class="search-input"
      type="text"
      :disabled="loading"
      :placeholder="loading ? 'Searching...' : 'Search for documents across all sources...'"
    />
    <!-- Button to choose Documents Only or not, sends down true or false when user search -->
    <button class="documents-only-button" type="button" @click="toggleDocumentsOnly">
      {{ documentsOnly ? 'Showing Documents Only' : 'Showing All Files' }}
    </button>
    <!-- Search button to trigger the search action -->
    <button class="search-button" type="submit" :disabled="isSearchDisabled">Search</button>
  </form>
</template>

<style scoped>
.search-input-wrap {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  background: #ffffff;
  border: 1px solid #d8dee7;
  border-radius: 13px;
  min-height: 60px;
  padding: 0 1rem;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
}

.search-icon {
  color: #97a3b6;
  width: 20px;
  height: 20px;
  stroke-width: 2;
}

.search-input {
  border: none;
  width: 100%;
  background: transparent;
  font-size: 1rem;
  line-height: 1.2;
  color: #6f7e95;
  outline: none;
}

.search-input::placeholder {
  color: #6f7e95;
}

.search-input:disabled {
  opacity: 0.75;
  cursor: not-allowed;
}

.search-button {
  border: none;
  border-radius: 10px;
  padding: 0.55rem 0.9rem;
  background: linear-gradient(135deg, #5b21b6 0%, #7c3aed 100%);
  color: #ffffff;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}

.search-button:hover {
  opacity: 0.95;
}

.search-button:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.documents-only-button {
  border: none;
  border-radius: 10px;
  padding: 0.55rem 0.9rem;
  background: linear-gradient(135deg, #5b21b6 0%, #7c3aed 100%);
  color: #ffffff;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}

@media (max-width: 1200px) {
  .search-input {
    font-size: 1.6rem;
  }
}

@media (max-width: 768px) {
  .search-input-wrap {
    min-height: 58px;
  }

  .search-input {
    font-size: 1.1rem;
  }

  .search-button {
    padding: 0.5rem 0.8rem;
    font-size: 0.85rem;
  }
}
</style>
