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
    expect(wrapper.find('.error-code').text()).toBe('404')
    expect(wrapper.find('h1').text()).toBe('Not Found')
    expect(wrapper.find('.description').text()).toBe('Page does not exist')
  })

  it('shows "Go to login" button for 401 errors', () => {
    const wrapper = mount(ErrorStatusView, {
      props: { code: 401, title: 'Unauthorized', description: 'Please log in' }
    })
    const btn = wrapper.find('button')
    expect(btn.text()).toBe('Go to login')
  })

  it('shows "Go back" button for non-401 errors', () => {
    const wrapper = mount(ErrorStatusView, {
      props: { code: 403, title: 'Forbidden', description: 'Access denied' }
    })
    const btn = wrapper.find('button')
    expect(btn.text()).toBe('Go back to previous page')
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
    expect(btn.text()).toBe('Go back to previous page')
  })
})
