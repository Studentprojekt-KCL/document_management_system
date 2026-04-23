import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

/* Mock config before importing api */
vi.mock('@/utils/config', () => ({
  SESSION_KEY_ACCESS_TOKEN: 'access_token'
}))

describe('api.js', () => {
  let fetchMock

  beforeEach(() => {
    fetchMock = vi.fn()
    global.fetch = fetchMock
    localStorage.clear()
  })

  afterEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  describe('authFetch', () => {
    let authFetch

    beforeEach(async () => {
      vi.resetModules()
      const mod = await import('@/utils/api')
      authFetch = mod.authFetch
    })

    it('attaches Bearer token from localStorage', async () => {
      localStorage.setItem('access_token', 'test-token-123')
      fetchMock.mockResolvedValue({ ok: true })

      await authFetch('/api/test')

      expect(fetchMock).toHaveBeenCalledWith('/api/test', {
        headers: {
          Authorization: 'Bearer test-token-123'
        }
      })
    })

    it('passes through additional options', async () => {
      localStorage.setItem('access_token', 'tok')
      fetchMock.mockResolvedValue({ ok: true })

      await authFetch('/api/test', {
        method: 'POST',
        body: '{"key":"value"}'
      })

      expect(fetchMock).toHaveBeenCalledWith('/api/test', {
        method: 'POST',
        body: '{"key":"value"}',
        headers: {
          Authorization: 'Bearer tok'
        }
      })
    })

    it('merges custom headers with auth header', async () => {
      localStorage.setItem('access_token', 'tok')
      fetchMock.mockResolvedValue({ ok: true })

      await authFetch('/api/test', {
        headers: { 'Content-Type': 'application/json' }
      })

      expect(fetchMock).toHaveBeenCalledWith('/api/test', {
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer tok'
        }
      })
    })

    it('sends Bearer null when no token exists', async () => {
      fetchMock.mockResolvedValue({ ok: true })

      await authFetch('/api/test')

      expect(fetchMock).toHaveBeenCalledWith('/api/test', {
        headers: {
          Authorization: 'Bearer null'
        }
      })
    })
  })

  describe('saveClassification', () => {
    let saveClassification

    beforeEach(async () => {
      vi.resetModules()
      localStorage.setItem('access_token', 'test-token')
      const mod = await import('@/utils/api')
      saveClassification = mod.saveClassification
    })

    it('sends POST with correct body', async () => {
      fetchMock.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ edited: true })
      })

      await saveClassification('pointer-123', 'Confidential')

      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining('/search_engine/classification'),
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json'
          }),
          body: JSON.stringify({
            unique_pointer: 'pointer-123',
            classification: 'Confidential'
          })
        })
      )
    })

    it('returns parsed JSON on success', async () => {
      fetchMock.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ edited: true, classification: 'Public' })
      })

      const result = await saveClassification('ptr', 'Public')
      expect(result).toEqual({ edited: true, classification: 'Public' })
    })

    it('returns empty object when response has no JSON body', async () => {
      fetchMock.mockResolvedValue({
        ok: true,
        json: () => Promise.reject(new Error('no body'))
      })

      const result = await saveClassification('ptr', 'Public')
      expect(result).toEqual({})
    })

    it('throws on non-ok response', async () => {
      fetchMock.mockResolvedValue({
        ok: false,
        status: 500
      })

      await expect(saveClassification('ptr', 'Public')).rejects.toThrow('Server responded with 500')
    })

    it('throws on network error', async () => {
      fetchMock.mockRejectedValue(new Error('Network error'))

      await expect(saveClassification('ptr', 'Public')).rejects.toThrow('Network error')
    })
  })

  describe('API_PATHS', () => {
    let API_PATHS

    beforeEach(async () => {
      vi.resetModules()
      const mod = await import('@/utils/api')
      API_PATHS = mod.API_PATHS
    })

    it('has classification endpoint', () => {
      expect(API_PATHS.classification).toContain('/search_engine/classification')
    })

    it('has search endpoint', () => {
      expect(API_PATHS.search).toContain('/search_engine/search')
    })

    it('has classifications endpoint', () => {
      expect(API_PATHS.classifications).toContain('/stochastic-analyzer/classifications')
    })

    it('has rerank endpoint', () => {
      expect(API_PATHS.rerank).toContain('/stochastic-analyzer/rerank')
    })
  })
})
