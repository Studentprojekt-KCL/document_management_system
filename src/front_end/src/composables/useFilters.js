/**
 * Composable functions for fetching and managing filter options used in the search interface.
 * This includes source system filters and security classification filters.
 * Centralized here to keep API logic separate from component code and allow reuse across components if needed.
 */
import { ref } from 'vue'
import { authFetch, API_PATHS } from '@/utils/api'

const normalizeExtensions = (extension) => {
  if (Array.isArray(extension)) return extension.map((ext) => String(ext))
  if (typeof extension === 'string' && extension) return [extension]
  return []
}

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
 * Fetches the file types for "documents only" filter
 *
 * @returns {Ref<Array<{description: string, extension: string[], type: string}>>}
 */
export function useDocumentsOnlyFilters() {
  const documentsOnlyFilters = ref([])

  authFetch(API_PATHS.documentsOnly)
    .then((res) => {
      if (!res.ok) {
        console.error(`Failed to fetch documents only filters: ${res.statusText}`)
        return
      }
      return res.json()
    })
    .then((data) => {
      if (!Array.isArray(data)) return

      documentsOnlyFilters.value = data
        .map((item) => ({
          description: item?.description || '',
          extension: normalizeExtensions(item?.extension),
          type: item?.type || ''
        }))
        .filter((item) => item.description && item.extension.length > 0)
    })
    .catch((error) => console.error(`Error fetching documents only filters: ${error}`))

  return documentsOnlyFilters
}

export function useAllFileTypeFilters() {
  const allFileTypeFilters = ref([])

  authFetch(API_PATHS.allFileTypes)
    .then((res) => {
      if (!res.ok) {
        console.error(`Failed to fetch all file type filters: ${res.statusText}`)
        return
      }
      return res.json()
    })
    .then((data) => {
      if (!Array.isArray(data)) return

      allFileTypeFilters.value = data
        .map((item) => ({
          description: item?.description || '',
          extension: normalizeExtensions(item?.extension),
          type: item?.type || ''
        }))
        .filter((item) => item.description && item.extension.length > 0)
    })
    .catch((error) => console.error(`Error fetching all file type filters: ${error}`))

  return allFileTypeFilters
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
