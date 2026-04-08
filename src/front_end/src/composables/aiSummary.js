import { computed, ref } from 'vue'
import { useSearchMetadata } from '@/composables/useSearchMetadata'

export function useAISummary(props) {
  /* Unique pointer from metadata */
  const { uniquePointer } = useSearchMetadata(props)

  const API_BASE_URL = import.meta.env.API_BASE_URL.replace(/\/$/, '')

  /* Summary state */
  const aiSummary = ref('')
  const aiSummaryHtmlRaw = ref('')
  const summaryPointer = ref('')
  const summaryError = ref('')
  const isGeneratingSummary = ref(false)

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
    const access_token = sessionStorage.getItem('access_token')

    try {
      const response = await globalThis.fetch(`${API_BASE_URL}/summary`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          Authorization: `Bearer ${access_token}`
        },
        body: JSON.stringify({ file_pointer: uniquePointer.value })
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
