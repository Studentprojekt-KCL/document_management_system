import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

describe('authClient.js', () => {
  let fetchMock

  beforeEach(() => {
    fetchMock = vi.fn()
    global.fetch = fetchMock
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('exchangeAuthorizationCode', () => {
    let exchangeAuthorizationCode

    beforeEach(async () => {
      vi.resetModules()
      const mod = await import('@/utils/authClient')
      exchangeAuthorizationCode = mod.exchangeAuthorizationCode
    })

    it('sends POST with code and code_verifier as form data', async () => {
      fetchMock.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ token: 'abc' })
      })

      await exchangeAuthorizationCode({
        code: 'auth-code-123',
        codeVerifier: 'verifier-456'
      })

      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining('/auth/codeExchange'),
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: expect.any(URLSearchParams)
        })
      )

      const callArgs = fetchMock.mock.calls[0]
      const body = callArgs[1].body
      expect(body.get('code')).toBe('auth-code-123')
      expect(body.get('code_verifier')).toBe('verifier-456')
    })

    it('returns ok true with data on success', async () => {
      const data = { token: 'abc', refresh: 'def' }
      fetchMock.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(data)
      })

      const result = await exchangeAuthorizationCode({
        code: 'c',
        codeVerifier: 'v'
      })

      expect(result).toEqual({ ok: true, data })
    })

    it('returns ok false with status and message on non-ok response', async () => {
      fetchMock.mockResolvedValue({
        ok: false,
        status: 401,
        json: () => Promise.resolve({ message: 'Invalid code' })
      })

      const result = await exchangeAuthorizationCode({
        code: 'bad',
        codeVerifier: 'bad'
      })

      expect(result).toEqual({
        ok: false,
        status: 401,
        message: 'Invalid code'
      })
    })

    it('returns default message when response has no message', async () => {
      fetchMock.mockResolvedValue({
        ok: false,
        status: 400,
        json: () => Promise.resolve({})
      })

      const result = await exchangeAuthorizationCode({
        code: 'bad',
        codeVerifier: 'bad'
      })

      expect(result).toEqual({
        ok: false,
        status: 400,
        message: 'Code exchange failed'
      })
    })

    it('handles JSON parse failure on error response', async () => {
      fetchMock.mockResolvedValue({
        ok: false,
        status: 500,
        json: () => Promise.reject(new Error('parse error'))
      })

      const result = await exchangeAuthorizationCode({
        code: 'bad',
        codeVerifier: 'bad'
      })

      expect(result).toEqual({
        ok: false,
        status: 500,
        message: 'Code exchange failed'
      })
    })

    it('returns network error on fetch failure', async () => {
      fetchMock.mockRejectedValue(new Error('Network failure'))

      const result = await exchangeAuthorizationCode({
        code: 'c',
        codeVerifier: 'v'
      })

      expect(result).toEqual({
        ok: false,
        status: 0,
        message: expect.stringContaining('Network error')
      })
    })

    it('handles successful response with no JSON body', async () => {
      fetchMock.mockResolvedValue({
        ok: true,
        json: () => Promise.reject(new Error('no body'))
      })

      const result = await exchangeAuthorizationCode({
        code: 'c',
        codeVerifier: 'v'
      })

      expect(result).toEqual({ ok: true, data: null })
    })
  })

  describe('isAuthenticated', () => {
    let isAuthenticated

    beforeEach(async () => {
      vi.resetModules()
      const mod = await import('@/utils/authClient')
      isAuthenticated = mod.isAuthenticated
    })

    it('returns true when authenticated', async () => {
      fetchMock.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ authenticated: true })
      })

      expect(await isAuthenticated()).toBe(true)
    })

    it('returns false when not authenticated', async () => {
      fetchMock.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ authenticated: false })
      })

      expect(await isAuthenticated()).toBe(false)
    })

    it('returns false on non-ok response', async () => {
      fetchMock.mockResolvedValue({
        ok: false,
        status: 401,
        json: () => Promise.resolve({})
      })

      expect(await isAuthenticated()).toBe(false)
    })

    it('returns false on network error', async () => {
      fetchMock.mockRejectedValue(new Error('Network error'))
      expect(await isAuthenticated()).toBe(false)
    })

    it('returns false when JSON parsing fails', async () => {
      fetchMock.mockResolvedValue({
        ok: true,
        json: () => Promise.reject(new Error('parse error'))
      })

      expect(await isAuthenticated()).toBe(false)
    })

    it('calls authCheck endpoint', async () => {
      fetchMock.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ authenticated: true })
      })

      await isAuthenticated()

      expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/auth/check'), expect.objectContaining({ method: 'GET' }))
    })
  })

  describe('getCurrentUser', () => {
    let getCurrentUser

    beforeEach(async () => {
      vi.resetModules()
      const mod = await import('@/utils/authClient')
      getCurrentUser = mod.getCurrentUser
    })

    it('returns user data on success', async () => {
      const userData = {
        authenticated: true,
        user: { client_roles: ['admin'], realm_roles: [] }
      }
      fetchMock.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(userData)
      })

      expect(await getCurrentUser()).toEqual(userData)
    })

    it('returns null on non-ok response', async () => {
      fetchMock.mockResolvedValue({
        ok: false,
        status: 401,
        json: () => Promise.resolve({})
      })

      expect(await getCurrentUser()).toBeNull()
    })

    it('returns null on network error', async () => {
      fetchMock.mockRejectedValue(new Error('Network error'))
      expect(await getCurrentUser()).toBeNull()
    })

    it('calls authMe endpoint', async () => {
      fetchMock.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ authenticated: true })
      })

      await getCurrentUser()

      expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/auth/me'), expect.objectContaining({ method: 'GET' }))
    })
  })
})
