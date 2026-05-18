/* useAuthSession Tests */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent } from 'vue'

/* Mock auth.js */
const mockRefreshSession = vi.hoisted(() => vi.fn())
const mockLogout = vi.hoisted(() => vi.fn())

vi.mock('@/utils/auth.js', () => ({
  refreshSession: mockRefreshSession,
  logout: mockLogout
}))

/* Mock authClient.js */
const mockIsAuthenticated = vi.hoisted(() => vi.fn())
vi.mock('@/utils/authClient.js', () => ({
  isAuthenticated: mockIsAuthenticated
}))

/* Mock authSync.js */
const mockTryBecomeLeader = vi.hoisted(() => vi.fn())
const mockIsLeader = vi.hoisted(() => vi.fn())
const mockSetLeader = vi.hoisted(() => vi.fn())
const mockBroadcastActivity = vi.hoisted(() => vi.fn())
const mockGetLastActivity = vi.hoisted(() => vi.fn())
const mockBroadcastLogout = vi.hoisted(() => vi.fn())
const mockIsLogoutEvent = vi.hoisted(() => vi.fn((e) => e.key === 'logout-event'))

vi.mock('@/utils/authSync.js', () => ({
  tryBecomeLeader: mockTryBecomeLeader,
  isLeader: mockIsLeader,
  setLeader: mockSetLeader,
  broadcastActivity: mockBroadcastActivity,
  getLastActivity: mockGetLastActivity,
  broadcastLogout: mockBroadcastLogout,
  isLogoutEvent: mockIsLogoutEvent
}))

import { useAuthSession } from '@/composables/useAuthSession'

/* Helper: mount the composable inside a real component to trigger lifecycle hooks */
function mountWithSession() {
  const TestComponent = defineComponent({
    setup() {
      useAuthSession()
      return {}
    },
    template: '<div />'
  })

  return mount(TestComponent)
}

describe('useAuthSession', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    localStorage.clear()
  })

  describe('storage listener', () => {
    it('registers a storage listener on mount', () => {
      const addSpy = vi.spyOn(window, 'addEventListener')
      mountWithSession()
      const eventTypes = addSpy.mock.calls.map((call) => call[0])
      expect(eventTypes).toContain('storage')
    })

    it('redirects to / when logout event is detected from another tab', () => {
      const originalHref = window.location.href
      delete window.location
      window.location = { href: originalHref }

      mountWithSession()

      const event = new StorageEvent('storage', { key: 'logout-event' })
      window.dispatchEvent(event)

      expect(window.location.href).toBe('/')
      window.location = { href: originalHref }
    })

    it('ignores storage events for other keys', () => {
      const originalHref = window.location.href
      delete window.location
      window.location = { href: originalHref }

      mountWithSession()

      const event = new StorageEvent('storage', { key: 'other-key' })
      window.dispatchEvent(event)

      expect(window.location.href).toBe(originalHref)
      window.location = { href: originalHref }
    })
  })

  describe('cleanup', () => {
    it('removes the storage listener on unmount', () => {
      const removeSpy = vi.spyOn(window, 'removeEventListener')
      const wrapper = mountWithSession()
      wrapper.unmount()
      const eventTypes = removeSpy.mock.calls.map((call) => call[0])
      expect(eventTypes).toContain('storage')
    })
  })
})
