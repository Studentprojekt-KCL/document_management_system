import { describe, it, expect, vi, beforeEach } from 'vitest'

describe('config.js', () => {
  let config

  beforeEach(async () => {
    vi.resetModules()
    config = await import('@/utils/config')
  })

  describe('Keycloak config', () => {
    it('exports FRONTEND_AD_URL from window.__ENV__', () => {
      expect(config.FRONTEND_AD_URL).toBe(window.__ENV__.FRONTEND_AD_URL)
    })

    it('exports FRONTEND_AD_REALM from window.__ENV__', () => {
      expect(config.FRONTEND_AD_REALM).toBe(window.__ENV__.FRONTEND_AD_REALM)
    })

    it('exports FRONTEND_AD_CLIENT_ID from window.__ENV__', () => {
      expect(config.FRONTEND_AD_CLIENT_ID).toBe(window.__ENV__.FRONTEND_AD_CLIENT_ID)
    })
  })

  describe('Keycloak URL builders', () => {
    it('keycloakAuthUrl returns correct auth endpoint', () => {
      const url = config.keycloakAuthUrl()
      expect(url).toContain('/realms/')
      expect(url).toContain('/protocol/openid-connect/auth')
    })

    it('keycloakLogoutUrl returns correct logout endpoint', () => {
      const url = config.keycloakLogoutUrl()
      expect(url).toContain('/realms/')
      expect(url).toContain('/protocol/openid-connect/logout')
    })
  })

  describe('storage key names', () => {
    it('exports SESSION_KEY_PKCE_VERIFIER', () => {
      expect(config.SESSION_KEY_PKCE_VERIFIER).toBe('pkce_verifier')
    })

    it('exports SESSION_KEY_OIDC_STATE', () => {
      expect(config.SESSION_KEY_OIDC_STATE).toBe('oidc_state')
    })

    it('exports LOCAL_KEY_LOGOUT_EVENT', () => {
      expect(config.LOCAL_KEY_LOGOUT_EVENT).toBe('logout-event')
    })
  })
})
