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

      <div class="tag-row">
        <span class="tag">{{ previewType }}</span>
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
</style>
