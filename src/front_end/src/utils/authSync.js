export const TAB_ID = crypto.randomUUID()

const LEADER_KEY = 'auth-leader'
const ACTIVITY_KEY = 'user-activity'
const LOGOUT_KEY = 'logout-event'

const TIMEOUT = 15000

// GET the leader
export function getLeader() {
  try {
    return JSON.parse(localStorage.getItem(LEADER_KEY))
  } catch {
    return null
  }
}
// Set the leader tab
export function setLeader() {
  localStorage.setItem(
    LEADER_KEY,
    JSON.stringify({
      id: TAB_ID,
      ts: Date.now()
    })
  )
}
// TRy to become a new leader, used when a leader tab is removed.
export function tryBecomeLeader() {
  const leader = getLeader()

  if (!leader) {
    setLeader()
    return true
  }

  if (Date.now() - leader.ts > TIMEOUT) {
    setLeader()
    return true
  }

  return leader.id === TAB_ID
}
// Who is leader?
export function isLeader() {
  const leader = getLeader()
  return leader?.id === TAB_ID
}
// Activity sync of different tabs, -
// - so we don't get logged out because of activity only in another tab than leader.
export function broadcastActivity() {
  localStorage.setItem(
    ACTIVITY_KEY,
    Date.now().toString()
  )
}
export function getLastActivity() {
  return Number(localStorage.getItem(ACTIVITY_KEY) || Date.now())
}
// logout sync broadcasting
export function broadcastLogout() {
  localStorage.setItem(LOGOUT_KEY, Date.now().toString())
}