<script setup>
/**
 * ConnectModal Component
 * A modal used for connecting our different source systems.
 * It supports both basic auth (username/password) and sessionbased auth.
 * Used in ConnectedSourcesView.vue when user clicks "Connect" on a source that is not yet connected.
 */
import { computed, ref, watch } from 'vue'
import { X } from 'lucide-vue-next'

const props = defineProps({
  open: { type: Boolean, default: false },
  sourceName: { type: String, default: '' },
  loading: { type: Boolean, default: false },
  authMethod: { type: String, default: 'unknown' },
  authEndpoint: { type: String, default: '' },
  errorMessage: { type: String, default: '' }
})

const emit = defineEmits(['close', 'connect'])

const normalizedAuthMethod = computed(() => String(props.authMethod || '').toLowerCase())

const usesSessionAuth = computed(() => normalizedAuthMethod.value === 'session')
const usesBasicAuth = computed(() => normalizedAuthMethod.value === 'ba')

const username = ref('')
const password = ref('')

watch(
  () => props.open,
  (isOpen) => {
    if (!isOpen) {
      username.value = ''
      password.value = ''
    }
  }
)

const submitConnection = computed(() => {
  if (usesBasicAuth.value) {
    return Boolean(username.value.trim() && password.value)
  }
  return true
})

const handleConnect = () => {
  if (!submitConnection.value || props.loading) return
  emit('connect', {
    source: props.sourceName,
    endpoint: props.authEndpoint,
    method: normalizedAuthMethod.value,
    username: username.value.trim(),
    password: password.value
  })
}
</script>

<template>
  <div v-if="open" class="modal-overlay" @click.self="emit('close')">
    <div class="modal">
      <div class="modal-header">
        <h2>Connect to {{ sourceName }}</h2>
        <button class="close-btn" @click="emit('close')">
          <X :size="18" />
        </button>
      </div>
      <div class="modal-body">
        <template v-if="usesBasicAuth">
          <form class="credential-form" @submit.prevent="handleConnect">
            <label for="username">Username</label>
            <input
              id="username"
              v-model="username"
              autocomplete="username"
              type="text"
              placeholder="Enter username"
              maxlength="256"
            />

            <label for="password">Password</label>
            <input
              id="password"
              v-model="password"
              autocomplete="current-password"
              type="password"
              placeholder="Enter password"
              maxlength="256"
            />

            <div class="modal-footer">
              <button class="connect-btn" :disabled="!submitConnection || loading" type="submit" @click="handleConnect">
                {{ loading ? 'Connecting...' : 'Connect' }}
              </button>
            </div>
          </form>
        </template>

        <template v-else-if="usesSessionAuth">
          <p>This source uses session-based authentication.</p>
          <p>Click "Continue" to authenticate to {{ sourceName }}.</p>
          <div class="modal-footer">
            <button class="connect-btn" :disabled="loading" @click="handleConnect">
              {{ loading ? 'Connecting...' : 'Continue' }}
            </button>
          </div>
        </template>

        <template v-else>
          <p>Unsupported authentication method for this source.</p>
        </template>

        <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  inset: 0;
}

.modal {
  width: 100%;
  max-width: 500px;
  background: #ffffff;
  border-radius: 16px;
  padding: 1.5rem;
}

.modal-header {
  display: flex;
  justify-content: space-between;
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
  cursor: pointer;
}

.credential-form {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.credential-form input {
  padding: 0.85rem 1rem;
  border-radius: 10px;
  border: 1px solid #dbe1ea;
  background: #f8fafc;
  font-size: 1rem;
}

.credential-form input:focus {
  outline: none;
  border-color: #7c3aed;
  background: #ffffff;
  box-shadow: 0 0 0 4px rgba(124, 58, 237, 0.12);
}

.credential-form input::placeholder {
  color: #94a3b8;
}

.modal-footer {
  margin-top: 1rem;
  display: flex;
  justify-content: flex-end;
}

.connect-btn {
  padding: 0.75rem 1.5rem;
  background: #7c3aed;
  color: #ffffff;
  border: none;
  border-radius: 8px;
  cursor: pointer;
}

.connect-btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.error-message {
  margin-top: 0.75rem;
  color: #b91c1c;
}
</style>
