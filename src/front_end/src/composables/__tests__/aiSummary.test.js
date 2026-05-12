/* useAISummary Tests */
import { describe, it, expect, vi, beforeEach } from 'vitest'

const mockUniquePointer = { value: 'ptr-abc-123' }
vi.mock('@/composables/useSearchMetadata', () => ({
  useSearchMetadata: () => ({ uniquePointer: mockUniquePointer })
}))

const mockAuthFetch = vi.fn()
vi.mock('@/utils/api', () => ({
  authFetch: (...args) => mockAuthFetch(...args),
  API_PATHS: { summarize: '/api/summarize' }
}))

vi.mock('@/composables/useReload', () => {
  const store = {}
  return {
    useReload: (key, initial) => {
      if (!store[key]) store[key] = { state: { value: initial } }
      return store[key]
    }
  }
})

// Mock marked for markdown-to-html conversion
globalThis.marked = { parse: (text) => `<p>${text}</p>` }

import { useAISummary } from '@/composables/aiSummary'

describe('useAISummary', () => {
  let summary

  beforeEach(() => {
    vi.clearAllMocks()
    summary = useAISummary({ selectedMatch: { unique_pointer: 'ptr-abc-123' } })
    // Reset state
    summary.summaryError.value = ''
    summary.isGeneratingSummary.value = false
    mockUniquePointer.value = 'ptr-abc-123'
  })

  it('returns all expected keys', () => {
    const keys = ['aiSummaryHtml', 'summaryError', 'isGeneratingSummary', 'generateAISummary']
    keys.forEach((key) => {
      expect(summary).toHaveProperty(key)
    })
  })

  describe('aiSummaryHtml', () => {
    it('returns html when summaryPointer matches uniquePointer', async () => {
      mockAuthFetch.mockResolvedValue({
        ok: true,
        headers: { get: () => 'application/json' },
        json: async () => ({ summary: 'Test summary' })
      })

      await summary.generateAISummary()
      expect(summary.aiSummaryHtml.value).toContain('Test summary')
    })

    it('returns empty string when pointer does not match', async () => {
      mockAuthFetch.mockResolvedValue({
        ok: true,
        headers: { get: () => 'application/json' },
        json: async () => ({ summary: 'Summary text' })
      })

      await summary.generateAISummary()

      // Change uniquePointer after generation
      mockUniquePointer.value = 'ptr-DIFFERENT'

      // The computed should now return empty since pointers diverge
      // (summaryPointer was set to 'ptr-abc-123' but uniquePointer is now different)
      expect(summary.aiSummaryHtml.value).toBe('')
    })
  })

  describe('generateAISummary — single file (default)', () => {
    beforeEach(() => {
      mockAuthFetch.mockResolvedValue({
        ok: true,
        headers: { get: () => 'application/json' },
        json: async () => ({ summary: '# Document Overview\nThis is a test.' })
      })
    })

    it('calls authFetch with the current uniquePointer', async () => {
      await summary.generateAISummary()

      expect(mockAuthFetch).toHaveBeenCalledWith('/api/summarize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pointers: ['ptr-abc-123'] })
      })
    })

    it('sets isGeneratingSummary during the request', async () => {
      let resolveResponse
      mockAuthFetch.mockReturnValue(
        new Promise((res) => {
          resolveResponse = res
        })
      )

      const promise = summary.generateAISummary()
      expect(summary.isGeneratingSummary.value).toBe(true)

      resolveResponse({
        ok: true,
        headers: { get: () => 'application/json' },
        json: async () => ({ summary: 'done' })
      })
      await promise
      expect(summary.isGeneratingSummary.value).toBe(false)
    })

    it('parses markdown via globalThis.marked', async () => {
      await summary.generateAISummary()

      expect(summary.aiSummaryHtml.value).toContain('<p>')
    })
  })

  describe('generateAISummary — multiple pointers (merge)', () => {
    beforeEach(() => {
      mockAuthFetch.mockResolvedValue({
        ok: true,
        headers: { get: () => 'application/json' },
        json: async () => ({ summary: 'Merged summary' })
      })
    })

    it('sends all pointers plus sourcePointer, deduplicated', async () => {
      await summary.generateAISummary(['ptr-1', 'ptr-2'], 'ptr-1')

      const body = JSON.parse(mockAuthFetch.mock.calls[0][1].body)
      // ptr-1 appears in both arrays but should only be sent once
      expect(body.pointers).toEqual(['ptr-1', 'ptr-2'])
    })

    it('filters out empty/whitespace pointers', async () => {
      await summary.generateAISummary(['ptr-1', '', '  '], 'ptr-2')

      const body = JSON.parse(mockAuthFetch.mock.calls[0][1].body)
      expect(body.pointers).toEqual(['ptr-1', 'ptr-2'])
    })

    it('falls back to uniquePointer when pointers array is empty', async () => {
      await summary.generateAISummary([], '')

      const body = JSON.parse(mockAuthFetch.mock.calls[0][1].body)
      expect(body.pointers).toEqual(['ptr-abc-123'])
    })
  })

  describe('generateAISummary — plain text response', () => {
    it('handles non-JSON content-type by reading as text', async () => {
      mockAuthFetch.mockResolvedValue({
        ok: true,
        headers: { get: () => 'text/plain' },
        text: async () => 'Plain text summary'
      })

      await summary.generateAISummary()

      expect(summary.aiSummaryHtml.value).toContain('Plain text summary')
    })
  })

  describe('generateAISummary — errors', () => {
    it('sets summaryError on non-ok response', async () => {
      mockAuthFetch.mockResolvedValue({ ok: false, status: 503 })

      await summary.generateAISummary()

      expect(summary.summaryError.value).toContain('503')
    })

    it('sets summaryError on network failure', async () => {
      mockAuthFetch.mockRejectedValue(new Error('Connection refused'))

      await summary.generateAISummary()

      expect(summary.summaryError.value).toBe('Connection refused')
    })

    it('resets isGeneratingSummary after error', async () => {
      mockAuthFetch.mockRejectedValue(new Error('fail'))

      await summary.generateAISummary()

      expect(summary.isGeneratingSummary.value).toBe(false)
    })
  })

  describe('generateAISummary — no valid pointers', () => {
    it('resets state and skips fetch when no pointers resolve', async () => {
      mockUniquePointer.value = ''

      await summary.generateAISummary([], '')

      expect(mockAuthFetch).not.toHaveBeenCalled()
      expect(summary.summaryError.value).toBe('')
    })
  })

  describe('edge: globalThis.marked unavailable', () => {
    it('falls back to raw text when marked is not loaded', async () => {
      const originalMarked = globalThis.marked
      globalThis.marked = undefined

      mockAuthFetch.mockResolvedValue({
        ok: true,
        headers: { get: () => 'application/json' },
        json: async () => ({ summary: 'raw text fallback' })
      })

      await summary.generateAISummary()

      expect(summary.aiSummaryHtml.value).toContain('raw text fallback')

      globalThis.marked = originalMarked
    })
  })
})
