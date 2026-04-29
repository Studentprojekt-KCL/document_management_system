<script setup>
/**
 * SearchPreviewDrawer Component
 * Displays a sliding drawer with detailed information about a selected file from the search results.
 *
 * @component
 * @example usage in SearchView.vue:
 * <SearchPreviewDrawer :open="isPreviewOpen" :selected-file="selectedFile" :selected-match="selectedMatch" :matches="matches" @close="closePreview" />
 */

import { ref, computed, watch } from 'vue'
import { X, StarsIcon, CalendarDays, HardDrive, FileType2, ExternalLink, Pencil, CheckCircle, AlertCircle } from 'lucide-vue-next'

import { useSearchMetadata } from '@/composables/useSearchMetadata'
import { useAISummary } from '@/composables/aiSummary'
import { hasRole } from '@/utils/auth'
import ClassificationEditor from '@/components/ClassificationEditor.vue'
import { saveClassification } from '@/utils/api'
import { useAIRerank } from '@/composables/aiRerank'

/* Props */
const props = defineProps({
  open: { type: Boolean, default: false },
  selectedFile: { type: String, default: '' },
  selectedMatch: { type: Object, default: null },
  matches: { type: Array, default: () => [] }
})

const emit = defineEmits(['close', 'update-security'])

/* Metadata */
const {
  previewTitle,
  previewFileDescription,
  sourceSystem,
  previewCreatedAt,
  previewSize,
  previewLink,
  previewSecurityClass,
  uniquePointer
} = useSearchMetadata(props)

/* AI */
const { aiSummaryHtml, summaryError, isGeneratingSummary, generateAISummary } = useAISummary(props)

/* State */
const isEditingClassification = ref(false)
const classificationEditorRef = ref(null)
const localSecurityLevel = ref('')

/* Sync from metadata */
watch(
  () => previewSecurityClass.value,
  (val) => {
    localSecurityLevel.value = val || ''
  },
  { immediate: true }
)

/* Computed */
const currentSecurityLevel = computed(() => localSecurityLevel.value)

/* Permissions */
const canEdit = computed(() => hasRole('admin'))

/* notification */
const notification = ref({ visible: false, success: true, message: '' })
let notificationTimer = null

const showNotification = (success, message) => {
  if (notificationTimer) clearTimeout(notificationTimer)

  notification.value = { visible: true, success, message }

  notificationTimer = setTimeout(() => {
    notification.value.visible = false
  }, 4000)
}

/* Save classification */
const handleClassificationSave = async (level) => {
  try {
    await saveClassification(uniquePointer.value, level)
    emit('update-security', {
      uniquePointer: uniquePointer.value,
      level
    })

    localSecurityLevel.value = level

    showNotification(true, 'Security classification updated successfully.')
    isEditingClassification.value = false
  } catch (err) {
    showNotification(false, `Update failed: ${err.message}`)
  } finally {
    classificationEditorRef.value?.resetSaving()
  }
}

/* Reset UI */
watch(
  () => [props.selectedFile, props.open],
  () => {
    isEditingClassification.value = false
    notification.value.visible = false
  }
)
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
      <!-- notification -->
      <Transition name="notification-fade">
        <div
          v-if="notification.visible"
          :class="['notification', notification.success ? 'notification-success' : 'notification-error']"
        >
          <CheckCircle v-if="notification.success" :size="16" />
          <AlertCircle v-else :size="16" />
          <span>{{ notification.message }}</span>
        </div>
      </Transition>

      <h3 class="preview-title">{{ previewTitle }}</h3>

      <div class="tag-row">
        <span class="tag">{{ previewFileDescription }}</span>
      </div>

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
            <div class="security-class-row">
              <p>{{ currentSecurityLevel || 'Unknown' }}</p>
              <button v-if="canEdit" class="edit-btn" @click="isEditingClassification = true">
                <Pencil :size="14" />
                Edit
              </button>
            </div>
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
      <!-- MODAL -->
      <ClassificationEditor
        ref="classificationEditorRef"
        :visible="isEditingClassification"
        :current-level="currentSecurityLevel"
        @save="handleClassificationSave"
        @cancel="isEditingClassification = false"
      />

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
              <ExternalLink :size="13" />
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
  gap: 0.35rem;
  margin: 0;
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

.edit-btn {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.35rem 0.7rem;
  border: 1px solid #d8dee7;
  border-radius: 8px;
  background: #f8fafc;
  color: #475569;
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
  margin-left: auto;
}

.security-class-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.edit-btn:hover {
  border-color: #7c3aed;
  color: #7c3aed;
  background: #faf5ff;
}

.notification {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.65rem 0.9rem;
  border-radius: 10px;
  font-size: 0.85rem;
  font-weight: 600;
  margin-bottom: 0.75rem;
}

.notification-success {
  background: #ecfdf5;
  color: #065f46;
  border: 1px solid #a7f3d0;
}
.notification-error {
  background: #fef2f2;
  color: #991b1b;
  border: 1px solid #fecaca;
}

.notification-fade-enter-active,
.notification-fade-leave-active {
  transition:
    opacity 0.3s ease,
    transform 0.3s ease;
}

.notification-fade-enter-from,
.notification-fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
