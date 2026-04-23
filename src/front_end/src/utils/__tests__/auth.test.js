import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'

const TEST_CLIENT_ID = 'dms-frontend'

/* Helper: create a fake JWT with a given payload */
function createFakeJwt(payload) {
  const header = btoa(JSON.stringify({ alg: 'RS256', typ: 'JWT' }))
  const body = btoa(JSON.stringify(payload))
  const signature = 'fake-signature'
  return `${header}.${body}.${signature}`
}

/* Helper: store token in both storages since auth.js may use either */
function setToken(token) {
  sessionStorage.setItem('access_token', token)
  localStorage.setItem('access_token', token)
}

describe('hasRole', () => {
  let hasRole

  beforeEach(async () => {
    vi.resetModules()
    sessionStorage.clear()
    localStorage.clear()

    const authModule = await import('@/utils/auth')
    hasRole = authModule.hasRole
  })

  afterEach(() => {
    sessionStorage.clear()
    localStorage.clear()
  })

  it('returns false when no access_token in storage', () => {
    expect(hasRole('admin')).toBe(false)
  })

  it('returns false when access_token is empty string', () => {
    setToken('')
    expect(hasRole('admin')).toBe(false)
  })

  it('returns false when access_token is invalid/malformed', () => {
    setToken('not-a-jwt')
    expect(hasRole('admin')).toBe(false)
  })

  it('returns false when access_token has invalid base64', () => {
    setToken('header.!!!invalid!!!.signature')
    expect(hasRole('admin')).toBe(false)
  })

  it('returns true when role exists in client roles', () => {
    const token = createFakeJwt({
      resource_access: {
        [TEST_CLIENT_ID]: { roles: ['admin', 'user'] }
      }
    })
    setToken(token)
    expect(hasRole('admin')).toBe(true)
  })

  it('returns false when role is missing from client roles', () => {
    const token = createFakeJwt({
      resource_access: {
        [TEST_CLIENT_ID]: { roles: ['user'] }
      }
    })
    setToken(token)
    expect(hasRole('admin')).toBe(false)
  })

  it('returns false when client has no roles array', () => {
    const token = createFakeJwt({
      resource_access: {
        [TEST_CLIENT_ID]: {}
      }
    })
    setToken(token)
    expect(hasRole('admin')).toBe(false)
  })

  it('returns false when resource_access has different client ID', () => {
    const token = createFakeJwt({
      resource_access: {
        'other-client': { roles: ['admin'] }
      }
    })
    setToken(token)
    expect(hasRole('admin')).toBe(false)
  })

  it('returns true when role exists in realm roles', () => {
    const token = createFakeJwt({
      realm_access: { roles: ['admin'] }
    })
    setToken(token)
    expect(hasRole('admin')).toBe(true)
  })

  it('returns false when role is missing from realm roles', () => {
    const token = createFakeJwt({
      realm_access: { roles: ['user'] }
    })
    setToken(token)
    expect(hasRole('admin')).toBe(false)
  })

  it('returns true when role is in realm but not client roles', () => {
    const token = createFakeJwt({
      resource_access: {
        [TEST_CLIENT_ID]: { roles: ['user'] }
      },
      realm_access: { roles: ['admin'] }
    })
    setToken(token)
    expect(hasRole('admin')).toBe(true)
  })

  it('returns true when role is in client but not realm roles', () => {
    const token = createFakeJwt({
      resource_access: {
        [TEST_CLIENT_ID]: { roles: ['admin'] }
      },
      realm_access: { roles: ['user'] }
    })
    setToken(token)
    expect(hasRole('admin')).toBe(true)
  })

  it('returns false when role is in neither client nor realm roles', () => {
    const token = createFakeJwt({
      resource_access: {
        [TEST_CLIENT_ID]: { roles: ['user'] }
      },
      realm_access: { roles: ['user'] }
    })
    setToken(token)
    expect(hasRole('admin')).toBe(false)
  })

  it('handles missing resource_access entirely', () => {
    const token = createFakeJwt({
      realm_access: { roles: ['admin'] }
    })
    setToken(token)
    expect(hasRole('admin')).toBe(true)
  })

  it('handles missing realm_access entirely', () => {
    const token = createFakeJwt({
      resource_access: {
        [TEST_CLIENT_ID]: { roles: ['admin'] }
      }
    })
    setToken(token)
    expect(hasRole('admin')).toBe(true)
  })

  it('handles completely empty payload', () => {
    const token = createFakeJwt({})
    setToken(token)
    expect(hasRole('admin')).toBe(false)
  })

  it('is case-sensitive for role names', () => {
    const token = createFakeJwt({
      realm_access: { roles: ['Admin'] }
    })
    setToken(token)
    expect(hasRole('admin')).toBe(false)
    expect(hasRole('Admin')).toBe(true)
  })

  it('checks "user" role correctly', () => {
    const token = createFakeJwt({
      resource_access: {
        [TEST_CLIENT_ID]: { roles: ['user'] }
      }
    })
    setToken(token)
    expect(hasRole('user')).toBe(true)
    expect(hasRole('admin')).toBe(false)
  })
})

describe('isLoggedIn', () => {
  let isLoggedIn

  beforeEach(async () => {
    vi.resetModules()
    sessionStorage.clear()
    localStorage.clear()

    const authModule = await import('@/utils/auth')
    isLoggedIn = authModule.isLoggedIn
  })

  afterEach(() => {
    sessionStorage.clear()
    localStorage.clear()
  })

  it('returns false when no token', () => {
    expect(isLoggedIn()).toBe(false)
  })

  it('returns true when token exists', () => {
    setToken('some-token')
    expect(isLoggedIn()).toBe(true)
  })

  it('returns false when token is empty string', () => {
    setToken('')
    expect(isLoggedIn()).toBe(false)
  })
})
