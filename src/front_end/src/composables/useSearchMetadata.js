/**
 * Composable for extracting and normalizing metadata from search results.
 * Utility functions to resolve filename, document type, and dates etc.
 * Functions are used in other files.
 */

import { computed } from 'vue'

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

export const resolveDocumentType = (entry) => {
  const metadata = getMetadata(entry)

  return pick(metadata?.file_type_description, entry?.file_type_description)
}

export const resolveDocumentExtension = (entry) => {
  const metadata = getMetadata(entry)

  return pick(metadata?.file_type, entry?.file_type)
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
export const useSearchMetadata = (props = {}) => {
  const metadata = computed(() => getMetadata(props.selectedMatch))

  const uniquePointer = computed(() => pick(metadata.value.unique_pointer, props.selectedMatch?.unique_pointer))

  const previewTitle = computed(() => resolveFilename(props.selectedMatch))

  const previewSize = computed(() => pick(metadata.value.size))

  const sourceSystem = computed(() => resolveSource(props.selectedMatch))

  const previewFileDescription = computed(() => resolveDocumentType(props.selectedMatch))

  const previewFileExtension = computed(() => resolveDocumentExtension(props.selectedMatch))

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
    previewFileDescription,
    previewFileExtension,
    previewCreatedAt,
    sourceSystem,
    previewLink,
    previewSecurityClass,
    normalizeMatches,
    resolveSecurityClass,
    resolveDateOnly,
    resolveSource,
    resolveDocumentType,
    resolveDocumentExtension
  }
}
