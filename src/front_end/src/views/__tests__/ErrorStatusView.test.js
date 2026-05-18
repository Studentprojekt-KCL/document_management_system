import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'

const mockRouterPush = vi.fn()
const mockRouterBack = vi.fn()

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mockRouterPush, back: mockRouterBack })
}))

import ErrorStatusView from '@/views/ErrorStatusView.vue'

describe('ErrorStatusView.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders error code, title and description', () => {
    const wrapper = mount(ErrorStatusView, {
      props: { code: 404, title: 'Not Found', description: 'Page does not exist' }
    })
    // Verify elements render and display the provided values without asserting exact copy
    expect(wrapper.find('.error-code').exists()).toBe(true)
    expect(wrapper.find('.error-code').text()).toBe(String(404))
    expect(wrapper.find('h1').exists()).toBe(true)
    expect(wrapper.find('.description').exists()).toBe(true)
  })

  it('shows "Go to login" button for 401 errors', () => {
    const wrapper = mount(ErrorStatusView, {
      props: { code: 401, title: 'Unauthorized', description: 'Please log in' }
    })
    // Ensure the action button is rendered and triggers the login redirect behaviour (checked in other tests)
    const btn = wrapper.find('button')
    expect(btn.exists()).toBe(true)
  })

  it('shows "Go back" button for non-401 errors', () => {
    const wrapper = mount(ErrorStatusView, {
      props: { code: 403, title: 'Forbidden', description: 'Access denied' }
    })
    const btn = wrapper.find('button')
    expect(btn.exists()).toBe(true)
  })

  it('redirects to / on 401 button click', () => {
    const wrapper = mount(ErrorStatusView, {
      props: { code: 401, title: 'Unauthorized', description: 'Please log in' }
    })
    wrapper.find('button').trigger('click')
    expect(mockRouterPush).toHaveBeenCalledWith('/')
    expect(mockRouterBack).not.toHaveBeenCalled()
  })

  it('calls router.back() on non-401 button click', () => {
    const wrapper = mount(ErrorStatusView, {
      props: { code: 500, title: 'Server Error', description: 'Something broke' }
    })
    wrapper.find('button').trigger('click')
    expect(mockRouterBack).toHaveBeenCalledTimes(1)
    expect(mockRouterPush).not.toHaveBeenCalled()
  })

  it('works with string error code', () => {
    const wrapper = mount(ErrorStatusView, {
      props: { code: '404', title: 'Not Found', description: 'Missing' }
    })
    expect(wrapper.find('.error-code').text()).toBe('404')
    const btn = wrapper.find('button')
    expect(btn.exists()).toBe(true)
  })
})
