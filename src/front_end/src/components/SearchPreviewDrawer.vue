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
import {
  X,
  StarsIcon,
  CalendarDays,
  HardDrive,
  FileType2,
  ExternalLink,
  ShieldCheck,
  Pencil,
  CheckCircle,
  AlertCircle
} from 'lucide-vue-next'
import { useSearchMetadata } from '@/composables/useSearchMetadata'
import { useAISummary } from '@/composables/aiSummary'
import { hasRole } from '@/utils/auth'
import ClassificationEditor from '@/components/ClassificationEditor.vue'

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
const { previewTitle, previewType, sourceSystem, previewCreatedAt, previewSize, previewLink, previewSecurityClass, uniquePointer } =
  useSearchMetadata(props)

/* AI summary composable */
const { aiSummaryHtml, summaryError, isGeneratingSummary, generateAISummary } = useAISummary(props)

const API_BASE_URL = window.__ENV__.API_BASE_URL.replace(/\/$/, '')

const isEditingClassification = ref(false)
const classificationEditorRef = ref(null)

/* Local override for optimistic updates */
const localSecurityLevel = ref('')

/* Sync initial value */
watch(
  () => previewSecurityClass.value,
  (val) => {
    localSecurityLevel.value = val || ''
  },
  { immediate: true }
)

/* Final value used in UI */
const currentSecurityLevel = computed(() => localSecurityLevel.value)

/* Permissions */
const canEdit = computed(() => hasRole('admin'))

/* Toast */
const toast = ref({ visible: false, success: true, message: '' })
let toastTimer = null

const showToast = (success, message) => {
  if (toastTimer) clearTimeout(toastTimer)
  toast.value = { visible: true, success, message }
  toastTimer = setTimeout(() => {
    toast.value.visible = false
  }, 4000)
}

/* Save classification */
const handleClassificationSave = async (level) => {
  try {
    const res = await fetch(`${API_BASE_URL}/search_engine/classification`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${sessionStorage.getItem('access_token')} ` },
      body: JSON.stringify({
        unique_pointer: uniquePointer.value,
        classification: level
      })
    })

    if (!res.ok) throw new Error(`Server responded with ${res.status}`)

    /* Optimistic UI update */
    localSecurityLevel.value = level

    showToast(true, 'Security classification updated successfully.')
    isEditingClassification.value = false
  } catch (err) {
    showToast(false, `Update failed: ${err.message}`)
  } finally {
    classificationEditorRef.value?.resetSaving()
  }
}

/* Reset UI on change */
watch(
  () => [props.selectedFile, props.open],
  () => {
    isEditingClassification.value = false
    toast.value.visible = false
  }
)
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
      <!-- Toast -->
      <Transition name="toast-fade">
        <div v-if="toast.visible" :class="['toast', toast.success ? 'toast-success' : 'toast-error']">
          <CheckCircle v-if="toast.success" :size="16" />
          <AlertCircle v-else :size="16" />
          <span>{{ toast.message }}</span>
        </div>
      </Transition>

      <h3 class="preview-title">{{ previewTitle }}</h3>

      <div class="tag-row">
        <span class="tag">{{ previewType }}</span>
      </div>

      <!-- SECURITY CLASSIFICATION -->
      <section class="panel-section">
        <div class="section-header">
          <p class="section-title"><ShieldCheck :size="15" /> SECURITY CLASSIFICATION</p>

          <button v-if="canEdit" class="edit-btn" @click="isEditingClassification = true">
            <Pencil :size="14" />
            Edit
          </button>
        </div>

        <div class="classification-display">
          <span :class="['classification-badge', `badge-${(currentSecurityLevel || 'none').toLowerCase()}`]">
            {{ currentSecurityLevel || 'Not classified' }}
          </span>
        </div>
      </section>

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
            <p><HardDrive :size="13" /> {{ previewSize }}</p>
          </div>
          <div class="meta-cell">
            <span>Format</span>
            <p><FileType2 :size="13" /> {{ previewType }}</p>
          </div>
          <div class="meta-cell">
            <span>Security Class</span>
            <p>{{ currentSecurityLevel || 'Unknown' }}</p>
          </div>
        </div>
      </section>

      <!-- AI Summary section -->
      <section class="panel-section">
        <p class="section-title">AI SUMMARY</p>
        <div v-if="aiSummaryHtml" class="meta-cell meta-cell-summary">
          <div class="summary-markdown" v-html="aiSummaryHtml"></div>
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

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.6rem;
}

.edit-btn {
  display: inline-flex;
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
}

.edit-btn:hover {
  border-color: #7c3aed;
  color: #7c3aed;
  background: #faf5ff;
}

.classification-display {
  margin-top: 0.25rem;
}

.classification-badge {
  display: inline-block;
  padding: 0.3rem 0.75rem;
  border-radius: 999px;
  font-size: 0.82rem;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.badge-public {
  background: #ecfdf5;
  color: #065f46;
  border: 1px solid #a7f3d0;
}
.badge-internal {
  background: #eff6ff;
  color: #1e40af;
  border: 1px solid #bfdbfe;
}
.badge-sensitive {
  background: #fffbeb;
  color: #92400e;
  border: 1px solid #fde68a;
}
.badge-confidential {
  background: #fef2f2;
  color: #991b1b;
  border: 1px solid #fecaca;
}
.badge-none {
  background: #f3f4f6;
  color: #6b7280;
  border: 1px solid #e5e7eb;
}

.toast {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.65rem 0.9rem;
  border-radius: 10px;
  font-size: 0.85rem;
  font-weight: 600;
  margin-bottom: 0.75rem;
}

.toast-success {
  background: #ecfdf5;
  color: #065f46;
  border: 1px solid #a7f3d0;
}
.toast-error {
  background: #fef2f2;
  color: #991b1b;
  border: 1px solid #fecaca;
}

.toast-fade-enter-active,
.toast-fade-leave-active {
  transition:
    opacity 0.3s ease,
    transform 0.3s ease;
}

.toast-fade-enter-from,
.toast-fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
