import { computed } from 'vue'
import { useSearchMetadata } from '@/composables/useSearchMetadata'
import { authFetch, API_PATHS } from '@/utils/api'
import { useReload } from '@/composables/useReload'

export function useAIRerank(props = {}) {
  /* Unique pointer from metadata */
  const { uniquePointer } = useSearchMetadata(props)

  /* Rerank state */
  const { state: aiRerankResults } = useReload('aiRerankResults', [])
  const { state: rerankPointer } = useReload('rerankPointer', '')
  const { state: rerankFilename } = useReload('rerankFilename', '')
  const { state: isReranking } = useReload('isReranking', false)
  const { state: rerankError } = useReload('rerankError', '')

  const mapRankedResults = (results = []) =>
    results.map((item, index) => ({
      ...item,
      rank: index + 1,
      scorePercent: `${(Number(item?.score ?? 0) * 100).toFixed(1)}%`
    }))

  /* Rerank results for specific file and disappears when new file is selected */
  const aiRerankResultsComputed = computed(() => (rerankPointer.value === uniquePointer.value ? aiRerankResults.value : []))

  /* When clicking button Rerank */
  const generateAIRerank = async (filename = '') => {
    if (!uniquePointer.value) {
      aiRerankResults.value = []
      rerankFilename.value = ''
      rerankError.value = ''
      return
    }

    isReranking.value = true
    rerankError.value = ''
    rerankPointer.value = ''
    aiRerankResults.value = []

    try {
      const response = await authFetch(API_PATHS.rerank, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pointers: [uniquePointer.value] })
      })

      if (!response.ok) {
        throw new Error(`Rerank request failed (${response.status})`)
      }

      const data = await response.json()
      const rankedResults = Array.isArray(data.ranked_results) ? data.ranked_results : []
      aiRerankResults.value = mapRankedResults(rankedResults)
      rerankPointer.value = uniquePointer.value
      rerankFilename.value = filename
    } catch (error) {
      rerankError.value = error.message || 'An error occurred while generating AI rerank.'
    } finally {
      isReranking.value = false
    }
  }

  return {
    aiRerankResults,
    aiRerankResultsComputed,
    rerankPointer,
    rerankFilename,
    isReranking,
    rerankError,
    generateAIRerank
  }
}
