<script setup>
/**
 * MergeFilesView.vue - Possibility to merge/summarize files received from the ranker.
 * Metadata displaying and so is fetched from SearchMatches.vue
 * Similar files and the scores are fetched from useAIRerank :)
 */
import { computed, ref } from 'vue'
import { useAIRerank } from '@/composables/aiRerank'
import { useAISummary } from '@/composables/aiSummary'
import SearchMatches from '@/components/SearchMatches.vue'

const { aiRerankResults, rerankFilename, rerankPointer } = useAIRerank()
const { aiSummaryHtml, summaryError, isGeneratingSummary, generateAISummary } = useAISummary()

const selectedPointers = ref([rerankPointer.value]) // Start with the reranked file selected

const selectedCount = computed(() => selectedPointers.value.length)
</script>

<template>
  <div class="merge-files-view">
    <h1>Merge/Summarize reranked files</h1>

    <div v-if="aiRerankResults.length">
      <h3>Similar to: {{ rerankFilename }}</h3>
      <p class="text-secondary">
        Click on one or more files to select them to merge and summarize them together with the reranked file.
      </p>

      <SearchMatches :matches="aiRerankResults" v-model:selected-pointers="selectedPointers" badge-mode="score" selectable />

      <div class="merge-actions">
        <p>{{ selectedCount }} file{{ selectedCount === 1 ? '' : 's' }} selected</p>

        <div>
          <button
            type="button"
            :disabled="isGeneratingSummary || selectedCount === 0"
            @click="generateAISummary(selectedPointers, rerankPointer.value)"
          >
            {{ isGeneratingSummary ? 'Generating summary...' : 'Merge & Summarize' }}
          </button>
          <p v-if="summaryError" class="error">Error generating summary: {{ summaryError }}</p>
        </div>
      </div>
      <div v-if="aiSummaryHtml" class="summary-result">
        <h2>Summary Result</h2>
        <div class="summary-markdown" v-html="aiSummaryHtml"></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.merge-files-view {
  padding: 2rem;
}

.merge-actions {
  margin-top: 1rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.merge-actions p {
  margin: 0;
  color: #64748b;
  font-weight: 600;
}

.merge-actions button {
  border: 1px solid #d7e0ec;
  background: #f6f8fc;
  color: #0f172a;
  padding: 0.55rem 0.9rem;
  border-radius: 10px;
  font-weight: 700;
  cursor: pointer;
}

.merge-actions button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}
</style>
