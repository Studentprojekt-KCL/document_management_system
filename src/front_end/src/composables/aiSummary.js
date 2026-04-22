import { computed } from 'vue'
import { useSearchMetadata } from '@/composables/useSearchMetadata'
import { authFetch, API_PATHS } from '@/utils/api'
import { useReload } from '@/composables/useReload'

export function useAISummary(props) {
  /* Unique pointer from metadata */
  const { uniquePointer } = useSearchMetadata(props)

  /* Summary state */
  const { state: aiSummary } = useReload('aiSummary', '')
  const { state: aiSummaryHtmlRaw } = useReload('aiSummaryHtmlRaw', '')
  const { state: summaryPointer } = useReload('summaryPointer', '')
  const { state: summaryError } = useReload('summaryError', '')
  const { state: isGeneratingSummary } = useReload('isGeneratingSummary', false)

  /* Summary for specific file and disappears when new file is selected */
  const aiSummaryHtml = computed(() => (summaryPointer.value === uniquePointer.value ? aiSummaryHtmlRaw.value : ''))

  /* When clicking button Generate AI summary */
  const generateAISummary = async () => {
    if (!uniquePointer.value) {
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
        body: JSON.stringify({ pointers: [uniquePointer.value] })
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
      summaryPointer.value = uniquePointer.value
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
