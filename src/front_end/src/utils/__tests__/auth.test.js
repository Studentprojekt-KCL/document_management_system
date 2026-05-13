import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'

vi.mock('@/utils/authClient', () => ({
  getCurrentUser: vi.fn()
}))

describe('hasRole', () => {
  let hasRole, getCurrentUser

  beforeEach(async () => {
    vi.resetModules()
    const authModule = await import('@/utils/auth')
    const authClientModule = await import('@/utils/authClient')
    hasRole = authModule.hasRole
    getCurrentUser = authClientModule.getCurrentUser
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('returns false when getCurrentUser returns null', async () => {
    getCurrentUser.mockResolvedValue(null)
    expect(await hasRole('admin')).toBe(false)
  })

  it('returns false when not authenticated', async () => {
    getCurrentUser.mockResolvedValue({ authenticated: false })
    expect(await hasRole('admin')).toBe(false)
  })

  it('returns true when role exists in client roles', async () => {
    getCurrentUser.mockResolvedValue({
      authenticated: true,
      user: { client_roles: ['admin', 'user'], realm_roles: [] }
    })
    expect(await hasRole('admin')).toBe(true)
  })

  it('returns false when role is missing from client roles', async () => {
    getCurrentUser.mockResolvedValue({
      authenticated: true,
      user: { client_roles: ['user'], realm_roles: [] }
    })
    expect(await hasRole('admin')).toBe(false)
  })

  it('returns true when role exists in realm roles', async () => {
    getCurrentUser.mockResolvedValue({
      authenticated: true,
      user: { client_roles: [], realm_roles: ['admin'] }
    })
    expect(await hasRole('admin')).toBe(true)
  })

  it('returns false when role is missing from both client and realm roles', async () => {
    getCurrentUser.mockResolvedValue({
      authenticated: true,
      user: { client_roles: ['user'], realm_roles: ['user'] }
    })
    expect(await hasRole('admin')).toBe(false)
  })

  it('returns true when role is in realm but not client roles', async () => {
    getCurrentUser.mockResolvedValue({
      authenticated: true,
      user: { client_roles: ['user'], realm_roles: ['admin'] }
    })
    expect(await hasRole('admin')).toBe(true)
  })

  it('returns true when role is in client but not realm roles', async () => {
    getCurrentUser.mockResolvedValue({
      authenticated: true,
      user: { client_roles: ['admin'], realm_roles: ['user'] }
    })
    expect(await hasRole('admin')).toBe(true)
  })

  it('handles missing client_roles and realm_roles', async () => {
    getCurrentUser.mockResolvedValue({
      authenticated: true,
      user: {}
    })
    expect(await hasRole('admin')).toBe(false)
  })

  it('is case-sensitive for role names', async () => {
    getCurrentUser.mockResolvedValue({
      authenticated: true,
      user: { client_roles: ['Admin'], realm_roles: [] }
    })
    expect(await hasRole('admin')).toBe(false)
    expect(await hasRole('Admin')).toBe(true)
  })
})

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
