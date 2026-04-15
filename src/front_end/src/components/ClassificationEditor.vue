<script setup>
/**
 * ClassificationEditor Component
 * A modal overlay for editing a document's security classification.
 * Intended to be used inside SearchPreviewDrawer.
 *
 * @component
 * @example usage:
 * <ClassificationEditor
 *   :visible="isEditingClassification"<script setup>
/**
 * ClassificationEditor Component
 * A modal overlay for editing a document's security classification.
 * Intended to be used inside SearchPreviewDrawer.
 *
 * @component
 * @example usage:
 * <ClassificationEditor
 *   :visible="isEditingClassification"
 *   :current-level="currentSecurityLevel"
 *   @save="handleClassificationSave"
 *   @cancel="isEditingClassification = false"
 * />
 */

import { ref, watch } from 'vue'
import { ShieldCheck, Save, XCircle } from 'lucide-vue-next'

const props = defineProps({
  visible: { type: Boolean, default: false },
  currentLevel: { type: String, default: '' }
})

const emit = defineEmits(['save', 'cancel'])

/* Security classification levels */
const SECURITY_LEVELS = ['Public', 'Internal', 'Sensitive', 'Confidential']

const selectedLevel = ref('')
const isSaving = ref(false)

/* Sync selected level when modal opens */
watch(
  () => props.visible,
  (open) => {
    if (open) {
      selectedLevel.value = props.currentLevel || ''
    }
  }
)

/* Handle save — emit the chosen level to the parent */
const handleSave = async () => {
  if (!selectedLevel.value) return
  isSaving.value = true

  emit('save', selectedLevel.value)

  setTimeout(() => {
    isSaving.value = false
  }, 5000)
}

/* Expose resetSaving so parent can call it after the API responds */
const resetSaving = () => {
  isSaving.value = false
}

defineExpose({ resetSaving })
</script>

<template>
  <Transition name="modal-fade">
    <div v-if="visible" class="classification-modal-backdrop" @click.self="emit('cancel')">
      <div class="classification-modal">
        <div class="modal-header">
          <h4 class="modal-title"><ShieldCheck :size="18" /> Edit Security Classification</h4>
        </div>

        <div class="modal-body">
          <p class="modal-description">Select the appropriate security level for this document.</p>

          <div class="level-options">
            <button
              v-for="level in SECURITY_LEVELS"
              :key="level"
              :class="['level-option', { selected: selectedLevel === level }, `option-${level.toLowerCase()}`]"
              type="button"
              @click="selectedLevel = level"
            >
              <span class="level-radio">
                <span v-if="selectedLevel === level" class="level-radio-dot" />
              </span>
              <span class="level-label">{{ level }}</span>
            </button>
          </div>
        </div>

        <div class="modal-actions">
          <button class="action-btn cancel-btn" type="button" :disabled="isSaving" @click="emit('cancel')">
            <XCircle :size="15" />
            Cancel
          </button>
          <button class="action-btn save-btn" type="button" :disabled="isSaving || !selectedLevel" @click="handleSave">
            <Save :size="15" />
            {{ isSaving ? 'Saving…' : 'Save' }}
          </button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.classification-modal-backdrop {
  position: absolute;
  inset: 0;
  background: rgba(15, 23, 42, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 60;
  padding: 1.5rem;
}

.classification-modal {
  background: #ffffff;
  border-radius: 16px;
  box-shadow: 0 12px 40px rgba(15, 23, 42, 0.18);
  width: 100%;
  max-width: 380px;
  overflow: hidden;
}

.modal-header {
  padding: 1.1rem 1.25rem;
  border-bottom: 1px solid #eef2f7;
}

.modal-title {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  color: #1e293b;
}

.modal-body {
  padding: 1.25rem;
}

.modal-description {
  margin: 0 0 1rem;
  font-size: 0.88rem;
  color: #64748b;
}

.level-options {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.level-option {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  padding: 0.7rem 0.85rem;
  border: 1.5px solid #e2e8f0;
  border-radius: 10px;
  background: #ffffff;
  cursor: pointer;
  transition: all 0.15s ease;
}

.level-option:hover {
  background: #f8fafc;
  border-color: #cbd5e1;
}

.level-option.selected {
  border-color: #7c3aed;
  background: #faf5ff;
}

.level-option.selected.option-public {
  border-color: #059669;
  background: #ecfdf5;
}
.level-option.selected.option-internal {
  border-color: #2563eb;
  background: #eff6ff;
}
.level-option.selected.option-sensitive {
  border-color: #d97706;
  background: #fffbeb;
}
.level-option.selected.option-confidential {
  border-color: #dc2626;
  background: #fef2f2;
}

/* Radio circle */
.level-radio {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 2px solid #cbd5e1;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.level-option.selected .level-radio {
  border-color: #7c3aed;
}
.level-option.selected.option-public .level-radio {
  border-color: #059669;
}
.level-option.selected.option-internal .level-radio {
  border-color: #2563eb;
}
.level-option.selected.option-sensitive .level-radio {
  border-color: #d97706;
}
.level-option.selected.option-confidential .level-radio {
  border-color: #dc2626;
}

.level-radio-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #7c3aed;
}

.level-option.selected.option-public .level-radio-dot {
  background: #059669;
}
.level-option.selected.option-internal .level-radio-dot {
  background: #2563eb;
}
.level-option.selected.option-sensitive .level-radio-dot {
  background: #d97706;
}
.level-option.selected.option-confidential .level-radio-dot {
  background: #dc2626;
}

.level-label {
  font-size: 0.9rem;
  font-weight: 600;
  color: #334155;
}

.modal-actions {
  display: flex;
  gap: 0.5rem;
  padding: 0.85rem 1.25rem 1.1rem;
  border-top: 1px solid #eef2f7;
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

.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.2s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}
</style>
