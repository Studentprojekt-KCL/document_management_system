<script setup>
import { Search as SearchIcon, Grid2X2, FileText, Shield } from 'lucide-vue-next'

const sourceFilters = ['Google Drive', 'SharePoint', 'Slack']
const typeFilters = ['PDF', 'Sheets', 'Docs', 'Messages']
const securityFilters = ['Public', 'Internal', 'Confidential', 'Highly']
</script>

<template>
	<section class="search-view">
		<div class="search-input-wrap">
			<SearchIcon class="search-icon" :size="28" />
			<input
				class="search-input"
				type="text"
				placeholder="Search across all sources, documents, and messages..."
			/>
		</div>

		<div class="filters-card">
			<div class="filters-row">
				<div class="filter-group">
					<span class="group-label">
						<Grid2X2 :size="14" />
						SOURCE:
					</span>
					<button v-for="item in sourceFilters" :key="item" class="chip" type="button">{{ item }}</button>
				</div>

				<span class="group-divider" aria-hidden="true"></span>

				<div class="filter-group">
					<span class="group-label">
						<FileText :size="14" />
						TYPE:
					</span>
					<button v-for="item in typeFilters" :key="item" class="chip" type="button">{{ item }}</button>
				</div>

				<span class="group-divider" aria-hidden="true"></span>

				<div class="filter-group">
					<span class="group-label">
						<Shield :size="14" />
						SECURITY:
					</span>
					<button v-for="item in securityFilters" :key="item" class="chip" type="button">{{ item }}</button>
				</div>
			</div>
		</div>
	</section>
</template>

<style scoped>
.search-view {
	padding: 1rem;
}

.filters-card {
	background: #f7f8fa;
	border: 1px solid #dde2ea;
	border-radius: 18px;
	padding: 0.95rem 1rem 1rem;
	margin-top: 0.8rem;
}

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

.group-divider {
	width: 1px;
	height: 22px;
	background: #d9dfe8;
}

@media (max-width: 1200px) {
	.search-input {
		font-size: 1.6rem;
	}
}

@media (max-width: 768px) {
	.filters-card {
		padding: 0.9rem;
	}

	.search-input-wrap {
		min-height: 58px;
	}

	.search-input {
		font-size: 1.1rem;
	}

	.group-divider {
		display: none;
	}
}
</style>
