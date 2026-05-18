import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'

const mockRouterReplace = vi.hoisted(() => vi.fn())
const mockRouterPush = vi.hoisted(() => vi.fn())
const mockRouteQuery = vi.hoisted(() => vi.fn(() => ({})))

vi.mock('vue-router', () => ({
  useRouter: () => ({ replace: mockRouterReplace, push: mockRouterPush }),
  useRoute: () => ({ query: mockRouteQuery() })
}))

const mockApiFetch = vi.hoisted(() => vi.fn())
vi.mock('@/utils/api', () => ({
  apiFetch: mockApiFetch,
  API_PATHS: { sessionCallback: '/api/connector/session/callback' }
}))

import SessionCallbackView from '@/views/SessionCallbackView.vue'

describe('SessionCallbackView.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows "Signing in..." text', () => {
    mockRouteQuery.mockReturnValue({ code: 'c', state: 's' })
    mockApiFetch.mockResolvedValue({ ok: true })
    const wrapper = mount(SessionCallbackView)
    // Check that the view indicates a signing-in state without depending on exact copy
    expect(wrapper.text().toLowerCase()).toContain('sign')
  })

  it('redirects to /login when code or state is missing', async () => {
    mockRouteQuery.mockReturnValue({})
    mount(SessionCallbackView)
    await nextTick()
    expect(mockRouterPush).toHaveBeenCalledWith('/login')
    expect(mockApiFetch).not.toHaveBeenCalled()
  })

  it('calls apiFetch with code and state when both are present', async () => {
    mockRouteQuery.mockReturnValue({ code: 'test-code', state: 'test-state' })
    mockApiFetch.mockResolvedValue({ ok: true })

    mount(SessionCallbackView)
    await nextTick()

    expect(mockApiFetch).toHaveBeenCalledWith('/api/connector/session/callback?code=test-code&state=test-state&source=null', {
      method: 'GET'
    })
  })

  it('redirects to /connections on success', async () => {
    mockRouteQuery.mockReturnValue({ code: 'test-code', state: 'test-state' })
    mockApiFetch.mockResolvedValue({ ok: true })

    mount(SessionCallbackView)
    await nextTick()

    expect(mockRouterReplace).toHaveBeenCalledWith('/connections')
  })

  it('does not redirect when response is not ok', async () => {
    mockRouteQuery.mockReturnValue({ code: 'bad-code', state: 'bad-state' })
    mockApiFetch.mockResolvedValue({ ok: false, status: 400 })

    mount(SessionCallbackView)
    await nextTick()
    await nextTick()

    expect(mockRouterReplace).not.toHaveBeenCalled()
    expect(mockRouterPush).not.toHaveBeenCalled()
  })

  it('does not redirect on network failure', async () => {
    mockRouteQuery.mockReturnValue({ code: 'test-code', state: 'test-state' })
    mockApiFetch.mockRejectedValue(new Error('Network error'))

    mount(SessionCallbackView)
    await nextTick()
    await nextTick()

    expect(mockRouterReplace).not.toHaveBeenCalled()
    expect(mockRouterPush).not.toHaveBeenCalled()
  })
})
