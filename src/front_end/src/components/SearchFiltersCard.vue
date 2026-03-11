<script setup>
import { computed, ref } from 'vue'
import { Grid2X2, FileText, Shield } from 'lucide-vue-next'

const sourceFilters = ['GitHub', 'GitLab', 'Network File System'] // Add more sources needed if possible
const typeFilters = ['PDF (.pdf)', 'Word (.docx)', 'Excel (.xlsx)', 'Text / Markdown (.txt, .md)']
const securityFilters = ['Public', 'Internal', 'Sensitive','Confidential']

const selectedFilters = ref({
	source: [],
	type: [],
	security: []
})

const hasActiveFilters = computed(() => {
	return (
		selectedFilters.value.source.length > 0 ||
		selectedFilters.value.type.length > 0 ||
		selectedFilters.value.security.length > 0
	)
})

const isSelected = (filterType, value) => {
	return selectedFilters.value[filterType].includes(value)
}

// Placeholder for handling filter changes. 
// In a later implementation, this will probably update the search query or trigger a new search with the applied filters.
const handleFilterChange = (filterType, value) => {
	if (isSelected(filterType, value)) {
		selectedFilters.value[filterType] = selectedFilters.value[filterType].filter((item) => item !== value)
	} else {
		selectedFilters.value[filterType] = [...selectedFilters.value[filterType], value]
	}

	console.log(`Selected ${filterType} filters:`, selectedFilters.value[filterType])
}

const clearAllFilters = () => {
	selectedFilters.value = {
		source: [],
		type: [],
		security: []
	}
}
</script>


// This component is a placeholder for the search filters UI. It currently displays static filter options for demonstration purposes. 
// Later on these filter section needs to be more dynamic and interactive, allowing users to select and apply them to their search queries.

<template>
	<div class="filters-card">


		<div class="filters-row">
			<div class="filter-group">
				<span class="group-label">
					<Grid2X2 :size="14" />
					SOURCE:
				</span>
				<button
					v-for="item in sourceFilters"
					:key="item"
					:class="['chip', { active: isSelected('source', item) }]"
					type="button"
					:aria-pressed="isSelected('source', item)"
					@click="handleFilterChange('source', item)"
				>
					{{ item }}
				</button>
			</div>

			<span class="group-divider" aria-hidden="true"></span>

			<div class="filter-group">
				<span class="group-label">
					<FileText :size="14" />
					TYPE:
				</span>
				<button
					v-for="item in typeFilters"
					:key="item"
					:class="['chip', { active: isSelected('type', item) }]"
					type="button"
					:aria-pressed="isSelected('type', item)"
					@click="handleFilterChange('type', item)"
				>
					{{ item }}
				</button>
			</div>

			<span class="group-divider" aria-hidden="true"></span>

			<div class="filter-group">
				<span class="group-label">
					<Shield :size="14" />
					SECURITY:
				</span>
				<button
					v-for="item in securityFilters"
					:key="item"
					:class="['chip', { active: isSelected('security', item) }]"
					type="button"
					:aria-pressed="isSelected('security', item)"
					@click="handleFilterChange('security', item)"
				>
					{{ item }}
				</button>
			</div>
            <div class="filters-header">
                <button v-if="hasActiveFilters" class="clear-button" type="button" @click="clearAllFilters">
                    Clear all
                </button>
            </div>
		</div>
	</div>
</template>

<style scoped>
.filters-card {
	background: #f7f8fa;
	border: 1px solid #dde2ea;
	border-radius: 18px;
	padding: 0.95rem 1rem 1rem;
	margin-top: 0.8rem;
}

.filters-header {
	display: flex;
	align-items: center;
	justify-content: flex-end;
	margin-left: auto;
}

.filters-title {
	font-size: 0.82rem;
	font-weight: 700;
	letter-spacing: 0.03em;
	color: #99a4b8;
	text-transform: uppercase;
}

.clear-button {
	border: none;
	background: transparent;
	color: #7c3aed;
	font-size: 0.85rem;
	font-weight: 600;
	cursor: pointer;
	padding: 0.1rem 0.2rem;
}

.clear-button:hover {
	text-decoration: underline;
}

.filters-row {
	display: flex;
	flex-wrap: wrap;
	gap: 0.7rem;
	align-items: center;
}

.filter-group {
	display: flex;
	align-items: center;
	gap: 0.45rem;
	flex-wrap: wrap;
}

.group-label {
	display: inline-flex;
	align-items: center;
	gap: 0.35rem;
	color: #99a4b8;
	font-size: 0.82rem;
	font-weight: 700;
	letter-spacing: 0.03em;
	margin-right: 0.15rem;
}

.chip {
	border: none;
	border-radius: 999px;
	padding: 0.35rem 0.82rem;
	background: #edf0f4;
	color: #6f7e95;
	font-size: 0.93rem;
	line-height: 1;
	font-weight: 600;
	cursor: pointer;
}

.chip:hover {
	background: #e2e7ef;
}

.chip.active {
	background: linear-gradient(135deg, #5b21b6 0%, #7c3aed 100%);
	color: #ffffff;
}

.group-divider {
	width: 1px;
	height: 22px;
	background: #d9dfe8;
}

@media (max-width: 768px) {
	.filters-card {
		padding: 0.9rem;
	}

	.filters-header {
		width: 100%;
		justify-content: flex-end;
	}

	.group-divider {
		display: none;
	}
}
</style>