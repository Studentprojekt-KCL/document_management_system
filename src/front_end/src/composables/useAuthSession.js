import { onMounted, onUnmounted } from 'vue'
import { refreshToken, logout, getAccessToken, isTokenExpired } from '@/utils/auth.js'

const LOGOUT_KEY = 'logout-event'
const REFRESH_KEY = 'refresh-event'
const REFRESH_LOCK = 'refresh-lock'

export function useAuthSession() {
  let lastActivity = Date.now()
  let lastRefresh = Date.now()
  let intervalID = null

  const TIME_LIMIT = 57 * 60 * 1000
  const REFRESH_TIME = 52 * 60 * 1000

  // Activity tracking
  const updateActivity = () => {
    lastActivity = Date.now()
  }
  // Cross-tab logout sync
  const triggerLogout = () => {
    localStorage.setItem(LOGOUT_KEY, Date.now().toString())
    logout()
  }

  const syncLogout = (event) => {
    if (event.key === LOGOUT_KEY) {
      logout()
    }
  }
  // Refresh lock (avoids multi-tab refresh)
  const acquireLock = () => {
    const now = Date.now()
    const raw = localStorage.getItem(REFRESH_LOCK)

    if (raw) {
      const lock = JSON.parse(raw)
      if (now - lock.time < 10000) return false
    }

    localStorage.setItem(REFRESH_LOCK, JSON.stringify({ time: now }))
    return true
  }

  const releaseLock = () => {
    localStorage.removeItem(REFRESH_LOCK)
  }

  // Refresh token
  const handleRefresh = async (now) => {
    if (!acquireLock()) return

    try {
      await refreshToken()
      lastRefresh = now

      localStorage.setItem(REFRESH_KEY, JSON.stringify({ time: now }))
    } catch (err) {
      console.log('Error:', err)
      triggerLogout()
    } finally {
      releaseLock()
    }
  }
  // Main loop
  const activity_loop = () => {
    intervalID = setInterval(
      async () => {
        const now = Date.now()
        const isActive = now - lastActivity < TIME_LIMIT
        const token = getAccessToken()

        if (!token) {
          triggerLogout()
          return
        }

        if (!isActive) {
          triggerLogout()
          return
        }

        // expired token → refresh
        if (isTokenExpired(token)) {
          await handleRefresh(now)
          return
        }

        // proactive refresh
        if (now - lastRefresh > REFRESH_TIME) {
          await handleRefresh(now)
        }
      },
      2 * 60 * 1000
    )
  }
  // Lifecycle
  onMounted(() => {
    window.addEventListener('mousemove', updateActivity)
    window.addEventListener('keydown', updateActivity)
    window.addEventListener('click', updateActivity)
    window.addEventListener('scroll', updateActivity)

    window.addEventListener('storage', syncLogout)

    activity_loop()
  })

  onUnmounted(() => {
    window.removeEventListener('mousemove', updateActivity)
    window.removeEventListener('keydown', updateActivity)
    window.removeEventListener('click', updateActivity)
    window.removeEventListener('scroll', updateActivity)

    window.removeEventListener('storage', syncLogout)

    clearInterval(intervalID)
  })
}
