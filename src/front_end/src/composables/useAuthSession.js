import { onMounted, onUnmounted } from 'vue'
import { refreshToken, logout, getAccessToken, isTokenExpired } from '@/utils/auth.js'

import { tryBecomeLeader, isLeader, setLeader, broadcastActivity, getLastActivity, broadcastLogout } from '@/utils/authSync.js'

export function useAuthSession() {
  let leaderLoop = null
  let watchdogLoop = null
  let lastRefresh = Date.now()
  let heartbeatLoop = null

  const TIME_LIMIT = 4 * 60 * 1000
  const REFRESH_TIME = 1 * 60 * 1000
  const LEADER_TIMEOUT = 15000

  // ACTIVITY (ALL TABS)
  const updateActivity = () => {
    broadcastActivity()
  }

  // LOGOUT
  const triggerLogout = () => {
    broadcastLogout()
    logout()
  }
  // syncs logout forcing tabs to change window.
  const syncLogout = (e) => {
    if (e.key === 'logout-event') {
      stopAll()
      window.location.href = '/'
    }
  }

  // Leader loop (ONLY ONE TAB!)
  const startLeaderLoop = () => {
    if (leaderLoop) return

    leaderLoop = setInterval(async () => {
      if (!isLeader()) return

      const now = Date.now()
      const token = getAccessToken()
      const lastActivity = getLastActivity()

      const isActive = now - lastActivity < TIME_LIMIT

      if (!token) return

      // inactivity logout
      if (!isActive) {
        triggerLogout()
        return
      }

      if (isTokenExpired(token)) {
        try {
          await refreshToken()
          lastRefresh = now
        } catch {
          triggerLogout()
        }
        return
      }

      if (now - lastRefresh > REFRESH_TIME) {
        try {
          await refreshToken()
          lastRefresh = now
        } catch {
          triggerLogout()
        }
      }
    }, 5000)
  }

  // watchdog on all tabs
  // ensures leader always exists
  const startWatchdog = () => {
    if (watchdogLoop) return

    watchdogLoop = setInterval(() => {
      const leader = JSON.parse(localStorage.getItem('auth-leader') || '{}')

      const leaderDead = !leader.id || Date.now() - (leader.ts || 0) > LEADER_TIMEOUT

      if (leaderDead) {
        if (tryBecomeLeader()) {
          setLeader()
          startLeaderHeartbeat()
          startLeaderLoop()
        }
      }
    }, 3000)
  }

  // hearbeat only leader tab
  const startLeaderHeartbeat = () => {
    if (heartbeatLoop) return

    heartbeatLoop = setInterval(() => {
      if (!isLeader()) return
      setLeader()
    }, 5000)
  }

  // stops everything
  const stopAll = () => {
    if (leaderLoop) clearInterval(leaderLoop)
    if (watchdogLoop) clearInterval(watchdogLoop)
    if (heartbeatLoop) clearInterval(heartbeatLoop)

    leaderLoop = null
    watchdogLoop = null
    heartbeatLoop = null
  }

  // Cycle
  onMounted(() => {
    window.addEventListener('mousemove', updateActivity)
    window.addEventListener('keydown', updateActivity)
    window.addEventListener('click', updateActivity)
    window.addEventListener('scroll', updateActivity)

    window.addEventListener('storage', syncLogout)

    // initial leader attempt
    if (tryBecomeLeader()) {
      setLeader()
      startLeaderHeartbeat()
      startLeaderLoop()
    }

    // watchdog runs in ALL tabs
    startWatchdog()
  })

  // CLEANUP
  onUnmounted(() => {
    window.removeEventListener('mousemove', updateActivity)
    window.removeEventListener('keydown', updateActivity)
    window.removeEventListener('click', updateActivity)
    window.removeEventListener('scroll', updateActivity)
    window.removeEventListener('storage', syncLogout)

    stopAll()
  })
}
