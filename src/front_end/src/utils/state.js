import { apiFetch, API_PATHS } from '@/utils/api'

export async function loadAppState() {
  const res = await apiFetch(API_PATHS.stateGet, { method: 'GET' })
  if (!res.ok) return {}
  const data = await res.json()
  return data?.state || {}
}

export async function saveAppState(state) {
  const res = await apiFetch(API_PATHS.statePut, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(state ?? {})
  })
  return res.ok
}

export async function clearAppState() {
  const res = await apiFetch(API_PATHS.stateDelete, { method: 'DELETE' })
  return res.ok
}
