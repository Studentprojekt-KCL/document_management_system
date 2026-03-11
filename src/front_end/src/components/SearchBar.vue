<script setup>
import { ref } from 'vue'
import { Search as SearchIcon } from 'lucide-vue-next'

const emit = defineEmits(['search'])

// Search query empty first
const searchQuery = ref('')

// Handle search action when user clicks the search button or presses Enter
const handleSearch = () => {
	const query = searchQuery.value.trim()
	if (!query) {
		return
	}

	emit('search', query)
	searchQuery.value = ''
}
</script>

<template>
	<form class="search-input-wrap" @submit.prevent="handleSearch">
		<SearchIcon class="search-icon" :size="28" />
		<input
			v-model="searchQuery"
			class="search-input"
			type="text"
			placeholder="Search for documents across all sources..."
		/>
		<button class="search-button" type="submit">Search</button>
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
	flex-shrink: 0;
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

.search-button {
	border: none;
	border-radius: 10px;
	padding: 0.55rem 0.9rem;
    background: linear-gradient(135deg, #5B21B6 0%, #7C3AED 100%);
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
