import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

/* Mock dependencies */
const mockAuthFetch = vi.hoisted(() => vi.fn())

vi.mock('@/utils/api', () => ({
  authFetch: mockAuthFetch,
  API_PATHS: {
    rerank: '/api/stochastic-analyzer/rerank'
  }
}))

vi.mock('@/composables/useSearchMetadata', () => {
  const { computed } = require('vue')
  return {
    useSearchMetadata: (props) => ({
      uniquePointer: computed(() => props.selectedMatch?.unique_pointer || '')
    }),
    resolveFilename: (entry, index) => entry?.name || `result-${index + 1}`
  }
})

vi.mock('@/composables/useReload', () => {
  const { ref } = require('vue')
  return {
    useReload: (key, defaultValue) => ({
      state: ref(defaultValue),
      clear: vi.fn()
    })
  }
})

import { useAIRerank } from '@/composables/aiRerank'

describe('useAIRerank', () => {
  const createProps = (pointer = 'test-pointer') => ({
    selectedMatch: { unique_pointer: pointer }
  })

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('returns expected properties', () => {
    const result = useAIRerank(createProps())
    expect(result).toHaveProperty('aiRerankResultsComputed')
    expect(result).toHaveProperty('isReranking')
    expect(result).toHaveProperty('rerankError')
    expect(result).toHaveProperty('generateAIRerank')
  })

  it('starts with empty results', () => {
    const { aiRerankResultsComputed } = useAIRerank(createProps())
    expect(aiRerankResultsComputed.value).toEqual([])
  })

  it('starts not reranking', () => {
    const { isReranking } = useAIRerank(createProps())
    expect(isReranking.value).toBe(false)
  })

  it('starts with no error', () => {
    const { rerankError } = useAIRerank(createProps())
    expect(rerankError.value).toBe('')
  })

  describe('generateAIRerank', () => {
    it('calls authFetch with correct endpoint and body', async () => {
      mockAuthFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ ranked_results: [] })
      })

      const { generateAIRerank } = useAIRerank(createProps('ptr-456'))
      await generateAIRerank()

      expect(mockAuthFetch).toHaveBeenCalledWith(
        '/api/stochastic-analyzer/rerank',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ pointers: ['ptr-456'] })
        })
      )
    })

    it('sets isReranking during fetch', async () => {
      let resolvePromise
      mockAuthFetch.mockReturnValue(
        new Promise((resolve) => {
          resolvePromise = resolve
        })
      )

      const { isReranking, generateAIRerank } = useAIRerank(createProps())
      const promise = generateAIRerank()

      expect(isReranking.value).toBe(true)

      resolvePromise({
        ok: true,
        json: () => Promise.resolve({ ranked_results: [] })
      })
      await promise

      expect(isReranking.value).toBe(false)
    })

    it('maps ranked results with correct structure', async () => {
      mockAuthFetch.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            ranked_results: [
              { name: 'file1.pdf', pointer: 'ptr1', score: 0.95 },
              { name: 'file2.md', pointer: 'ptr2', score: 0.73 }
            ]
          })
      })

      const { aiRerankResultsComputed, generateAIRerank } = useAIRerank(createProps())
      await generateAIRerank()

      const results = aiRerankResultsComputed.value
      expect(results).toHaveLength(2)
      expect(results[0]).toEqual({
        rank: 1,
        name: 'file1.pdf',
        pointer: 'ptr1',
        scorePercent: '95.0%'
      })
      expect(results[1]).toEqual({
        rank: 2,
        name: 'file2.md',
        pointer: 'ptr2',
        scorePercent: '73.0%'
      })
    })

    it('handles empty ranked_results', async () => {
      mockAuthFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ ranked_results: [] })
      })

      const { aiRerankResultsComputed, generateAIRerank } = useAIRerank(createProps())
      await generateAIRerank()

      expect(aiRerankResultsComputed.value).toEqual([])
    })

    it('handles missing ranked_results key', async () => {
      mockAuthFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({})
      })

      const { aiRerankResultsComputed, generateAIRerank } = useAIRerank(createProps())
      await generateAIRerank()

      expect(aiRerankResultsComputed.value).toEqual([])
    })

    it('sets error on failed response', async () => {
      mockAuthFetch.mockResolvedValue({
        ok: false,
        status: 500
      })

      const { rerankError, generateAIRerank } = useAIRerank(createProps())
      await generateAIRerank()

      expect(rerankError.value).toContain('500')
    })

    it('sets error on network failure', async () => {
      mockAuthFetch.mockRejectedValue(new Error('Connection refused'))

      const { rerankError, generateAIRerank } = useAIRerank(createProps())
      await generateAIRerank()

      expect(rerankError.value).toBe('Connection refused')
    })

    it('does nothing when uniquePointer is empty', async () => {
      const { generateAIRerank } = useAIRerank(createProps(''))
      await generateAIRerank()

      expect(mockAuthFetch).not.toHaveBeenCalled()
    })

    it('resets isReranking even on error', async () => {
      mockAuthFetch.mockRejectedValue(new Error('fail'))

      const { isReranking, generateAIRerank } = useAIRerank(createProps())
      await generateAIRerank()

      expect(isReranking.value).toBe(false)
    })

    it('formats score as percentage with one decimal', async () => {
      mockAuthFetch.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            ranked_results: [{ name: 'test.txt', pointer: 'p', score: 0.1234 }]
          })
      })

      const { aiRerankResultsComputed, generateAIRerank } = useAIRerank(createProps())
      await generateAIRerank()

      expect(aiRerankResultsComputed.value[0].scorePercent).toBe('12.3%')
    })

    it('handles zero score', async () => {
      mockAuthFetch.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            ranked_results: [{ name: 'test.txt', pointer: 'p', score: 0 }]
          })
      })

      const { aiRerankResultsComputed, generateAIRerank } = useAIRerank(createProps())
      await generateAIRerank()

      expect(aiRerankResultsComputed.value[0].scorePercent).toBe('0.0%')
    })
  })
})
