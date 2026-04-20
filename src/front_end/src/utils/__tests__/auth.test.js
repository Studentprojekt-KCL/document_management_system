import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'

/* ── Setup: mock window.__ENV__ before importing auth ── */
const TEST_CLIENT_ID = 'dms-frontend'

// Must set window.__ENV__ before auth.js is imported (it reads CLIENT_ID at module level)
beforeEach(() => {
  window.__ENV__ = { KEYCLOAK_CLIENT_ID: TEST_CLIENT_ID }
})

/* Helper: create a fake JWT with a given payload */
function createFakeJwt(payload) {
  const header = btoa(JSON.stringify({ alg: 'RS256', typ: 'JWT' }))
  const body = btoa(JSON.stringify(payload))
  const signature = 'fake-signature'
  return `${header}.${body}.${signature}`
}

describe('hasRole', () => {
  let hasRole

  beforeEach(async () => {
    // Clear module cache so auth.js re-reads window.__ENV__
    vi.resetModules()
    sessionStorage.clear()

    const authModule = await import('../auth')
    hasRole = authModule.hasRole
  })

  afterEach(() => {
    sessionStorage.clear()
  })

  /* ── No token scenarios ── */
  it('returns false when no access_token in sessionStorage', () => {
    expect(hasRole('admin')).toBe(false)
  })

  it('returns false when access_token is empty string', () => {
    sessionStorage.setItem('access_token', '')
    expect(hasRole('admin')).toBe(false)
  })

  it('returns false when access_token is invalid/malformed', () => {
    sessionStorage.setItem('access_token', 'not-a-jwt')
    expect(hasRole('admin')).toBe(false)
  })

  it('returns false when access_token has invalid base64', () => {
    sessionStorage.setItem('access_token', 'header.!!!invalid!!!.signature')
    expect(hasRole('admin')).toBe(false)
  })

  /* ── Client roles ── */
  it('returns true when role exists in client roles', () => {
    const token = createFakeJwt({
      resource_access: {
        [TEST_CLIENT_ID]: { roles: ['admin', 'user'] }
      }
    })
    sessionStorage.setItem('access_token', token)
    expect(hasRole('admin')).toBe(true)
  })

  it('returns false when role is missing from client roles', () => {
    const token = createFakeJwt({
      resource_access: {
        [TEST_CLIENT_ID]: { roles: ['user'] }
      }
    })
    sessionStorage.setItem('access_token', token)
    expect(hasRole('admin')).toBe(false)
  })

  it('returns false when client has no roles array', () => {
    const token = createFakeJwt({
      resource_access: {
        [TEST_CLIENT_ID]: {}
      }
    })
    sessionStorage.setItem('access_token', token)
    expect(hasRole('admin')).toBe(false)
  })

  it('returns false when resource_access has different client ID', () => {
    const token = createFakeJwt({
      resource_access: {
        'other-client': { roles: ['admin'] }
      }
    })
    sessionStorage.setItem('access_token', token)
    expect(hasRole('admin')).toBe(false)
  })

  /* ── Realm roles ── */
  it('returns true when role exists in realm roles', () => {
    const token = createFakeJwt({
      realm_access: { roles: ['admin'] }
    })
    sessionStorage.setItem('access_token', token)
    expect(hasRole('admin')).toBe(true)
  })

  it('returns false when role is missing from realm roles', () => {
    const token = createFakeJwt({
      realm_access: { roles: ['user'] }
    })
    sessionStorage.setItem('access_token', token)
    expect(hasRole('admin')).toBe(false)
  })

  /* ── Combined scenarios ── */
  it('returns true when role is in realm but not client roles', () => {
    const token = createFakeJwt({
      resource_access: {
        [TEST_CLIENT_ID]: { roles: ['user'] }
      },
      realm_access: { roles: ['admin'] }
    })
    sessionStorage.setItem('access_token', token)
    expect(hasRole('admin')).toBe(true)
  })

  it('returns true when role is in client but not realm roles', () => {
    const token = createFakeJwt({
      resource_access: {
        [TEST_CLIENT_ID]: { roles: ['admin'] }
      },
      realm_access: { roles: ['user'] }
    })
    sessionStorage.setItem('access_token', token)
    expect(hasRole('admin')).toBe(true)
  })

  it('returns false when role is in neither client nor realm roles', () => {
    const token = createFakeJwt({
      resource_access: {
        [TEST_CLIENT_ID]: { roles: ['user'] }
      },
      realm_access: { roles: ['user'] }
    })
    sessionStorage.setItem('access_token', token)
    expect(hasRole('admin')).toBe(false)
  })

  /* ── Missing structures ── */
  it('handles missing resource_access entirely', () => {
    const token = createFakeJwt({
      realm_access: { roles: ['admin'] }
    })
    sessionStorage.setItem('access_token', token)
    expect(hasRole('admin')).toBe(true)
  })

  it('handles missing realm_access entirely', () => {
    const token = createFakeJwt({
      resource_access: {
        [TEST_CLIENT_ID]: { roles: ['admin'] }
      }
    })
    sessionStorage.setItem('access_token', token)
    expect(hasRole('admin')).toBe(true)
  })

  it('handles completely empty payload', () => {
    const token = createFakeJwt({})
    sessionStorage.setItem('access_token', token)
    expect(hasRole('admin')).toBe(false)
  })

  /* ── Role name edge cases ── */
  it('is case-sensitive for role names', () => {
    const token = createFakeJwt({
      realm_access: { roles: ['Admin'] }
    })
    sessionStorage.setItem('access_token', token)
    expect(hasRole('admin')).toBe(false)
    expect(hasRole('Admin')).toBe(true)
  })

  it('checks "user" role correctly', () => {
    const token = createFakeJwt({
      resource_access: {
        [TEST_CLIENT_ID]: { roles: ['user'] }
      }
    })
    sessionStorage.setItem('access_token', token)
    expect(hasRole('user')).toBe(true)
    expect(hasRole('admin')).toBe(false)
  })
})
