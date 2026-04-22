import { ref, computed } from 'vue'

/**
 * Persist a reactive state in localStorage and restore on reload.
 * @param {string} key - localStorage key
 * @param {*} defaultValue - initial value if nothing in localStorage
 */
export function useReload(key, defaultValue) {
  const stored = localStorage.getItem(key)
  const internal = ref(stored ? JSON.parse(stored) : defaultValue)

  // Load from localStorage on init
  const state = computed({
    get: () => internal.value,
    set: (val) => {
      internal.value = val
      localStorage.setItem(key, JSON.stringify(val))
    }
  })
  const clear = () => {
    internal.value = defaultValue
    localStorage.removeItem(key)
  }
  return { state, clear }
}
// function to clear  search state
export function clearAllSearchState() {
  const keys = [
    // search Keys
    'searchMatches',
    'searchAllMatches',
    'selectedFile',
    'selectedMatch',
    'lastQuery',
    'isPreviewOpen',
    // AI summary keys
    'aiSummary',
    'aiSummaryHtmlRaw',
    'summaryPointer',
    'summaryError',
    'isGeneratingSummary'
  ]

  keys.forEach((key) => localStorage.removeItem(key))
}
