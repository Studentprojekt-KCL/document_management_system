import { ref } from 'vue'
import { useSearchMetadata } from '@/composables/useSearchMetadata'

export function useAIRerank(props) {
  /* Unique pointer from metadata */
  const { uniquePointer } = useSearchMetadata(props)
  const API_BASE_URL = window.__ENV__.API_BASE_URL.replace(/\/$/, '')

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
        pointer,
        scorePercent
      }
    })

  /* Rerank for specific file and disappears when new file is selected */
  // const aiRerankResultsComputed = computed(() => (rerankPointer.value === uniquePointer.value ? aiRerankResults.value : []))

  /* HARDCODED results for testing UI without backend, remove when backend is ready */
  /* const testResult = [
    {
      rank: 1,
      pointer: `Similar-file-1`,
      filename: 'emil_i_lÃ¶nneberga.txt',
      scorePercent: '93.0%'
    },
    {
      rank: 2,
      pointer: `Similar-file-2`,
      filename: 'jesper_lennehag.txt',
      scorePercent: '89.0%'
    },
    {
      rank: 3,
      pointer: `Similar-file-3`,
      filename: 'dmis_api.md',
      scorePercent: '84.0%'
    }
  ] */

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
    const access_token = sessionStorage.getItem('access_token')

    try {
      // testing
      // await new Promise((resolve) => setTimeout(resolve, 1500)) // Remove when backend is ready
      // aiRerankResults.value = testResult // Remove when backend is ready
      // rerankPointer.value = uniquePointer.value // Remove when backend is ready
      // return // Remove when backend is ready
      const response = await globalThis.fetch(`${API_BASE_URL}/rerank`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${access_token}`
        },
        body: JSON.stringify({ pointers: [uniquePointer.value] })
      })

      if (!response.ok) {
        throw new Error(`Rerank request failed (${response.status})`)
      }

      const data = await response.json()
      const rankedResults = Array.isArray(data.ranked_results) ? data.ranked_results : []
      aiRerankResults.value = mapRankedResults(rankedResults)
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
