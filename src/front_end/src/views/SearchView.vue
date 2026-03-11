<script setup>
import SearchBar from '@/components/SearchBar.vue'
import SearchFiltersCard from '@/components/SearchFiltersCard.vue'

// Placeholder for the search view. 
// It currently includes the SearchBar and a static SearchFiltersCard.

// The handleSearch function is a placeholder for the actual search logic. 
// It currently just logs the search query to the console. 
// In a later implementation, this will probably be what makes the API call to perform the search
const handleSearch = (query) => {
	console.log('Searching for:', query) // enter and button works
}

// same as handleSearch, this is a placeholder for handling filter changes. 
// It currently just logs the changed filter to the console.
// I like to see that things happens :)
const handleFilterChange = (filter) => {
	console.log('Filter changed:', filter) // placeholder for handling filter changes
}
</script>

<template>
	<section class="search-view">
		<SearchBar @search="handleSearch" />
		<p class="search-hint">Click Search or press Enter to search.</p>
		<SearchFiltersCard @filter-change="handleFilterChange" />
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
</style>
