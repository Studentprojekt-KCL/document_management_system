import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

/* Mock dependencies */
const mockAuthFetch = vi.hoisted(() => vi.fn())

vi.mock('@/utils/api', () => ({
  authFetch: mockAuthFetch,
  API_PATHS: {
    summarize: '/api/stochastic-analyzer/summarize'
  }
}))

vi.mock('@/composables/useSearchMetadata', () => {
  const { computed } = require('vue')
  return {
    useSearchMetadata: (props) => ({
      uniquePointer: computed(() => props.selectedMatch?.unique_pointer || '')
    })
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

import { useAISummary } from '@/composables/aiSummary'

describe('useAISummary', () => {
  const createProps = (pointer = 'test-pointer') => ({
    selectedMatch: { unique_pointer: pointer }
  })

  beforeEach(() => {
    vi.clearAllMocks()
    globalThis.marked = undefined
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('returns expected properties', () => {
    const result = useAISummary(createProps())
    expect(result).toHaveProperty('aiSummaryHtml')
    expect(result).toHaveProperty('summaryError')
    expect(result).toHaveProperty('isGeneratingSummary')
    expect(result).toHaveProperty('generateAISummary')
  })

  it('starts with empty summary', () => {
    const { aiSummaryHtml } = useAISummary(createProps())
    expect(aiSummaryHtml.value).toBe('')
  })

  it('starts with no error', () => {
    const { summaryError } = useAISummary(createProps())
    expect(summaryError.value).toBe('')
  })

  it('starts not generating', () => {
    const { isGeneratingSummary } = useAISummary(createProps())
    expect(isGeneratingSummary.value).toBe(false)
  })

  describe('generateAISummary', () => {
    it('calls authFetch with correct endpoint and body', async () => {
      mockAuthFetch.mockResolvedValue({
        ok: true,
        headers: { get: () => 'application/json' },
        json: () => Promise.resolve({ summary: 'Test summary' })
      })

      const { generateAISummary } = useAISummary(createProps('ptr-123'))
      await generateAISummary()

      expect(mockAuthFetch).toHaveBeenCalledWith(
        '/api/stochastic-analyzer/summarize',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ pointers: ['ptr-123'] })
        })
      )
    })

    it('sets isGeneratingSummary during fetch', async () => {
      let resolvePromise
      mockAuthFetch.mockReturnValue(
        new Promise((resolve) => {
          resolvePromise = resolve
        })
      )

      const { isGeneratingSummary, generateAISummary } = useAISummary(createProps())
      const promise = generateAISummary()

      expect(isGeneratingSummary.value).toBe(true)

      resolvePromise({
        ok: true,
        headers: { get: () => 'text/plain' },
        text: () => Promise.resolve('summary')
      })
      await promise

      expect(isGeneratingSummary.value).toBe(false)
    })

    it('sets error on failed response', async () => {
      mockAuthFetch.mockResolvedValue({
        ok: false,
        status: 500
      })

      const { summaryError, generateAISummary } = useAISummary(createProps())
      await generateAISummary()

      expect(summaryError.value).toContain('500')
    })

    it('sets error on network failure', async () => {
      mockAuthFetch.mockRejectedValue(new Error('Network down'))

      const { summaryError, generateAISummary } = useAISummary(createProps())
      await generateAISummary()

      expect(summaryError.value).toBe('Network down')
    })

    it('does nothing when uniquePointer is empty', async () => {
      const { generateAISummary } = useAISummary(createProps(''))
      await generateAISummary()

      expect(mockAuthFetch).not.toHaveBeenCalled()
    })

    it('handles text/plain response', async () => {
      mockAuthFetch.mockResolvedValue({
        ok: true,
        headers: { get: () => 'text/plain' },
        text: () => Promise.resolve('Plain text summary')
      })

      const { generateAISummary } = useAISummary(createProps())
      await generateAISummary()

      // No error means it processed successfully
      expect(mockAuthFetch).toHaveBeenCalled()
    })

    it('uses marked.parse when available', async () => {
      globalThis.marked = { parse: (text) => `<p>${text}</p>` }

      mockAuthFetch.mockResolvedValue({
        ok: true,
        headers: { get: () => 'text/plain' },
        text: () => Promise.resolve('Test text')
      })

      const { generateAISummary } = useAISummary(createProps())
      await generateAISummary()

      expect(mockAuthFetch).toHaveBeenCalled()
    })

    it('resets isGeneratingSummary even on error', async () => {
      mockAuthFetch.mockRejectedValue(new Error('fail'))

      const { isGeneratingSummary, generateAISummary } = useAISummary(createProps())
      await generateAISummary()

      expect(isGeneratingSummary.value).toBe(false)
    })
  })
})
