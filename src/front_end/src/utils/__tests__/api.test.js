import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

describe('api.js', () => {
  let fetchMock

  beforeEach(() => {
    fetchMock = vi.fn()
    global.fetch = fetchMock
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('apiFetch', () => {
    let apiFetch

    beforeEach(async () => {
      vi.resetModules()
      const mod = await import('@/utils/api')
      apiFetch = mod.apiFetch
    })

    it('calls fetch with credentials include', async () => {
      fetchMock.mockResolvedValue({ ok: true })
      await apiFetch('/api/test')
      expect(fetchMock).toHaveBeenCalledWith('/api/test', {
        credentials: 'include',
        headers: {}
      })
    })

    it('passes through additional options', async () => {
      fetchMock.mockResolvedValue({ ok: true })
      await apiFetch('/api/test', { method: 'POST', body: 'data' })
      expect(fetchMock).toHaveBeenCalledWith('/api/test', {
        credentials: 'include',
        method: 'POST',
        body: 'data',
        headers: {}
      })
    })

    it('merges custom headers', async () => {
      fetchMock.mockResolvedValue({ ok: true })
      await apiFetch('/api/test', {
        headers: { 'Content-Type': 'application/json' }
      })
      expect(fetchMock).toHaveBeenCalledWith('/api/test', {
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' }
      })
    })

    it('returns the fetch response', async () => {
      const response = { ok: true, status: 200 }
      fetchMock.mockResolvedValue(response)
      const result = await apiFetch('/api/test')
      expect(result).toBe(response)
    })
  })

  describe('authFetch', () => {
    it('is the same function as apiFetch', async () => {
      vi.resetModules()
      const mod = await import('@/utils/api')
      expect(mod.authFetch).toBe(mod.apiFetch)
    })
  })

  describe('API_PATHS', () => {
    let API_PATHS

    beforeEach(async () => {
      vi.resetModules()
      const mod = await import('@/utils/api')
      API_PATHS = mod.API_PATHS
    })

    it('has search endpoint', () => {
      expect(API_PATHS.search).toContain('/search_engine/search')
    })

    it('has classifications endpoint', () => {
      expect(API_PATHS.classifications).toContain('/search_engine/classifications')
    })

    it('has classification endpoint', () => {
      expect(API_PATHS.classification).toContain('/search_engine/classification')
    })

    it('has rerank endpoint', () => {
      expect(API_PATHS.rerank).toContain('/search_engine/find_matching')
    })

    it('has summarize endpoint', () => {
      expect(API_PATHS.summarize).toContain('/stochastic-analyzer/summarize')
    })

    it('has authCheck endpoint', () => {
      expect(API_PATHS.authCheck).toContain('/auth/check')
    })

    it('has authMe endpoint', () => {
      expect(API_PATHS.authMe).toContain('/auth/me')
    })

    it('has authRefresh endpoint', () => {
      expect(API_PATHS.authRefresh).toContain('/auth/refresh')
    })

    it('has authLogout endpoint', () => {
      expect(API_PATHS.authLogout).toContain('/auth/logout')
    })

    it('has codeExchange endpoint', () => {
      expect(API_PATHS.codeExchange).toContain('/auth/codeExchange')
    })
  })
})
