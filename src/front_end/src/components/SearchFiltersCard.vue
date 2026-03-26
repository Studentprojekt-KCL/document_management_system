<script setup>
import { computed, watch, reactive } from 'vue'
import { Grid2X2, FileText, Shield } from 'lucide-vue-next'

const sourceFilters = ['GitHub', 'GitLab', 'Network File System']
const typeFilters = ['PDF (.pdf)', 'Word (.docx)', 'Excel (.xlsx)', 'Text / Markdown (.txt, .md)']
const securityFilters = ['Public', 'Internal', 'Sensitive', 'Confidential']

const props = defineProps({
  selectedFilters: Object
})
const emit = defineEmits(['update:filters'])

// Make reactive local copy
const localFilters = reactive({
  source: [...props.selectedFilters.source],
  type: [...props.selectedFilters.type],
  security: [...props.selectedFilters.security]
})

// Keep local filters in sync with parent
watch(
  () => props.selectedFilters,
  (newFilters) => {
    localFilters.source = [...newFilters.source]
    localFilters.type = [...newFilters.type]
    localFilters.security = [...newFilters.security]
  },
  { deep: true, immediate: true }
)

const hasActiveFilters = computed(() => {
  return localFilters.source.length > 0 || localFilters.type.length > 0 || localFilters.security.length > 0
})

const isSelected = (filterType, value) => localFilters[filterType].includes(value)

const handleFilterChange = (filterType, value) => {
  if (isSelected(filterType, value)) {
    localFilters[filterType] = localFilters[filterType].filter((item) => item !== value)
  } else {
    localFilters[filterType] = [...localFilters[filterType], value]
  }
  emit('update:filters', { ...localFilters })
}

const clearAllFilters = () => {
  localFilters.source = []
  localFilters.type = []
  localFilters.security = []
  emit('update:filters', { ...localFilters })
}
</script>

// This component is a placeholder for the search filters UI. It currently displays static filter options for demonstration
purposes. // Later on these filter section needs to be more dynamic and interactive, allowing users to select and apply them to
their search queries.

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
    </div>

    <div class="filters-header">
      <button
        v-if="hasActiveFilters"
        class="clear-button"
        type="button"
        @click="clearAllFilters"
      >
        Clear all
      </button>
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
  justify-content: flex-end;
  margin-top: 0.5rem;
}

.clear-button {
  border: none;
  background: transparent;
  color: #7c3aed;
  font-weight: 600;
  cursor: pointer;
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
  font-weight: 700;
  margin-right: 0.15rem;
}

.chip {
  border: none;
  border-radius: 999px;
  padding: 0.35rem 0.82rem;
  background: #edf0f4;
  color: #6f7e95;
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
  .group-divider {
    display: none;
  }
}
</style>