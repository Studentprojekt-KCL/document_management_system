<script setup>
/**
 * SearchPreviewDrawer Component
 * Displays a sliding drawer with detailed information about a selected file from the search results.
 *
 * @component
 * @example usage in SearchView.vue:
 * <SearchPreviewDrawer :open="isPreviewOpen" :selected-file="selectedFile" :selected-match="selectedMatch" :matches="matches" @close="closePreview" />
 */

import { X, StarsIcon, CalendarDays, HardDrive, FileType2, ExternalLink } from 'lucide-vue-next'
import { useSearchMetadata } from '@/composables/useSearchMetadata'
import { useAISummary } from '@/composables/aiSummary'
import { useAIRerank } from '@/composables/aiRerank'

/* Props received from parent component (SearchView) */
const props = defineProps({
  open: { type: Boolean, default: false },
  selectedFile: { type: String, default: '' },
  selectedMatch: { type: Object, default: null },
  matches: { type: Array, default: () => [] }
})

/* Emit event to parent component to signal closing the preview drawer */
const emit = defineEmits(['close'])

/* Use custom composable to extract metadata for the selected file */
const { previewTitle, sourceSystem, previewFileDescription, previewCreatedAt, previewSize, previewLink, previewSecurityClass } =
  useSearchMetadata(props)

/* AI summary composable */
const { aiSummaryHtml, summaryError, isGeneratingSummary, generateAISummary } = useAISummary(props)

/* AI rerank composable */
const { aiRerankResultsComputed, isReranking, rerankError, generateAIRerank } = useAIRerank(props)
</script>

<template>
  <div v-if="open" class="preview-backdrop" @click="emit('close')" />

  <!-- Drawer container with dynamic classes based on open state -->
  <aside class="preview-drawer" :class="{ open }">
    <!-- Header section with title and close button -->
    <div class="preview-header">
      <p class="panel-kicker">DOCUMENT INTELLIGENCE</p>
      <button class="close-btn" type="button" @click="emit('close')" aria-label="Close preview" title="Close preview">
        <X :size="18" />
      </button>
    </div>

    <!-- Main content area of the preview drawer -->
    <div class="preview-body">
      <h3 class="preview-title">{{ previewTitle }}</h3>

      <!-- Technical Metadata section -->
      <section class="panel-section">
        <p class="section-title">TECHNICAL METADATA</p>
        <div class="meta-grid">
          <div class="meta-cell">
            <span>Created</span>
            <p><CalendarDays :size="13" /> {{ previewCreatedAt }}</p>
          </div>
          <div class="meta-cell">
            <span>File Size</span>
            <p><HardDrive :size="13" /> {{ previewSize }} B</p>
          </div>
          <div class="meta-cell">
            <span>Format</span>
            <p><FileType2 :size="13" /> {{ previewFileDescription }}</p>
          </div>
          <div class="meta-cell">
            <span>Security Class</span>
            <p>{{ previewSecurityClass || 'Unknown' }}</p>
          </div>
        </div>
      </section>

      <!-- AI Summary section -->
      <section class="panel-section">
        <p class="section-title">AI SUMMARY</p>
        <div v-if="aiSummaryHtml">
          <div class="meta-cell meta-cell-summary">
            <div class="summary-markdown" v-html="aiSummaryHtml"></div>
          </div>
          <button
            class="meta-cell meta-cell-summary summary-regenerate-button"
            type="button"
            :disabled="isGeneratingSummary"
            @click="generateAISummary"
          >
            <p>
              <StarsIcon :size="13" />
              {{ isGeneratingSummary ? 'Generating summary...' : 'Regenerate Summary' }}
            </p>
          </button>
        </div>
        <button
          v-else
          class="meta-cell meta-cell-summary summary-cell-button"
          type="button"
          :disabled="isGeneratingSummary"
          @click="generateAISummary"
        >
          <p>
            <StarsIcon :size="13" />
            {{ isGeneratingSummary ? 'Generating summary...' : 'Generate AI Summary' }}
          </p>
          <p v-if="summaryError" class="error">Error generating summary: {{ summaryError }}</p>
        </button>
      </section>

      <!-- Rerank (similarity) section -->
      <section class="panel-section">
        <p class="section-title">SIMILARITY</p>
        <div v-if="aiRerankResultsComputed.length">
          <ul>
            <li v-for="result in aiRerankResultsComputed" :key="result.pointer" class="meta-cell meta-cell-rerank">
              <p>{{ result.rank }}. {{ result.name }}<br />Score: {{ result.scorePercent }}</p>
            </li>
          </ul>
          <button
            class="meta-cell meta-cell-summary summary-regenerate-button"
            type="button"
            :disabled="isReranking"
            @click="generateAIRerank"
          >
            <p>
              <StarsIcon :size="13" />
              {{ isReranking ? 'Finding matches...' : 'Regenerate Similar Files' }}
            </p>
            <p v-if="rerankError" class="error">Error finding matches: {{ rerankError }}</p>
          </button>
          <!-- Possibility to merge files button -->
          <button
            class="meta-cell meta-cell-summary summary-regenerate-button"
            type="button"
            @click="$router.push({ name: 'MergeFiles' })"
          >
            <p>
              <StarsIcon :size="13" />
              Merge Files
            </p>
          </button>
        </div>
        <button
          v-else
          class="meta-cell meta-cell-summary summary-cell-button"
          type="button"
          :disabled="isReranking"
          @click="generateAIRerank(previewTitle)"
        >
          <p>
            <StarsIcon :size="13" />
            {{ isReranking ? 'Finding matches...' : 'Find Similar Files' }}
          </p>
          <p v-if="rerankError" class="error">Error finding matches: {{ rerankError }}</p>
        </button>
      </section>
    </div>

    <div class="preview-footer">
      <a v-if="previewLink" class="open-file-btn" :href="previewLink" target="_blank" rel="noopener noreferrer">
        <ExternalLink :size="14" />
        Open file in {{ sourceSystem }}
      </a>
      <button v-else class="open-file-btn" type="button" disabled>
        <ExternalLink :size="14" />
        No file link available
      </button>
    </div>
  </aside>
</template>

<style scoped>
.preview-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.22);
  z-index: 40;
}

.preview-drawer {
  position: fixed;
  top: 0;
  right: 0;
  height: 100vh;
  width: min(700px, 100vw);
  background: #ffffff;
  transform: translateX(100%);
  transition: transform 0.25s ease;
  z-index: 50;
  display: flex;
  flex-direction: column;
}

.preview-drawer.open {
  transform: translateX(0);
}

.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1rem 0.9rem;
  border-bottom: 1px solid #eef2f7;
}

.panel-kicker {
  margin: 0;
  letter-spacing: 0.1em;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}

.close-btn {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.preview-body {
  padding: 1rem;
  overflow: auto;
  flex: 1;
}

.preview-title {
  margin-top: 2rem;
  text-align: center;
  line-height: 1.15;
  word-break: break-word;
  overflow-wrap: break-word;
  white-space: normal;
}

.tag-row {
  margin-top: 0.7rem;
  display: flex;
  justify-content: center;
}

.tag {
  border: 1px solid #e2e8f0;
  border-radius: 999px;
  padding: 0.2rem 0.55rem;
  text-transform: uppercase;
  font-size: 0.7rem;
  font-weight: 700;
}

.panel-section {
  margin-top: 4rem;
}

.section-title {
  font-weight: 700;
  display: inline-flex;
  align-items: center;
}

.meta-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.5rem;
}

.meta-cell {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 0.55rem;
  background: #fbfdff;
}

.meta-cell span {
  display: block;
  color: #94a3b8;
  font-size: 0.66rem;
  font-weight: 700;
}

.meta-cell p {
  margin: 0;
  display: inline-flex;
  align-items: center;
  gap: 0.32rem;
  font-size: 0.82rem;
  font-weight: 600;
}

.meta-cell-summary {
  grid-column: 1 / -1;
  overflow: hidden;
}

.meta-cell-rerank {
  grid-column: 1 / -1;
  overflow: hidden;
  margin-bottom: 0.5rem;
}

.meta-cell-rerank p {
  display: block;
  overflow-wrap: break-word;
  word-break: break-all;
  white-space: normal;
}

.summary-markdown {
  padding: 1rem 1.5rem;
}

.summary-cell-button {
  width: 100%;
  text-align: left;
  font: inherit;
  appearance: none;
  cursor: pointer;
}

.summary-cell-button:hover:not(:disabled) {
  border-color: #94a3b8;
  background: #f1f5f9;
}

.summary-cell-button:disabled {
  opacity: 0.8;
  cursor: wait;
}

.summary-regenerate-button {
  margin-top: 0.75rem;
  cursor: pointer;
}

.summary-regenerate-button + .summary-regenerate-button {
  margin-left: 1rem;
}

.summary-regenerate-button:hover:not(:disabled) {
  border-color: #94a3b8;
  background: #f1f5f9;
}

.summary-regenerate-button:disabled {
  opacity: 0.8;
  cursor: wait;
}

.preview-footer {
  border-top: 1px solid #eef2f7;
  padding: 0.85rem 1rem 1rem;
}

.open-file-btn {
  width: 100%;
  border: 1px solid #cbd5e1;
  background: #f8fafc;
  color: #334155;
  border-radius: 10px;
  padding: 0.75rem;
  font-weight: 600;
  font-size: 0.82rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
}

.open-file-btn:hover:not(:disabled) {
  border-color: #94a3b8;
  background: #f1f5f9;
}

.open-file-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
</style>
