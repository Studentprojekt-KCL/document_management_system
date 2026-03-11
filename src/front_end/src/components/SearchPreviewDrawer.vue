<script setup>
import { X, StarsIcon, CalendarDays, HardDrive, FileType2 } from 'lucide-vue-next'
import { useSearchMetadata } from '@/composables/useSearchMetadata'

const props = defineProps({
  open: { type: Boolean, default: false },
  selectedFile: { type: String, default: '' },
  selectedMatch: { type: Object, default: null },
  matches: { type: Array, default: () => [] }
})

const emit = defineEmits(['close'])
const { previewTitle, previewType, previewCreatedAt, previewSize } = useSearchMetadata(props)
</script>

<template>
  <div v-if="open" class="preview-backdrop" @click="emit('close')" />
  <aside class="preview-drawer" :class="{ open }">
    <div class="preview-header">
      <p class="panel-kicker">DOCUMENT INTELLIGENCE</p>
      <button class="close-btn" type="button" @click="emit('close')" aria-label="Close preview" title="Close preview">
        <X :size="18" />
      </button>
    </div>

    <div class="preview-body">
      <h3 class="preview-title">{{ previewTitle }}</h3>

      <div class="tag-row">
        <span class="tag">{{ previewType }}</span>
      </div>

      <section class="panel-section">
        <!-- QUICK FIX: This should be a button, where we ask for the ai summary for chosen file -->
        <p class="section-title">AI SUMMARY</p>
        <div class="generate-summary">
          <p class="summary-card"><StarsIcon :size="13" />Generate AI summary</p>
        </div>
      </section>

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
</style>
