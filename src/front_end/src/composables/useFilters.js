/**
 * Composable functions for fetching and managing filter options used in the search interface.
 * This includes source system filters and security classification filters.
 * Centralized here to keep API logic separate from component code and allow reuse across components if needed.
 */
import { ref } from 'vue'
import { authFetch, API_PATHS } from '@/utils/api'

/**
 * Fetches the available connected source systems.
 *
 * @returns {Ref<string[]>}
 */
export function useSourceFilters() {
  const sourceFilters = ref([])

  authFetch(API_PATHS.connectedSourceSystems)
    .then((res) => {
      if (!res.ok) {
        console.error(`Failed to fetch source systems: ${res.statusText}`)
        return
      }
      return res.json()
    })
    .then((data) => {
      if (data) sourceFilters.value = data
    })
    .catch((error) => console.error(`Error fetching source systems: ${error}`))

  return sourceFilters
}

/**
 * Fetches the available security classifications.
 *
 * @returns {Ref<string[]>}
 */
export function useSecurityFilters() {
  const securityFilters = ref([])

  authFetch(API_PATHS.classifications)
    .then((res) => {
      if (!res.ok) {
        console.error(`Failed to fetch security classifications: ${res.statusText}`)
        return
      }
      return res.json()
    })
    .then((data) => {
      if (data) securityFilters.value = data
    })
    .catch((error) => console.error(`Error fetching security classifications: ${error}`))

  return securityFilters
}
