import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'

describe('refreshSession', () => {
  let refreshSession, fetchMock

  beforeEach(async () => {
    vi.resetModules()
    fetchMock = vi.fn()
    global.fetch = fetchMock
    const authModule = await import('@/utils/auth')
    refreshSession = authModule.refreshSession
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('returns true on successful refresh', async () => {
    fetchMock.mockResolvedValue({ ok: true })
    expect(await refreshSession()).toBe(true)
  })

  it('returns false on failed refresh', async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 401 })
    expect(await refreshSession()).toBe(false)
  })

  it('returns false on network error', async () => {
    fetchMock.mockRejectedValue(new Error('Network error'))
    expect(await refreshSession()).toBe(false)
  })
})

describe('logout', () => {
  let logout, fetchMock

  beforeEach(async () => {
    vi.resetModules()
    localStorage.clear()
    fetchMock = vi.fn()
    global.fetch = fetchMock
    const authModule = await import('@/utils/auth')
    logout = authModule.logout
  })

  afterEach(() => {
    vi.restoreAllMocks()
    localStorage.clear()
  })

  it('sets logout-event in localStorage', async () => {
    fetchMock.mockResolvedValue({ ok: true, json: () => Promise.resolve({}) })
    delete window.location
    window.location = { href: '' }
    await logout()
    expect(localStorage.getItem('logout-event')).not.toBeNull()
  })

  it('clears pkce_verifier and oidc_state from localStorage', async () => {
    localStorage.setItem('pkce_verifier', 'some-verifier')
    localStorage.setItem('oidc_state', 'some-state')
    fetchMock.mockResolvedValue({ ok: true, json: () => Promise.resolve({}) })
    delete window.location
    window.location = { href: '' }
    await logout()
    expect(localStorage.getItem('pkce_verifier')).toBeNull()
    expect(localStorage.getItem('oidc_state')).toBeNull()
  })

  it('redirects to logout_url when provided', async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ logout_url: 'https://sso.example.com/logout' })
    })
    delete window.location
    window.location = { href: '' }
    await logout()
    expect(window.location.href).toBe('https://sso.example.com/logout')
  })

  it('redirects to / when response has no logout_url', async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({})
    })
    delete window.location
    window.location = { href: '' }
    await logout()
    expect(window.location.href).toBe('/')
  })

  it('redirects to / when response is not ok', async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 500 })
    delete window.location
    window.location = { href: '' }
    await logout()
    expect(window.location.href).toBe('/')
  })

  it('redirects to / on network error', async () => {
    fetchMock.mockRejectedValue(new Error('Network error'))
    delete window.location
    window.location = { href: '' }
    await logout()
    expect(window.location.href).toBe('/')
  })
})
