<script setup>
/**
 * SearchPreviewDrawer Component
 * Displays a sliding drawer with detailed information about a selected file from the search results.
 *
 * @component
 * @example usage in SearchView.vue:
 * <SearchPreviewDrawer :open="isPreviewOpen" :selected-file="selectedFile" :selected-match="selectedMatch" :matches="matches" @close="closePreview" />
 */

import { computed, ref, watch } from 'vue'
import {
  X,
  StarsIcon,
  CalendarDays,
  HardDrive,
  FileType2,
  ExternalLink,
  Pencil,
  Save,
  XCircle,
  CheckCircle,
  AlertCircle
} from 'lucide-vue-next'
import { useSearchMetadata } from '@/composables/useSearchMetadata'
import { hasRole } from '@/utils/auth'

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
const { previewTitle, previewType, previewCreatedAt, previewSize, previewLink } = useSearchMetadata(props)

/* Base URL for API requests */
const API_BASE_URL = import.meta.env.API_BASE_URL?.replace(/\/$/, '') ?? ''

/* Edit mode state */
const isEditing = ref(false)
const isSaving = ref(false)

/* Editable field values (populated when entering edit mode) */
const editFields = ref({
  title: '',
  type: '',
  created: '',
  size: ''
})

/* Status toast for save feedback */
const toast = ref({ visible: false, success: true, message: '' })
let toastTimer = null

/* Check if the current user is allowed to edit metadata */
const canEdit = computed(() => hasRole('admin'))

/* Enter edit mode: snapshot current values into the form */
const startEditing = () => {
  editFields.value = {
    title: previewTitle.value || '',
    type: previewType.value || '',
    created: previewCreatedAt.value || '',
    size: previewSize.value || ''
  }
  isEditing.value = true
}

/* Cancel editing: reset form and exit edit mode */
const cancelEditing = () => {
  isEditing.value = false
  editFields.value = { title: '', type: '', created: '', size: '' }
}

/* Save metadata changes */
const saveMetadata = async () => {
  isSaving.value = true

  try {
    // TODO: Replace with real endpoint when backend supports metadata updates.
    // The endpoint should accept the document identifier and updated fields.
    const res = await fetch(`${API_BASE_URL}/metadata`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        filename: props.selectedFile,
        metadata: { ...editFields.value }
      })
    })

    if (!res.ok) {
      throw new Error(`Server responded with ${res.status}`)
    }

    showToast(true, 'Metadata updated successfully.')
    isEditing.value = false
  } catch (err) {
    showToast(false, `Update failed: ${err.message}`)
  } finally {
    isSaving.value = false
  }
}

/* Toast helper */
const showToast = (success, message) => {
  if (toastTimer) clearTimeout(toastTimer)
  toast.value = { visible: true, success, message }
  toastTimer = setTimeout(() => {
    toast.value.visible = false
  }, 4000)
}

/* Reset edit state when a different document is selected or drawer closes */
watch(
  () => [props.selectedFile, props.open],
  () => {
    cancelEditing()
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
      <Transition name="toast-fade">
        <div v-if="toast.visible" :class="['toast', toast.success ? 'toast-success' : 'toast-error']">
          <CheckCircle v-if="toast.success" :size="16" />
          <AlertCircle v-else :size="16" />
          <span>{{ toast.message }}</span>
        </div>
      </Transition>

      <template v-if="isEditing">
        <input v-model="editFields.title" class="edit-input edit-title" type="text" placeholder="Document title" />
      </template>

      <h3 class="preview-title">{{ previewTitle }}</h3>

      <div class="tag-row">
        <span class="tag">{{ isEditing ? editFields.type || previewType : previewType }}</span>
      </div>

      <!-- AI Summary section -->
      <section class="panel-section">
        <!-- QUICK FIX: This should be a button, where we ask for the ai summary for chosen file -->
        <p class="section-title">AI SUMMARY</p>
        <div class="generate-summary">
          <p class="summary-card"><StarsIcon :size="13" />Generate AI summary</p>
        </div>
      </section>

      <!-- Technical Metadata section -->
      <section class="panel-section">
        <div class="section-header">
          <p class="section-title">TECHNICAL METADATA</p>

          <!-- Edit button – only visible to authorized users when not already editing -->
          <button v-if="canEdit && !isEditing" class="edit-btn" type="button" title="Edit metadata" @click="startEditing">
            <Pencil :size="14" />
            Edit
          </button>
        </div>

        <!-- ── Read-only metadata grid ── -->
        <div v-if="!isEditing" class="meta-grid">
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
        </div>

        <!-- ── Editable metadata form ── -->
        <div v-else class="meta-edit-form">
          <div class="edit-field">
            <label class="edit-label" for="edit-created">Created</label>
            <input id="edit-created" v-model="editFields.created" class="edit-input" type="date" />
          </div>
          <div class="edit-field">
            <label class="edit-label" for="edit-size">File Size</label>
            <input id="edit-size" v-model="editFields.size" class="edit-input" type="text" placeholder="e.g. 2.4 MB" />
          </div>
          <div class="edit-field">
            <label class="edit-label" for="edit-type">Format</label>
            <input id="edit-type" v-model="editFields.type" class="edit-input" type="text" placeholder="e.g. PDF Document" />
          </div>

          <!-- Save / Cancel actions -->
          <div class="edit-actions">
            <button class="action-btn cancel-btn" type="button" :disabled="isSaving" @click="cancelEditing">
              <XCircle :size="15" />
              Cancel
            </button>
            <button class="action-btn save-btn" type="button" :disabled="isSaving" @click="saveMetadata">
              <Save :size="15" />
              {{ isSaving ? 'Saving…' : 'Save' }}
            </button>
          </div>
        </div>
      </section>
    </div>

    <div class="preview-footer">
      <a v-if="previewLink" class="open-file-btn" :href="previewLink" target="_blank" rel="noopener noreferrer">
        <ExternalLink :size="14" />
        Open file
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
  width: min(520px, 92vw);
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
  position: relative;
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
  margin: 0;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.6rem;
}

/* QUICK FIX: This should be a button, but we can iterate later */
.summary-card {
  border: 1px solid #e2e8f0;
  background: #f8faff;
  border-radius: 12px;
  padding: 0.75rem;
  color: #334155;
  margin: 0;
  display: inline-flex;
  align-items: center;
  gap: 0.32rem;
  font-size: 0.82rem;
  font-weight: 600;
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

.meta-edit-form {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.edit-field {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.edit-label {
  font-size: 0.7rem;
  font-weight: 700;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.edit-input {
  border: 1px solid #d8dee7;
  border-radius: 8px;
  padding: 0.5rem 0.65rem;
  font-size: 0.88rem;
  color: #1e293b;
  background: #ffffff;
  outline: none;
  font-family: inherit;
}

.edit-input:focus {
  border-color: #7c3aed;
  box-shadow: 0 0 0 2px rgba(124, 58, 237, 0.12);
}

.edit-title {
  margin-top: 2rem;
  text-align: center;
  font-size: 1.25rem;
  font-weight: 600;
}

.edit-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.action-btn {
  flex: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
  padding: 0.6rem 0.75rem;
  border-radius: 8px;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
}

.cancel-btn {
  border: 1px solid #d8dee7;
  background: #f8fafc;
  color: #475569;
}

.cancel-btn:hover:not(:disabled) {
  background: #f1f5f9;
  border-color: #94a3b8;
}

.save-btn {
  border: none;
  background: linear-gradient(135deg, #5b21b6 0%, #7c3aed 100%);
  color: #ffffff;
}

.save-btn:hover:not(:disabled) {
  opacity: 0.92;
}

.action-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
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
