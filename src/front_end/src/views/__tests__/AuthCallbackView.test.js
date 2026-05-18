import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'

const mockRouterReplace = vi.hoisted(() => vi.fn())
const mockRouteQuery = vi.hoisted(() => vi.fn(() => ({})))

vi.mock('vue-router', () => ({
  useRouter: () => ({ replace: mockRouterReplace }),
  useRoute: () => ({ query: mockRouteQuery() })
}))

const mockExchangeCode = vi.hoisted(() => vi.fn())
const mockIsAuthenticated = vi.hoisted(() => vi.fn())
vi.mock('@/utils/authClient', () => ({
  exchangeAuthorizationCode: mockExchangeCode,
  isAuthenticated: mockIsAuthenticated
}))

const mockLogout = vi.hoisted(() => vi.fn())
vi.mock('@/utils/auth', () => ({
  logout: mockLogout
}))

import AuthCallbackView from '@/views/AuthCallbackView.vue'

describe('AuthCallbackView.vue', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    localStorage.setItem('oidc_state', 'expected-state')
    localStorage.setItem('pkce_verifier', 'test-verifier')
    vi.clearAllMocks()
    mockExchangeCode.mockResolvedValue({ ok: true, data: {} })
    mockIsAuthenticated.mockResolvedValue(true)
  })

  afterEach(() => {
    vi.useRealTimers()
    localStorage.clear()
  })

  const mountView = () => mount(AuthCallbackView)

  it('shows error when OAuth error is in query', async () => {
    mockRouteQuery.mockReturnValue({ error: 'access_denied', error_description: 'User cancelled' })
    const wrapper = mountView()
    await nextTick()
    expect(wrapper.find('.error-message').text()).toContain('access_denied')
    expect(wrapper.find('.error-message').text()).toContain('User cancelled')
  })

  it('shows error when no authorization code', async () => {
    mockRouteQuery.mockReturnValue({})
    const wrapper = mountView()
    await nextTick()
    expect(wrapper.find('.error-message').text()).toContain('No authorization code')
  })

  it('shows error on state mismatch', async () => {
    mockRouteQuery.mockReturnValue({ code: 'test-code', state: 'wrong-state' })
    const wrapper = mountView()
    await nextTick()
    expect(wrapper.find('.error-message').text()).toContain('State mismatch')
  })

  it('shows error when PKCE verifier is missing', async () => {
    localStorage.removeItem('pkce_verifier')
    mockRouteQuery.mockReturnValue({ code: 'test-code', state: 'expected-state' })
    const wrapper = mountView()
    await nextTick()
    expect(wrapper.find('.error-message').text()).toContain('Missing PKCE verifier')
  })

  it('calls exchangeAuthorizationCode and redirects on success', async () => {
    mockRouteQuery.mockReturnValue({ code: 'valid-code', state: 'expected-state' })
    mockExchangeCode.mockResolvedValue({ ok: true, data: { token: 'abc' } })
    mockIsAuthenticated.mockResolvedValue(true)

    mountView()
    await nextTick()
    await nextTick()

    expect(mockExchangeCode).toHaveBeenCalledWith({
      code: 'valid-code',
      codeVerifier: 'test-verifier'
    })
    expect(mockIsAuthenticated).toHaveBeenCalled()
    expect(mockRouterReplace).toHaveBeenCalledWith('/search')
  })

  it('shows error when exchangeAuthorizationCode fails', async () => {
    mockRouteQuery.mockReturnValue({ code: 'bad-code', state: 'expected-state' })
    mockExchangeCode.mockResolvedValue({ ok: false, message: 'Invalid code' })

    const wrapper = mountView()
    await nextTick()
    await nextTick()

    expect(wrapper.find('.error-message').text()).toContain('Login failed: Invalid code')
  })

  it('calls logout after delay when auth check fails', async () => {
    mockRouteQuery.mockReturnValue({ code: 'valid-code', state: 'expected-state' })
    mockExchangeCode.mockResolvedValue({ ok: true, data: { token: 'abc' } })
    mockIsAuthenticated.mockResolvedValue(false)

    mountView()
    await nextTick()
    await nextTick()

    expect(mockLogout).not.toHaveBeenCalled()
    vi.advanceTimersByTime(3000)
    expect(mockLogout).toHaveBeenCalledTimes(1)
  })
})
