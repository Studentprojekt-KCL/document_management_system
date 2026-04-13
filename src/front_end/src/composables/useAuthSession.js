import { onMounted, onUnmounted } from 'vue'
import router from '@/router'
import { refreshToken, logout, getAccessToken, isTokenExpired } from '@/utils/auth.js'

export function useAuthSession() {
  let lastActivity = Date.now()
  let lastRefresh = Date.now()
  let intervalID = null

  // configuration
  const TIME_LIMIT = 28 * 60 * 1000 //28 minutes idle logout
  const REFRESH_TIME = 25 * 60 * 1000 // 25 minutes refresh early (safe buffer)

  // update functions for lastActivity
  const updateActivity = () => {
    lastActivity = Date.now()
  }
  const triggerLogout = () => {
    logout()
  }
  // Synchronize logout across multiple tabs for storage events.
  const syncLogout = (event) => {
    if (event.key === 'logout-event') {
      sessionStorage.clear()
      router.push('/')
    }
  }

  const activity_loop = () => {
    intervalID = setInterval(
      async () => {
        const now = Date.now()
        const isActive = now - lastActivity < TIME_LIMIT

        if (!isActive) {
          console.log('inactive -> logging out')
          triggerLogout()
          return
        }
        const token = getAccessToken()

        if (!token) {
          console.log('no token')
          triggerLogout()
          return
        }

        try {
          if (isTokenExpired(token)) {
            await refreshToken()
            lastRefresh = now
            return
          }

          const shouldRefresh = now - lastRefresh > REFRESH_TIME
          if (shouldRefresh) {
            console.log('active- should refresh...')
            await refreshToken()
            lastRefresh = now
          }
        } catch (err) {
          console.error('refresh failed:', err)
        }
      },
      2 * 60 * 1000
    ) // 1 minute check
  }
  // life cycle
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
