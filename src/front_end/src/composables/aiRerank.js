import { computed, ref } from 'vue'
import { useSearchMetadata } from '@/composables/useSearchMetadata'
import { authFetch, API_PATHS } from '@/utils/api'

const DEFAULT_RERANK_COUNT = 5

export function useAIRerank(props = {}) {
  /* Unique pointer from metadata */
  const { uniquePointer } = useSearchMetadata(props)

  /* Rerank state */
  const aiRerankResults = ref([])
  const rerankPointer = ref('')
  const rerankFilename = ref('')
  const rerankError = ref('')
  const isReranking = ref(false)

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
      const rerankUrl = new URL(API_PATHS.rerank, window.location.origin)
      rerankUrl.searchParams.set('pointer', uniquePointer.value)
      rerankUrl.searchParams.set('count', String(DEFAULT_RERANK_COUNT))

      const response = await authFetch(rerankUrl, {
        method: 'GET'
      })

      if (!response.ok) {
        throw new Error(`Rerank request failed (${response.status})`)
      }

      const data = await response.json()
      const rankedResults = Array.isArray(data) ? data : []
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
