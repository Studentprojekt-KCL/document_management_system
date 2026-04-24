import { computed } from 'vue'
import { useSearchMetadata } from '@/composables/useSearchMetadata'
import { authFetch, API_PATHS } from '@/utils/api'
import { useReload } from '@/composables/useReload'

export function useAISummary(props = {}) {
  /* Unique pointer from metadata */
  const { uniquePointer } = useSearchMetadata(props)

  /* Summary state */
  const { state: aiSummary } = useReload('aiSummary', '')
  const { state: aiSummaryHtmlRaw } = useReload('aiSummaryHtmlRaw', '')
  const { state: summaryPointer } = useReload('summaryPointer', '')
  const { state: summaryError } = useReload('summaryError', '')
  const { state: isGeneratingSummary } = useReload('isGeneratingSummary', false)

  const aiSummaryHtml = computed(() => {
    if (!uniquePointer.value) {
      return aiSummaryHtmlRaw.value
    }

    return summaryPointer.value === uniquePointer.value ? aiSummaryHtmlRaw.value : ''
  })

  /* Generate summary for selected pointers, including a source/rerank pointer. */
  const generateAISummary = async (pointers = [], sourcePointer = '') => {
    // Current file if nothing selected to summarize
    const filesToSummarize = pointers && pointers.length > 0 ? pointers : uniquePointer.value ? [uniquePointer.value] : []

    // Combine selected files + rerank source pointer, filter for valid strings and removes duplicates (set part)
    const requestPointers = [...new Set([...filesToSummarize, sourcePointer].filter((p) => p?.trim()))]

    if (!requestPointers.length) {
      aiSummary.value = ''
      aiSummaryHtmlRaw.value = ''
      summaryPointer.value = ''
      summaryError.value = ''
      return
    }

    isGeneratingSummary.value = true
    summaryError.value = ''
    aiSummary.value = ''
    aiSummaryHtmlRaw.value = ''
    summaryPointer.value = ''
    try {
      const response = await authFetch(API_PATHS.summarize, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pointers: requestPointers })
      })

      if (!response.ok) {
        throw new Error(`Summary request failed (${response.status})`)
      }

      const contentType = response.headers.get('content-type') || ''
      let summaryText = ''

      if (contentType.includes('application/json')) {
        const data = await response.json()
        summaryText = typeof data.summary === 'string' ? data.summary : JSON.stringify(data)
      } else {
        summaryText = await response.text()
      }

      aiSummary.value = summaryText
      aiSummaryHtmlRaw.value = globalThis.marked ? globalThis.marked.parse(summaryText) : summaryText
      summaryPointer.value = requestPointers.join('|')
    } catch (error) {
      summaryError.value = error.message
    } finally {
      isGeneratingSummary.value = false
    }
  }

  return {
    aiSummaryHtml,
    summaryError,
    isGeneratingSummary,
    generateAISummary
  }
}
