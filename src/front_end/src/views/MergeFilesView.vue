<script setup>
/**
 * MergeFilesView.vue - Possibility to merge/summarize files received from the ranker.
 * Metadata displaying and so is fetched from SearchMatches.vue
 * Similar files and the scores are fetched from useAIRerank :)
 */
import { computed, ref } from 'vue'
import { useAIRerank } from '@/composables/aiRerank'
import { useAISummary } from '@/composables/aiSummary'
import { useMdToPdf } from '@/composables/mdToPdf'
import SearchMatches from '@/components/SearchMatches.vue'
import { Download } from 'lucide-vue-next'

const { aiRerankResults, rerankFilename, rerankPointer } = useAIRerank()
const { aiSummaryHtml, summaryError, isGeneratingSummary, generateAISummary, resetSummary } = useAISummary()
const { pdfError, mergedHtmlRaw, isGeneratingPDF, generatePDF, pdfUrl, resetMerged } = useMdToPdf()

const selectedPointer = ref([rerankPointer.value]) // Start with the reranked file selected

const selectedCount = computed(() => selectedPointer.value.length)

const changedSelctions = computed(() => [...selectedPointer.value].sort().join('|'))
const lastPdfSelction = ref('')
const lastSummarySelection = ref('')

const currentPdfSelection = computed(() => Boolean(pdfUrl.value) && lastPdfSelction.value === changedSelctions.value)
const currentSummarySelection = computed(
  () => Boolean(aiSummaryHtml.value) && lastSummarySelection.value === changedSelctions.value
)

const handleGeneratePDF = async () => {
  lastPdfSelction.value = changedSelctions.value
  resetMerged()
  await generatePDF(selectedPointer.value, rerankPointer.value)
}

const handleGenerateSummary = async () => {
  lastSummarySelection.value = changedSelctions.value
  resetSummary()
  await generateAISummary(selectedPointer.value, rerankPointer.value)
}
</script>

<template>
  <div class="merge-files-view">
    <h1>Merge/Summarize reranked files</h1>

    <div v-if="aiRerankResults.length">
      <h3>Files similar to: {{ rerankFilename }}</h3>
      <p>
        Click on one or more files to select them to merge and summarize them together with the reranked file. The merging will also
        generate a PDF you can download. You can choose to merge/summarize as many files as you want, but keep in mind that the
        result may take more time.
      </p>
      <p v-if="selectedCount === 1">Currently, only the reranked file is selected</p>

      <SearchMatches :matches="aiRerankResults" v-model:selected-pointers="selectedPointer" badge-mode="score" selectable />

      <div class="actions">
        <p>{{ selectedCount }} file{{ selectedCount === 1 ? '' : 's' }} selected</p>
        <div class="pdf-actions">
          <button
            v-if="!currentPdfSelection"
            type="button"
            :disabled="isGeneratingPDF || selectedCount === 0"
            @click="handleGeneratePDF"
          >
            {{ isGeneratingPDF ? 'Generating PDF...' : 'Merge + Generate PDF' }}
          </button>

          <div v-else class="download-section">
            <a :href="pdfUrl" target="_blank" class="preview-button"> Preview merged PDF </a>

            <a :href="pdfUrl" download="mergedFiles.pdf" class="download-button"> <Download /> Download merged PDF </a>
          </div>

          <p v-if="pdfError" class="error">Error generating PDF: {{ pdfError }}</p>
        </div>

        <div class="summary-actions">
          <button v-if="!currentSummarySelection" type="button" :disabled="isGeneratingSummary" @click="handleGenerateSummary">
            {{ isGeneratingSummary ? 'Generating summary...' : 'Summarize' }}
          </button>

          <p v-if="summaryError" class="error">Error generating summary: {{ summaryError }}</p>
        </div>
      </div>
      <div v-if="aiSummaryHtml" class="summary-result">
        <h2>Summary Result</h2>
        <div class="summary-markdown" v-html="aiSummaryHtml"></div>
      </div>
      <div v-if="mergedHtmlRaw" class="merged-html-result">
        <h2>Merged Result</h2>
        <div class="summary-markdown" v-html="mergedHtmlRaw"></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.merge-files-view {
  padding: 2rem;
}

.actions {
  margin-top: 1rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.actions p {
  margin: 0;
  color: #64748b;
  font-weight: 600;
}

.actions button,
.preview-button,
.download-button {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  border: 1px solid #d7e0ec;
  background: #f6f8fc;
  color: #0f172a;
  padding: 0.55rem 0.9rem;
  border-radius: 10px;
  font-weight: 700;
  cursor: pointer;
  text-decoration: none;
}

.actions button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.pdf-actions {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.download-section {
  display: flex;
  gap: 0.75rem;
  align-items: center;
}

.preview-button:hover,
.download-button:hover {
  background: #f8fafc;
}
</style>
