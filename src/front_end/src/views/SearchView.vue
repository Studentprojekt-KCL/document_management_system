<script setup>
import { ref } from "vue";

import SearchBar from "@/components/SearchBar.vue";
import SearchFiltersCard from "@/components/SearchFiltersCard.vue";
import SearchMatches from "@/components/SearchMatches.vue"; // <-- your new component

const matches = ref([]);
const selectedFile = ref("");
const fileContent = ref("");
const error = ref("");
const isSearching = ref(false);
const isLoadingFile = ref(false);

const handleSearch = async (query) => {
  console.log("Searching for:", query);

  error.value = "";
  matches.value = [];
  selectedFile.value = "";
  fileContent.value = "";

  if (!query || !query.trim()) {
    error.value = "Please enter a search term.";
    return;
  }


  isSearching.value = true;
  try {
    // If you use Vite proxy, change to: `/api/files/search?...`
    const res = await fetch(
      `/api/files/search?q=${encodeURIComponent(query)}`
    );

    if (!res.ok) {
      error.value = `Search failed: ${res.status} ${await res.text()}`;
      return;
    }

    const data = await res.json();
    matches.value = data.matches || [];

    if (matches.value.length === 0) {
      error.value = "No matching files found.";
    }
  } catch (e) {
    error.value = `Search error: ${String(e)}`;
  } finally {
    isSearching.value = false;
  }
};

const fetchData = async (filename) => {
  error.value = "";
  selectedFile.value = filename;
  fileContent.value = "";

  isLoadingFile.value = true;
  try {
    // If you use Vite proxy, change to: `/api/files/${...}`
    const res = await fetch(
      `api/files/${encodeURIComponent(filename)}`
    );

    if (!res.ok) {
      error.value = `Load failed: ${res.status} ${await res.text()}`;
      return;
    }

    fileContent.value = await res.text();
  } catch (e) {
    error.value = `Load error: ${String(e)}`;
  } finally {
    isLoadingFile.value = false;
  }
};

const handleFilterChange = (filter) => {
  console.log("Filter changed:", filter);
};
</script>

<template>
  <section class="search-view">
    <SearchBar @search="handleSearch" />
    <p class="search-hint">Click Search or press Enter to search.</p>
    <SearchFiltersCard @filter-change="handleFilterChange" />

    <p v-if="error" class="error">{{ error }}</p>

    <div class="results-layout">
      <!-- Left: matches -->
      <SearchMatches
        :matches="matches"
        :loading="isSearching"
        :selected="selectedFile"
        @select="fetchData"
      />

      <!-- Right: preview -->
      <div class="preview">
        <h3>Preview</h3>
        <p v-if="isLoadingFile">Loading {{ selectedFile }}…</p>
        <p v-else-if="!fileContent">Select a file to preview.</p>

        <pre v-else class="preview-box">{{ fileContent }}</pre>
      </div>
    </div>
  </section>
</template>

<style scoped>
.search-view {
  padding: 1rem;
}

.search-hint {
  font-size: 0.85rem;
  margin: 0.45rem 0 0;
}

.error {
  margin-top: 1rem;
  color: #b91c1c;
  white-space: pre-wrap;
}

.results-layout {
  margin-top: 1.25rem;
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 1rem;
  align-items: start;
}

.preview-box {
  white-space: pre-wrap;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 0.75rem;
}
</style>