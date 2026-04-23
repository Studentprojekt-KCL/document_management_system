import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent } from 'vue'

/* Mock auth.js */
const mockRefreshToken = vi.hoisted(() => vi.fn())
const mockLogout = vi.hoisted(() => vi.fn())
const mockGetAccessToken = vi.hoisted(() => vi.fn())
const mockIsTokenExpired = vi.hoisted(() => vi.fn())

vi.mock('@/utils/auth.js', () => ({
  refreshToken: mockRefreshToken,
  logout: mockLogout,
  getAccessToken: mockGetAccessToken,
  isTokenExpired: mockIsTokenExpired
}))

/* Mock authSync.js */
const mockTryBecomeLeader = vi.hoisted(() => vi.fn())
const mockIsLeader = vi.hoisted(() => vi.fn())
const mockSetLeader = vi.hoisted(() => vi.fn())
const mockBroadcastActivity = vi.hoisted(() => vi.fn())
const mockGetLastActivity = vi.hoisted(() => vi.fn())
const mockBroadcastLogout = vi.hoisted(() => vi.fn())

vi.mock('@/utils/authSync.js', () => ({
  tryBecomeLeader: mockTryBecomeLeader,
  isLeader: mockIsLeader,
  setLeader: mockSetLeader,
  broadcastActivity: mockBroadcastActivity,
  getLastActivity: mockGetLastActivity,
  broadcastLogout: mockBroadcastLogout
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
    vi.useFakeTimers()
    localStorage.clear()

    mockTryBecomeLeader.mockReturnValue(false)
    mockIsLeader.mockReturnValue(false)
    mockGetAccessToken.mockReturnValue('valid-token')
    mockIsTokenExpired.mockReturnValue(false)
    mockGetLastActivity.mockReturnValue(Date.now())
    mockRefreshToken.mockResolvedValue(undefined)
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
    localStorage.clear()
  })

  describe('initialization', () => {
    it('attempts to become leader on mount', () => {
      mountWithSession()
      expect(mockTryBecomeLeader).toHaveBeenCalled()
    })

    it('sets leader when becoming leader', () => {
      mockTryBecomeLeader.mockReturnValue(true)
      mountWithSession()
      expect(mockSetLeader).toHaveBeenCalled()
    })

    it('does not set leader when another tab is leader', () => {
      mockTryBecomeLeader.mockReturnValue(false)
      mountWithSession()
      expect(mockSetLeader).not.toHaveBeenCalled()
    })
  })

  describe('activity tracking', () => {
    it('registers activity event listeners on mount', () => {
      const addSpy = vi.spyOn(window, 'addEventListener')
      mountWithSession()
      const eventTypes = addSpy.mock.calls.map((call) => call[0])
      expect(eventTypes).toContain('mousemove')
      expect(eventTypes).toContain('keydown')
      expect(eventTypes).toContain('click')
      expect(eventTypes).toContain('scroll')
    })

    it('broadcasts activity on user interaction', () => {
      mountWithSession()
      window.dispatchEvent(new Event('mousemove'))
      expect(mockBroadcastActivity).toHaveBeenCalled()
    })

    it('registers storage listener for logout sync', () => {
      const addSpy = vi.spyOn(window, 'addEventListener')
      mountWithSession()
      const eventTypes = addSpy.mock.calls.map((call) => call[0])
      expect(eventTypes).toContain('storage')
    })
  })

  describe('cleanup', () => {
    it('removes event listeners on unmount', () => {
      const removeSpy = vi.spyOn(window, 'removeEventListener')
      const wrapper = mountWithSession()
      wrapper.unmount()
      const eventTypes = removeSpy.mock.calls.map((call) => call[0])
      expect(eventTypes).toContain('mousemove')
      expect(eventTypes).toContain('keydown')
      expect(eventTypes).toContain('click')
      expect(eventTypes).toContain('scroll')
      expect(eventTypes).toContain('storage')
    })
  })

  describe('watchdog', () => {
    it('tries to become leader when current leader is dead', () => {
      mockTryBecomeLeader.mockReturnValue(false)
      mountWithSession()

      localStorage.setItem('auth-leader', JSON.stringify({ id: 'dead-tab', ts: Date.now() - 20000 }))
      mockTryBecomeLeader.mockReturnValue(true)
      vi.advanceTimersByTime(3000)

      expect(mockTryBecomeLeader).toHaveBeenCalledTimes(2)
    })

    it('does not try to become leader when current leader is alive', () => {
      mockTryBecomeLeader.mockReturnValue(false)
      mountWithSession()

      localStorage.setItem('auth-leader', JSON.stringify({ id: 'active-tab', ts: Date.now() }))
      vi.advanceTimersByTime(3000)

      expect(mockTryBecomeLeader).toHaveBeenCalledTimes(1)
    })
  })

  describe('leader loop', () => {
    it('refreshes token when expired and user is active', async () => {
      mockTryBecomeLeader.mockReturnValue(true)
      mockIsLeader.mockReturnValue(true)
      mockIsTokenExpired.mockReturnValue(true)
      mockGetLastActivity.mockReturnValue(Date.now())

      mountWithSession()
      await vi.advanceTimersByTimeAsync(5000)

      expect(mockRefreshToken).toHaveBeenCalled()
    })

    it('logs out when user is inactive', async () => {
      mockTryBecomeLeader.mockReturnValue(true)
      mockIsLeader.mockReturnValue(true)
      mockGetLastActivity.mockReturnValue(Date.now() - 2 * 60 * 60 * 1000)

      mountWithSession()
      await vi.advanceTimersByTimeAsync(5000)

      expect(mockBroadcastLogout).toHaveBeenCalled()
      expect(mockLogout).toHaveBeenCalled()
    })

    it('does nothing when not leader', async () => {
      mockTryBecomeLeader.mockReturnValue(true)
      mockIsLeader.mockReturnValue(false)

      mountWithSession()
      await vi.advanceTimersByTimeAsync(5000)

      expect(mockRefreshToken).not.toHaveBeenCalled()
      expect(mockLogout).not.toHaveBeenCalled()
    })

    it('does nothing when no token exists', async () => {
      mockTryBecomeLeader.mockReturnValue(true)
      mockIsLeader.mockReturnValue(true)
      mockGetAccessToken.mockReturnValue(null)

      mountWithSession()
      await vi.advanceTimersByTimeAsync(5000)

      expect(mockRefreshToken).not.toHaveBeenCalled()
    })

    it('logs out when refresh fails', async () => {
      mockTryBecomeLeader.mockReturnValue(true)
      mockIsLeader.mockReturnValue(true)
      mockIsTokenExpired.mockReturnValue(true)
      mockGetLastActivity.mockReturnValue(Date.now())
      mockRefreshToken.mockRejectedValue(new Error('refresh failed'))

      mountWithSession()
      await vi.advanceTimersByTimeAsync(5000)

      expect(mockBroadcastLogout).toHaveBeenCalled()
      expect(mockLogout).toHaveBeenCalled()
    })

    it('proactively refreshes token before expiry', async () => {
      mockTryBecomeLeader.mockReturnValue(true)
      mockIsLeader.mockReturnValue(true)
      mockIsTokenExpired.mockReturnValue(false)
      mockGetLastActivity.mockReturnValue(Date.now())

      mountWithSession()
      await vi.advanceTimersByTimeAsync(26 * 60 * 1000)

      expect(mockRefreshToken).toHaveBeenCalled()
    })
  })

  describe('logout sync', () => {
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
})
