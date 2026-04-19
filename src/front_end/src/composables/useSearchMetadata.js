/**
 * Composable for extracting and normalizing metadata from search results.
 * Utility functions to resolve filename, document type, and dates etc.
 * Functions are used in other files.
 */

import { computed, ref } from 'vue'

/* Function to pick the first non-empty value from a list of candidates.*/
const pick = (...values) => {
  const found = values.find((value) => value !== undefined && value !== null && String(value).trim() !== '')
  return found ?? ''
}

/* Function to extract metadata from an entry. */
const getMetadata = (entry) => {
  if (!entry || typeof entry !== 'object') {
    return {}
  }

  if (entry.metadata && typeof entry.metadata === 'object') {
    return entry.metadata
  }

  return entry
}

/* Function to resolve the filename from metadata or entry. Can differ between sources. */
export const resolveFilename = (entry, index = 0) => {
  const metadata = getMetadata(entry)

  return pick(metadata?.name, entry?.name, `result-${index + 1}`)
}

/* Function to resolve the document type from source type and name. */
export const TYPE_KEYWORDS = {
  'PDF Document': ['.pdf'],
  'Word Document': ['word', 'doc', '.docx'],
  'Excel Spreadsheet': ['excel', 'sheet', '.xlsx'],
  'Text Document': ['.txt'],
  'Markdown Document': ['markdown', '.md']
}

/* Used for filtering doc types (SearchView, SearchFilterCard)*/
export const TYPE_FILTERS = {
  'PDF (.pdf)': ['.pdf'],
  'Word (.docx)': ['.doc', '.docx', 'word'],
  'Excel (.xlsx)': ['.xlsx'],
  'Text / Markdown (.txt, .md)': ['.md', '.txt']
}

/* Shared security levels — fetched once, used by SearchFiltersCard and ClassificationEditor */
export const securityLevels = ref([])
let securityFetchPromise = null

export const fetchSecurityLevels = async () => {
  if (securityLevels.value.length > 0) return securityLevels.value
  if (securityFetchPromise) return securityFetchPromise

  const API_BASE_URL = window.__ENV__.API_BASE_URL?.replace(/\/$/, '') ?? ''
  const token = sessionStorage.getItem('access_token')

  securityFetchPromise = fetch(`${API_BASE_URL}/stochastic-analyzer/classifications`, {
    headers: { Authorization: `Bearer ${token}` }
  })
    .then((res) => res.json())
    .then((data) => {
      securityLevels.value = Array.isArray(data) ? data : []
      return securityLevels.value
    })
    .catch(() => {
      securityLevels.value = ['Public', 'Internal', 'Sensitive', 'Confidential']
      return securityLevels.value
    })

  return securityFetchPromise
}

/* Function to resolve the document type from source type and name. */
export const resolveDocumentType = ({ sourceType, sourceName }) => {
  const type = String(sourceType || '').toLowerCase()
  const name = String(sourceName || '').toLowerCase()
  const typeOrName = `${type} ${name}`

  for (const [docType, keywords] of Object.entries(TYPE_KEYWORDS)) {
    if (keywords.some((keyword) => typeOrName.includes(keyword))) {
      return docType
    }
  }

  return pick(sourceType, sourceName)
}

/* Function to resolve the source of the document from metadata. */
export const resolveSource = (entry) => {
  const metadata = getMetadata(entry)

  return pick(metadata?.source_system, entry?.source_system)
}

/* Function to resolve the date from a value. */
export const resolveDateOnly = (entry) => {
  const metadata = getMetadata(entry)
  const value = pick(metadata?.last_edit_date, entry?.last_edit_date)

  return pick((value || '').split('T')[0])
}

/* Function to resolve the clickable link from metadata or entry. */
export const resolveLink = (entry) => {
  const metadata = getMetadata(entry)

  return pick(metadata?.clickable_url, entry?.clickable_url)
}

export const resolveSecurityClass = (entry) => {
  const metadata = getMetadata(entry)

  return pick(metadata?.security_class, entry?.security_class)
}

/**
 * Function to extract and normalize metadata for search results.
 * @param {Object} props - The props object containing the selected match to preview.
 * @returns {Object} An object containing computed properties and utility functions for search metadata.
 */
export const useSearchMetadata = (props) => {
  const metadata = computed(() => getMetadata(props.selectedMatch))

  const uniquePointer = computed(() => pick(metadata.value.unique_pointer, props.selectedMatch?.unique_pointer))

  const previewTitle = computed(() => resolveFilename(props.selectedMatch))

  const previewSize = computed(() => pick(metadata.value.size))

  /* TODO: REMOVE HARDCODED LOCIG LATER */
  const previewType = computed(() => {
    const sourceType = pick(props.selectedMatch?.type, metadata.value.type, metadata.value.file_type, metadata.value.source_type)
    const sourceName = pick(
      metadata.value.name,
      metadata.value.filename,
      metadata.value.file_name,
      metadata.value.unique_pointer,
      metadata.value.source_file,
      metadata.value.clickable_url,
      props.selectedFile
    )

    return resolveDocumentType({ sourceType, sourceName })
  })

  const sourceSystem = computed(() => resolveSource(props.selectedMatch))

  const previewCreatedAt = computed(() => resolveDateOnly(props.selectedMatch))

  const previewLink = computed(() => resolveLink(props.selectedMatch))

  const previewSecurityClass = computed(() => resolveSecurityClass(props.selectedMatch))

  const normalizeMatches = (matches = []) =>
    matches.map((entry, index) => {
      const metadata = getMetadata(entry)
      const filename = resolveFilename(entry, index)

      return {
        rawMatch: entry,
        filename,
        title: pick(metadata?.name, filename),
        type: resolveDocumentType({
          sourceType: entry?.type || metadata?.type,
          sourceName: filename
        })
      }
    })

  return {
    uniquePointer,
    previewTitle,
    previewSize,
    previewType,
    previewCreatedAt,
    sourceSystem,
    previewLink,
    previewSecurityClass,
    normalizeMatches,
    resolveSecurityClass,
    resolveDateOnly,
    resolveSource
  }
}
