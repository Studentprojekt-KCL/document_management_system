import { describe, it, expect, vi, beforeEach } from 'vitest'

/* ──────────────────────────────────────────────
   Mocks — must be declared before the import
   that triggers them
   ────────────────────────────────────────────── */

// Mock useSearchMetadata to return a controllable uniquePointer
const mockUniquePointer = { value: 'ptr-abc-123' }
vi.mock('@/composables/useSearchMetadata', () => ({
  useSearchMetadata: () => ({ uniquePointer: mockUniquePointer })
}))

// Mock authFetch so we never hit the network
const mockAuthFetch = vi.fn()
vi.mock('@/utils/api', () => ({
  authFetch: (...args) => mockAuthFetch(...args),
  API_PATHS: { rerank: '/api/rerank' }
}))

// Mock useReload to return plain refs (the real one persists across HMR)
vi.mock('@/composables/useReload', () => {
  const { ref } = require('vue')
  const store = {}
  return {
    useReload: (key, initial) => {
      if (!store[key]) store[key] = { state: ref(initial) }
      return store[key]
    }
  }
})

import { useAIRerank } from '@/composables/aiRerank'

/* ═══════════════════════════════════════════════ */

describe('useAIRerank', () => {
  let rerank

  beforeEach(() => {
    vi.clearAllMocks()
    rerank = useAIRerank({ selectedMatch: { unique_pointer: 'ptr-abc-123' } })
    // Reset state between tests
    rerank.aiRerankResults.value = []
    rerank.rerankPointer.value = ''
    rerank.rerankFilename.value = ''
    rerank.isReranking.value = false
    rerank.rerankError.value = ''
    mockUniquePointer.value = 'ptr-abc-123'
  })

  it('returns all expected keys', () => {
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

  /* ─── aiRerankResultsComputed ─── */

  describe('aiRerankResultsComputed', () => {
    it('returns results when rerankPointer matches uniquePointer', () => {
      rerank.aiRerankResults.value = [{ name: 'a.pdf', score: 0.95, rank: 1 }]
      rerank.rerankPointer.value = 'ptr-abc-123'

      expect(rerank.aiRerankResultsComputed.value).toHaveLength(1)
    })

    it('returns empty array when pointers differ', () => {
      rerank.aiRerankResults.value = [{ name: 'a.pdf', score: 0.95, rank: 1 }]
      rerank.rerankPointer.value = 'ptr-OTHER'

      expect(rerank.aiRerankResultsComputed.value).toEqual([])
    })
  })

  /* ─── generateAIRerank — success ─── */

  describe('generateAIRerank — success', () => {
    const apiResults = [
      { name: 'alpha.pdf', score: 0.92, unique_pointer: 'ptr-1' },
      { name: 'beta.docx', score: 0.78, unique_pointer: 'ptr-2' }
    ]

    beforeEach(() => {
      mockAuthFetch.mockResolvedValue({
        ok: true,
        json: async () => ({ ranked_results: apiResults })
      })
    })

    it('calls authFetch with the correct pointer payload', async () => {
      await rerank.generateAIRerank('my-file.pdf')

      expect(mockAuthFetch).toHaveBeenCalledWith('/api/rerank', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pointers: ['ptr-abc-123'] })
      })
    })

    it('sets isReranking to true during the request', async () => {
      // Start but don't await
      let resolveResponse
      mockAuthFetch.mockReturnValue(
        new Promise((res) => {
          resolveResponse = res
        })
      )

      const promise = rerank.generateAIRerank()
      expect(rerank.isReranking.value).toBe(true)

      resolveResponse({ ok: true, json: async () => ({ ranked_results: [] }) })
      await promise
      expect(rerank.isReranking.value).toBe(false)
    })

    it('maps ranked results with rank and scorePercent', async () => {
      await rerank.generateAIRerank('my-file.pdf')

      const results = rerank.aiRerankResults.value
      expect(results).toHaveLength(2)
      expect(results[0]).toMatchObject({ rank: 1, scorePercent: '92.0%' })
      expect(results[1]).toMatchObject({ rank: 2, scorePercent: '78.0%' })
    })

    it('stores the rerankPointer and rerankFilename on success', async () => {
      await rerank.generateAIRerank('my-file.pdf')

      expect(rerank.rerankPointer.value).toBe('ptr-abc-123')
      expect(rerank.rerankFilename.value).toBe('my-file.pdf')
    })

    it('clears previous error on success', async () => {
      rerank.rerankError.value = 'old error'
      await rerank.generateAIRerank()

      expect(rerank.rerankError.value).toBe('')
    })
  })

  /* ─── generateAIRerank — error handling ─── */

  describe('generateAIRerank — errors', () => {
    it('sets rerankError on non-ok response', async () => {
      mockAuthFetch.mockResolvedValue({ ok: false, status: 500 })

      await rerank.generateAIRerank()

      expect(rerank.rerankError.value).toContain('500')
      expect(rerank.aiRerankResults.value).toEqual([])
    })

    it('sets rerankError on network failure', async () => {
      mockAuthFetch.mockRejectedValue(new Error('Network down'))

      await rerank.generateAIRerank()

      expect(rerank.rerankError.value).toBe('Network down')
    })

    it('sets isReranking back to false after error', async () => {
      mockAuthFetch.mockRejectedValue(new Error('fail'))

      await rerank.generateAIRerank()

      expect(rerank.isReranking.value).toBe(false)
    })
  })

  /* ─── generateAIRerank — no pointer ─── */

  describe('generateAIRerank — no uniquePointer', () => {
    it('resets state and returns early without calling authFetch', async () => {
      mockUniquePointer.value = ''

      await rerank.generateAIRerank()

      expect(mockAuthFetch).not.toHaveBeenCalled()
      expect(rerank.aiRerankResults.value).toEqual([])
      expect(rerank.rerankFilename.value).toBe('')
      expect(rerank.rerankError.value).toBe('')
    })
  })

  /* ─── Edge cases ─── */

  describe('edge cases', () => {
    it('handles missing ranked_results in response', async () => {
      mockAuthFetch.mockResolvedValue({
        ok: true,
        json: async () => ({})
      })

      await rerank.generateAIRerank()

      expect(rerank.aiRerankResults.value).toEqual([])
    })

    it('handles null score gracefully (defaults to 0)', async () => {
      mockAuthFetch.mockResolvedValue({
        ok: true,
        json: async () => ({
          ranked_results: [{ name: 'x.pdf', score: null }]
        })
      })

      await rerank.generateAIRerank()

      expect(rerank.aiRerankResults.value[0].scorePercent).toBe('0.0%')
    })
  })
})
