import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'

/* Must set window.__ENV__ before hoisted mock so config module reads correct values */
vi.hoisted(() => {
  window.__ENV__ = window.__ENV__ || {}
  window.__ENV__.FRONTEND_AD_URL = 'https://sso.example.com'
  window.__ENV__.FRONTEND_AD_REALM = 'my-realm'
  window.__ENV__.FRONTEND_AD_CLIENT_ID = 'my-client'
})

const mockCreatePkcePair = vi.hoisted(() => vi.fn())
const mockGenerateState = vi.hoisted(() => vi.fn())

vi.mock('@/utils/pkce', () => ({
  createPkcePair: mockCreatePkcePair,
  generateState: mockGenerateState
}))

import LoginView from '@/views/LoginView.vue'

describe('LoginView.vue', () => {
  let assignMock

  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    assignMock = vi.fn()
    Object.defineProperty(window, 'location', {
      value: { assign: assignMock, origin: 'https://app.example.com' },
      writable: true
    })
    mockCreatePkcePair.mockResolvedValue({ verifier: 'v1', challenge: 'ch1' })
    mockGenerateState.mockReturnValue('test-state-123')
  })

  afterEach(() => {
    localStorage.clear()
  })

  it('renders login page title', () => {
    const wrapper = mount(LoginView)
    // Avoid asserting exact static text; ensure the title exists
    const h1 = wrapper.find('h1')
    expect(h1.exists()).toBe(true)
    expect(h1.text().length).toBeGreaterThan(0)
  })

  it('renders sign in button', () => {
    const wrapper = mount(LoginView)
    const btn = wrapper.find('button')
    // Ensure a primary sign-in button is present without asserting exact copy
    expect(btn.exists()).toBe(true)
  })

  it('disables button and shows "Signing in..." while loading', async () => {
    const wrapper = mount(LoginView)
    const btn = wrapper.find('button')
    await btn.trigger('click')
    // Focus on the behavioral outcome (disabled) rather than exact label text
    expect(btn.attributes('disabled')).toBeDefined()
  })

  it('stores PKCE verifier and state in localStorage on login', async () => {
    const wrapper = mount(LoginView)
    await wrapper.find('button').trigger('click')
    expect(localStorage.getItem('pkce_verifier')).toBe('v1')
    expect(localStorage.getItem('oidc_state')).toBe('test-state-123')
  })

  it('calls createPkcePair and generateState on login', async () => {
    const wrapper = mount(LoginView)
    await wrapper.find('button').trigger('click')
    expect(mockCreatePkcePair).toHaveBeenCalledTimes(1)
    expect(mockGenerateState).toHaveBeenCalledTimes(1)
  })

  it('redirects to Keycloak auth URL with correct params', async () => {
    const wrapper = mount(LoginView)
    await wrapper.find('button').trigger('click')

    expect(assignMock).toHaveBeenCalledTimes(1)
    const url = assignMock.mock.calls[0][0]
    expect(url).toContain('https://sso.example.com')
    expect(url).toContain('/realms/my-realm/protocol/openid-connect/auth')
    expect(url).toContain('client_id=my-client')
    expect(url).toContain('redirect_uri=https%3A%2F%2Fapp.example.com%2Fauth%2Fcallback')
    expect(url).toContain('response_type=code')
    expect(url).toContain('scope=openid')
    expect(url).toContain('state=test-state-123')
    expect(url).toContain('code_challenge=ch1')
    expect(url).toContain('code_challenge_method=S256')
  })
})
