import { ref, watch } from 'vue'

const SEARCH_STORAGE_KEYS = [
  'searchMatches',
  'searchAllMatches',
  'selectedFile',
  'selectedMatch',
  'lastQuery',
  'isPreviewOpen',
  'aiSummary',
  'aiSummaryHtmlRaw',
  'summaryPointer',
  'summaryError',
  'isGeneratingSummary'
]

export function useReload(key, initialValue) {
  const stored = localStorage.getItem(key)
  const state = ref(stored ? JSON.parse(stored) : initialValue)

  watch(
    state,
    (newVal) => {
      localStorage.setItem(key, JSON.stringify(newVal))
    },
    { deep: true, flush: 'sync' }
  )

  const clear = () => {
    state.value = initialValue
    localStorage.removeItem(key)
  }

  return { state, clear }
}

export function clearAllSearchState() {
  SEARCH_STORAGE_KEYS.forEach((key) => localStorage.removeItem(key))
}
