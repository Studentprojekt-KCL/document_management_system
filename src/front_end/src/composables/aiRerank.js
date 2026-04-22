import { ref, computed } from 'vue'
import { useSearchMetadata, resolveFilename } from '@/composables/useSearchMetadata'
import { authFetch, API_PATHS } from '@/utils/api'

export function useAIRerank(props) {
  /* Unique pointer from metadata */
  const { uniquePointer } = useSearchMetadata(props)

  /* Rerank state */
  const aiRerankResults = ref([])
  const rerankPointer = ref('')
  const isReranking = ref(false)
  const rerankError = ref('')

  const mapRankedResults = (results = []) =>
    results.map((item, index) => {
      const pointer = item?.pointer ?? ''
      const scorePercent = `${(Number(item?.score ?? 0) * 100).toFixed(1)}%`

      return {
        rank: index + 1,
        name: resolveFilename(item, index),
        pointer,
        scorePercent
      }
    })

  /* Rerank results for specific file and disappears when new file is selected */
  const aiRerankResultsComputed = computed(() => (rerankPointer.value === uniquePointer.value ? aiRerankResults.value : []))

  /* When clicking button Rerank */
  const generateAIRerank = async () => {
    if (!uniquePointer.value) {
      aiRerankResults.value = []

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
    } catch (error) {
      rerankError.value = error.message || 'An error occurred while generating AI rerank.'
    } finally {
      isReranking.value = false
    }
  }

  return {
    aiRerankResultsComputed,
    isReranking,
    rerankError,
    generateAIRerank
  }
}
