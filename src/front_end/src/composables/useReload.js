import { ref, watch } from 'vue'

/**
 * Persist a reactive state in localStorage and restore on reload.
 * @param {string} key - localStorage key
 * @param {*} defaultValue - initial value if nothing in localStorage
 */
export function useReload(key, defaultValue) {
  const state = ref(defaultValue)

  // Load from localStorage on init
  try {
    const stored = localStorage.getItem(key)
    if (stored) state.value = JSON.parse(stored)
  } catch (err) {
    console.warn(`Failed to load ${key} from localStorage:`, err)
  }

  // Saves to localStorage whenever it changes
  watch(
    state,
    (val) => {
      try {
        localStorage.setItem(key, JSON.stringify(val))
      } catch (err) {
        console.warn(`Failed to save ${key} to localStorage:`, err)
      }
    },
    { deep: true }
  )

  const clear = () => {
    state.value = defaultValue
    localStorage.removeItem(key)
  }

  return { state, clear }
}
// clears state
export function clearAllSearchState() {
  const keys = [
    'searchMatches',
    'searchAllMatches',
    'selectedFile',
    'selectedMatch',
    'lastQuery',
    'isPreviewOpen'
  ]
  keys.forEach(key => localStorage.removeItem(key))
}