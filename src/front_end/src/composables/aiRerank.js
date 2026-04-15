import { ref } from 'vue'
import { useSearchMetadata } from '@/composables/useSearchMetadata'

export function useAIRerank(props) {
  /* Unique pointer from metadata */
  const { uniquePointer } = useSearchMetadata(props)

  const API_BASE_URL = window.__ENV__.API_BASE_URL.replace(/\/$/, '')

  /* Rerank state */
  const aiRerankResults = ref([])
  const isReranking = ref(false)
  const rerankError = ref('')

  /* When clicking button Rerank */
  const generateAIRerank = async () => {
    if (!uniquePointer.value) {
      aiRerankResults.value = []
      rerankError.value = ''
      return
    }

    isReranking.value = true
    rerankError.value = ''
    aiRerankResults.value = []
    const access_token = sessionStorage.getItem('access_token')

    try {
      const response = await globalThis.fetch(`${API_BASE_URL}/stochastic-analyzer/rerank`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${access_token}`
        },
        body: JSON.stringify({ pointer: uniquePointer.value })
      })

      if (!response.ok) {
        throw new Error(`Rerank request failed (${response.status})`)
      }

      const data = await response.json()
      aiRerankResults.value = Array.isArray(data.reranked_results) ? data.reranked_results : []
    } catch (error) {
      rerankError.value = error.message || 'An error occurred while generating AI rerank.'
    } finally {
      isReranking.value = false
    }
  }

  return {
    aiRerankResults,
    isReranking,
    rerankError,
    generateAIRerank
  }
}
