<script setup>
import { computed } from 'vue'
import { Calendar, FileText } from 'lucide-vue-next'
import { useSearchMetadata } from '@/composables/useSearchMetadata'

const props = defineProps({
  matches: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  selected: { type: String, default: '' },
  query: { type: String, default: '' }
})

const emit = defineEmits(['select'])
const { normalizeMatches, resolveMatchDate } = useSearchMetadata(props)

const normalizedMatches = computed(() => normalizeMatches(props.matches))

const resultsLabel = computed(() => {
  const count = normalizedMatches.value.length
  if (count === 0) {
    return `No results found for "${props.query}"`
  }
  return `Found ${count} result${count === 1 ? '' : 's'} for "${props.query}"`
})
</script>

<template>
  <div class="results-shell">
    <p v-if="loading" class="state-text">Searching…</p>
    <p v-else-if="query" class="results-count">{{ resultsLabel }}</p>

    <ul class="results-list">
      <li v-for="item in normalizedMatches" :key="item.filename" class="result-item">
        <button class="result-card" :class="{ active: selected === item.filename }" @click="emit('select', item.rawMatch)">
          <div class="result-main">
            <div class="result-content">
              <h3 class="result-title">{{ item.title }}</h3>

              <div class="meta-row">
                <span><FileText :size="13" /> {{ item.type }}</span>
                <span><Calendar :size="13" /> {{ resolveMatchDate(item.rawMatch) }}</span>
              </div>
            </div>
          </div>
        </button>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.results-count {
  margin: 0;
  margin-top: 1rem;
  color: #94a3b8;
  text-transform: uppercase;
  font-weight: 700;
}

.state-text {
  margin: 0;
  color: var(--color-text-secondary);
  padding: 0.7rem 0;
}

.results-list {
  margin-top: 1rem;
  list-style: none;
  display: grid;
  gap: 0.75rem;
}

.result-item {
  margin: 0;
}

.result-card {
  width: 100%;
  background: #ffffff;
  border: 1px solid #e6ebf2;
  border-radius: 16px;
  text-align: left;
  padding: 1.05rem 1rem;
}

.result-card:hover {
  border-color: #d8e1f0;
}

.result-card.active {
  background: #f6f8fc;
  border-color: #d7e0ec;
}

.result-main {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.8rem;
  align-items: start;
}

.result-content {
  min-width: 0;
}

.result-title {
  margin: 0;
  font-size: 1.1rem;
  line-height: 1.25;
  color: #0f172a;
}

.meta-row {
  margin-top: 0.5rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  color: #9aa7bb;
  font-size: 0.84rem;
}

.meta-row span {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
}
</style>
