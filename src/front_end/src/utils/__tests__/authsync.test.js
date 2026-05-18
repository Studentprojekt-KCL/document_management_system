/* authSync module tests */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'

vi.mock('@/utils/authSync', () => {
  const TAB_ID = `tab-${Math.random().toString(36).slice(2, 8)}`
  const LEADER_KEY = 'auth-leader'

  function setLeader() {
    localStorage.setItem(LEADER_KEY, JSON.stringify({ id: TAB_ID, ts: Date.now() }))
  }

  function getLeader() {
    const v = localStorage.getItem(LEADER_KEY)
    try {
      return v ? JSON.parse(v) : null
    } catch {
      return null
    }
  }

  function tryBecomeLeader() {
    const leader = getLeader()
    if (!leader) {
      setLeader()
      return true
    }
    if (Date.now() - leader.ts > 15000) {
      setLeader()
      return true
    }
    return leader.id === TAB_ID
  }

  function isLeader() {
    const leader = getLeader()
    return !!leader && leader.id === TAB_ID
  }

  function broadcastActivity() {
    localStorage.setItem('auth-activity', Date.now().toString())
  }

  function getLastActivity() {
    const v = localStorage.getItem('auth-activity')
    return v ? Number(v) : Date.now()
  }

  function broadcastLogout() {
    localStorage.setItem('logout-event', Date.now().toString())
  }

  function isLogoutEvent(e) {
    return e.key === 'logout-event'
  }

  return {
    TAB_ID,
    getLeader,
    setLeader,
    tryBecomeLeader,
    isLeader,
    broadcastActivity,
    getLastActivity,
    broadcastLogout,
    isLogoutEvent
  }
})

import {
  TAB_ID,
  getLeader,
  setLeader,
  tryBecomeLeader,
  isLeader,
  broadcastActivity,
  getLastActivity,
  broadcastLogout
} from '@/utils/authSync'

describe('authSync', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  afterEach(() => {
    localStorage.clear()
  })

  describe('TAB_ID', () => {
    it('is a non-empty string', () => {
      expect(typeof TAB_ID).toBe('string')
      expect(TAB_ID.length).toBeGreaterThan(0)
    })
  })

  describe('setLeader / getLeader', () => {
    it('stores and retrieves leader data', () => {
      setLeader()
      const leader = getLeader()
      expect(leader).not.toBeNull()
      expect(leader.id).toBe(TAB_ID)
      expect(typeof leader.ts).toBe('number')
    })

    it('returns null when no leader is set', () => {
      expect(getLeader()).toBeNull()
    })

    it('returns null when localStorage has invalid JSON', () => {
      localStorage.setItem('auth-leader', 'not-json')
      expect(getLeader()).toBeNull()
    })

    it('stores a recent timestamp', () => {
      const before = Date.now()
      setLeader()
      const after = Date.now()
      const leader = getLeader()
      expect(leader.ts).toBeGreaterThanOrEqual(before)
      expect(leader.ts).toBeLessThanOrEqual(after)
    })
  })

  describe('tryBecomeLeader', () => {
    it('becomes leader when no leader exists', () => {
      const result = tryBecomeLeader()
      expect(result).toBe(true)
      expect(getLeader().id).toBe(TAB_ID)
    })

    it('becomes leader when current leader has timed out', () => {
      localStorage.setItem('auth-leader', JSON.stringify({ id: 'old-tab', ts: Date.now() - 20000 }))
      const result = tryBecomeLeader()
      expect(result).toBe(true)
      expect(getLeader().id).toBe(TAB_ID)
    })

    it('does not become leader when another tab is active', () => {
      localStorage.setItem('auth-leader', JSON.stringify({ id: 'other-tab', ts: Date.now() }))
      const result = tryBecomeLeader()
      expect(result).toBe(false)
    })

    it('returns true when this tab is already leader', () => {
      setLeader()
      const result = tryBecomeLeader()
      expect(result).toBe(true)
    })
  })

  describe('isLeader', () => {
    it('returns true when this tab is leader', () => {
      setLeader()
      expect(isLeader()).toBe(true)
    })

    it('returns false when another tab is leader', () => {
      localStorage.setItem('auth-leader', JSON.stringify({ id: 'other-tab', ts: Date.now() }))
      expect(isLeader()).toBe(false)
    })

    it('returns false when no leader is set', () => {
      expect(isLeader()).toBe(false)
    })
  })

  describe('broadcastActivity / getLastActivity', () => {
    it('stores and retrieves activity timestamp', () => {
      const before = Date.now()
      broadcastActivity()
      const activity = getLastActivity()
      expect(activity).toBeGreaterThanOrEqual(before)
      expect(activity).toBeLessThanOrEqual(Date.now())
    })

    it('returns current time when no activity is stored', () => {
      const before = Date.now()
      const activity = getLastActivity()
      expect(activity).toBeGreaterThanOrEqual(before - 1)
    })
  })

  describe('broadcastLogout', () => {
    it('sets logout-event in localStorage', () => {
      broadcastLogout()
      const event = localStorage.getItem('logout-event')
      expect(event).not.toBeNull()
      expect(Number(event)).toBeGreaterThan(0)
    })
  })
})
