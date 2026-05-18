const LOGOUT_KEY = 'logout-event'

export function broadcastLogout() {
  localStorage.setItem(LOGOUT_KEY, Date.now().toString())
}

export function isLogoutEvent(e) {
  return e.key === LOGOUT_KEY
}
