<script setup>
import { computed, ref } from 'vue'
import { Grid2X2, FileText, Shield } from 'lucide-vue-next'
import { TYPE_FILTERS } from '@/composables/useSearchMetadata'
import { useSourceFilters, useSecurityFilters } from '@/composables/useFilters'

/* Type filter labels derived from the canonical TYPE_FILTERS map. */
const typeFilters = Object.keys(TYPE_FILTERS) // WIll be changed soon
const sourceFilters = useSourceFilters()
const securityFilters = useSecurityFilters()

const props = defineProps({
  selectedFilters: Object
})
const emit = defineEmits(['update:filters'])

/* Local refs for filter selection */
const localSource = ref([...props.selectedFilters.source])
const localType = ref([...props.selectedFilters.type])
const localSecurity = ref([...props.selectedFilters.security])

/* Computed to check if any filters are active */
const hasActiveFilters = computed(
  () => localSource.value.length > 0 || localType.value.length > 0 || localSecurity.value.length > 0
)

/* Check if a filter is selected */
const isSelected = (filterType, value) => {
  if (filterType === 'source') return localSource.value.includes(value)
  if (filterType === 'type') return localType.value.includes(value)
  if (filterType === 'security') return localSecurity.value.includes(value)
  return false
}

/* Toggle filter selection */
const toggleFilter = (filterType, value) => {
  let refArray
  if (filterType === 'source') refArray = localSource
  else if (filterType === 'type') refArray = localType
  else if (filterType === 'security') refArray = localSecurity
  else return

  if (refArray.value.includes(value)) {
    refArray.value = refArray.value.filter((f) => f !== value)
  } else {
    refArray.value = [...refArray.value, value]
  }
  emit('update:filters', {
    source: localSource.value,
    type: localType.value,
    security: localSecurity.value
  })
}

/* Clear all filters */
const clearAllFilters = () => {
  localSource.value = []
  localType.value = []
  localSecurity.value = []
  emit('update:filters', {
    source: [],
    type: [],
    security: []
  })
}
</script>

<template>
  <div class="filters-card">
    <div class="filters-row">
      <!-- Source Filters -->
      <div class="filter-group">
        <span class="group-label">
          <Grid2X2 :size="14" />
          SOURCE:
        </span>
        <button
          v-for="item in sourceFilters"
          :key="item"
          :class="['chip', { active: isSelected('source', item) }]"
          @click="toggleFilter('source', item)"
        >
          {{ item }}
        </button>
      </div>

      <span class="group-divider" aria-hidden="true"></span>

      <!-- Type Filters -->
      <div class="filter-group">
        <span class="group-label">
          <FileText :size="14" />
          TYPE:
        </span>
        <button
          v-for="item in typeFilters"
          :key="item"
          :class="['chip', { active: isSelected('type', item) }]"
          @click="toggleFilter('type', item)"
        >
          {{ item }}
        </button>
      </div>

      <span class="group-divider" aria-hidden="true"></span>

      <!-- Security Filters -->
      <div class="filter-group">
        <span class="group-label">
          <Shield :size="14" />
          SECURITY:
        </span>
        <button
          v-for="item in securityFilters"
          :key="item"
          :class="['chip', { active: isSelected('security', item) }]"
          @click="toggleFilter('security', item)"
        >
          {{ item }}
        </button>
      </div>
      <div class="filters-header">
        <button v-if="hasActiveFilters" class="clear-button" @click="clearAllFilters">Clear all</button>
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

.clear-button {
  border: none;
  background: transparent;
  color: #7c3aed;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  padding: 0.1rem 0.6rem;
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
