/* useAIRerank Tests */
import { describe, it, expect, vi, beforeEach } from 'vitest'

const mockUniquePointer = { value: 'ptr-abc-123' }
vi.mock('@/composables/useSearchMetadata', () => ({
  useSearchMetadata: () => ({ uniquePointer: mockUniquePointer })
}))

const mockAuthFetch = vi.fn()
vi.mock('@/utils/api', () => ({
  authFetch: (...args) => mockAuthFetch(...args),
  API_PATHS: { rerank: '/api/rerank' }
}))

import { useAIRerank } from '@/composables/aiRerank'

describe('useAIRerank', () => {
  let rerank

  beforeEach(() => {
    vi.clearAllMocks()
    mockUniquePointer.value = 'ptr-abc-123'
    rerank = useAIRerank({ selectedMatch: { unique_pointer: 'ptr-abc-123' } })
    rerank.rerankError.value = ''
    rerank.isReranking.value = false
  })

  it('returns all expected reactive keys and methods', () => {
    const keys = [
      'aiRerankResults',
      'aiRerankResultsComputed',
      'rerankPointer',
      'rerankFilename',
      'isReranking',
      'rerankError',
      'generateAIRerank'
    ]
    keys.forEach((key) => {
      expect(rerank).toHaveProperty(key)
    })
  })

  describe('aiRerankResultsComputed', () => {
    it('returns results when rerankPointer matches uniquePointer', () => {
      rerank.rerankPointer.value = 'ptr-abc-123'
      rerank.aiRerankResults.value = [{ id: 1 }]
      expect(rerank.aiRerankResultsComputed.value).toEqual([{ id: 1 }])
    })

    it('returns empty array when rerankPointer does not match', () => {
      rerank.rerankPointer.value = 'ptr-different'
      rerank.aiRerankResults.value = [{ id: 1 }]
      expect(rerank.aiRerankResultsComputed.value).toEqual([])
    })
  })

  describe('generateAIRerank — success', () => {
    beforeEach(() => {
      mockAuthFetch.mockResolvedValue({
        ok: true,
        json: async () => [
          { filename: 'doc1.pdf', score: 0.95 },
          { filename: 'doc2.pdf', score: 0.8 }
        ]
      })
    })

    it('sends GET request to rerank endpoint with correct pointer', async () => {
      await rerank.generateAIRerank('test.pdf')
      const [url] = mockAuthFetch.mock.calls[0]
      expect(url.pathname).toBe('/api/rerank')
      expect(url.searchParams.get('pointer')).toBe('ptr-abc-123')
    })

    it('toggles isReranking during fetch', async () => {
      let resolveResponse
      mockAuthFetch.mockReturnValue(
        new Promise((res) => {
          resolveResponse = res
        })
      )

      const promise = rerank.generateAIRerank('test.pdf')
      expect(rerank.isReranking.value).toBe(true)

      resolveResponse({
        ok: true,
        json: async () => []
      })
      await promise
      expect(rerank.isReranking.value).toBe(false)
    })

    it('maps API response to include rank and scorePercent', async () => {
      await rerank.generateAIRerank('test.pdf')
      expect(rerank.aiRerankResults.value).toEqual([
        { filename: 'doc1.pdf', score: 0.95, rank: 1, scorePercent: '95.0%' },
        { filename: 'doc2.pdf', score: 0.8, rank: 2, scorePercent: '80.0%' }
      ])
    })

    it('stores rerankPointer and rerankFilename on success', async () => {
      await rerank.generateAIRerank('myfile.pdf')
      expect(rerank.rerankPointer.value).toBe('ptr-abc-123')
      expect(rerank.rerankFilename.value).toBe('myfile.pdf')
    })

    it('clears rerankError on successful fetch', async () => {
      rerank.rerankError.value = 'old error'
      await rerank.generateAIRerank('test.pdf')
      expect(rerank.rerankError.value).toBe('')
    })
  })

  describe('generateAIRerank — errors', () => {
    it('sets rerankError on non-ok HTTP response', async () => {
      mockAuthFetch.mockResolvedValue({ ok: false, status: 500 })
      await rerank.generateAIRerank('test.pdf')
      expect(rerank.rerankError.value).toContain('500')
    })

    it('sets rerankError on network failures', async () => {
      mockAuthFetch.mockRejectedValue(new Error('Network error'))
      await rerank.generateAIRerank('test.pdf')
      expect(rerank.rerankError.value).toBe('Network error')
    })

    it('resets isReranking after errors', async () => {
      mockAuthFetch.mockRejectedValue(new Error('fail'))
      await rerank.generateAIRerank('test.pdf')
      expect(rerank.isReranking.value).toBe(false)
    })
  })

  describe('generateAIRerank — no pointer', () => {
    it('resets state and aborts fetch when uniquePointer is empty', async () => {
      mockUniquePointer.value = ''
      rerank.aiRerankResults.value = [{ id: 1 }]
      rerank.rerankFilename.value = 'old'
      rerank.rerankError.value = 'old error'

      await rerank.generateAIRerank('test.pdf')

      expect(mockAuthFetch).not.toHaveBeenCalled()
      expect(rerank.aiRerankResults.value).toEqual([])
      expect(rerank.rerankFilename.value).toBe('')
      expect(rerank.rerankError.value).toBe('')
    })
  })

  describe('edge cases', () => {
    it('handles non-array response gracefully', async () => {
      mockAuthFetch.mockResolvedValue({
        ok: true,
        json: async () => ({ ranked_results: 'not an array' })
      })
      await rerank.generateAIRerank('test.pdf')
      expect(rerank.aiRerankResults.value).toEqual([])
    })

    it('defaults null scores to 0', async () => {
      mockAuthFetch.mockResolvedValue({
        ok: true,
        json: async () => [{ filename: 'doc.pdf', score: null }, { filename: 'doc2.pdf' }]
      })
      await rerank.generateAIRerank('test.pdf')
      expect(rerank.aiRerankResults.value[0].scorePercent).toBe('0.0%')
      expect(rerank.aiRerankResults.value[1].scorePercent).toBe('0.0%')
    })
  })
})
