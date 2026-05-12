/*
*
  useReload(key, initialValue) — creates a ref initialized from localStorage (or the provided default). A watch with { deep: true, flush: 'sync' } 
  persists every change back to localStorage immediately. Returns { state, clear } where clear() resets to the default and removes the key from storage.
  clearAllSearchState() — removes all predefined search-related keys from localStorage in one call (used on logout to wipe stale state).
*
*/
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
