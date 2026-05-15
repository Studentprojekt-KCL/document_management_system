import { onMounted, onUnmounted } from 'vue'
import { refreshSession, logout } from '@/utils/auth.js'
import { tryBecomeLeader, isLeader, setLeader, broadcastActivity, getLastActivity, broadcastLogout } from '@/utils/authSync.js'

export function useAuthSession() {
  let leaderLoop = null
  let watchdogLoop = null
  let heartbeatLoop = null

  /**
   30 min
   4 min
   15s 
   */
  const IDLE_TIMEOUT = 30 * 60 * 1000
  const REFRESH_INTERVAL = 4 * 60 * 1000
  const LEADER_TIMEOUT = 15000

  // ACTIVITY (ALL TABS)
  const updateActivity = () => {
    broadcastActivity()
  }

  // LOGOUT
  const triggerLogout = async (reason = 'unknown') => {
    console.log('Logout triggered: ', reason)
    console.trace()
    broadcastLogout()
    await logout()
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
      const lastActivity = getLastActivity()
      const isActive = now - lastActivity < IDLE_TIMEOUT

      // inactivity logout
      if (!isActive) {
        await triggerLogout('inactive')
        return
      }

      const refreshed = await refreshSession()
      if (!refreshed) {
        await triggerLogout('refresh-failed')
        return
      }
    }, REFRESH_INTERVAL)
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

  onMounted(() => {
    window.addEventListener('mousemove', updateActivity)
    window.addEventListener('keydown', updateActivity)
    window.addEventListener('click', updateActivity)
    window.addEventListener('scroll', updateActivity)
    window.addEventListener('storage', syncLogout)

    broadcastActivity()

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
