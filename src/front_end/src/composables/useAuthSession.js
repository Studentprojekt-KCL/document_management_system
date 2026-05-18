import { onMounted, onUnmounted } from 'vue'
import { isLogoutEvent } from '@/utils/authSync.js'

export function useAuthSession() {
  const syncLogout = (e) => {
    if (isLogoutEvent(e)) {
      window.location.href = '/'
    }
  }

  onMounted(() => {
    window.addEventListener('storage', syncLogout)
  })

  onUnmounted(() => {
    window.removeEventListener('storage', syncLogout)
  })
}