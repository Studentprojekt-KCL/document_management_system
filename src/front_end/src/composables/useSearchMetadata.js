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

  return pick(
    metadata?.name,
    metadata?.title,
    metadata?.filename,
    metadata?.file_name,
    metadata?.unique_pointer,
    metadata?.source_file,
    metadata?.clickable_url,
    entry?.filename,
    entry?.name,
    `result-${index + 1}`
  )
}

/* Function to resolve the date from a value. */
const resolveDateOnly = (value) => pick((value || '').split('T')[0])

/* Function to resolve the clickable link from metadata or entry. */
const resolveLink = (entry) => {
  const metadata = getMetadata(entry)

  return pick(metadata?.clickable_url, entry?.clickable_url)
}

const resolveUniquePointer = (entry) => {
  const metadata = getMetadata(entry)

  return pick(metadata?.unique_pointer, entry?.unique_pointer)
}

/* Function to resolve the document type from source type and name. */
const TYPE_KEYWORDS = {
  'PDF Document': ['pdf'],
  'Word Document': ['word', 'doc', 'docx'],
  'Excel Spreadsheet': ['excel', 'sheet', 'xlsx'],
  'Text Document': ['txt'],
  'Markdown Document': ['markdown', 'md']
}

/* Function to resolve the document type from source type and name. */
const resolveDocumentType = ({ sourceType, sourceName }) => {
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
const resolveSource = (entry) => {
  const metadata = getMetadata(entry)

  if (metadata?.unique_pointer) {
    const pointer = metadata.unique_pointer.toLowerCase()
    if (pointer.includes('gitlab')) return 'GitLab'
    if (pointer.includes('github')) return 'GitHub'
    // etc...
    // More sources can be added
  }
}

/**
 * Function to extract and normalize metadata for search results.
 * @param {Object} props - The props object containing the selected match to preview.
 * @returns {Object} An object containing computed properties and utility functions for search metadata.
 */
export const useSearchMetadata = (props) => {
  const metadata = computed(() => getMetadata(props.selectedMatch))

  const previewTitle = computed(() =>
    pick(metadata.value.name, metadata.value.title, metadata.value.filename, metadata.value.file_name, 'Untitled')
  )

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

  const previewCreatedAt = computed(() =>
    resolveDateOnly(
      metadata.value.last_edit_date ||
        metadata.value.edited ||
        metadata.value.updated_at ||
        metadata.value.created_at ||
        metadata.value.date
    )
  )

  const previewSize = computed(() => pick(metadata.value.size, metadata.value.file_size, metadata.value.bytes))

  const previewLink = computed(() => resolveLink(props.selectedMatch))

  const uniquePointer = computed(() => resolveUniquePointer(props.selectedMatch))

  const normalizeMatches = (matches = []) =>
    matches.map((entry, index) => {
      const metadata = getMetadata(entry)
      const filename = resolveFilename(entry, index)

      return {
        rawMatch: entry,
        filename,
        title: pick(metadata?.name, metadata?.title, metadata?.filename, metadata?.file_name, filename),
        type: resolveDocumentType({
          sourceType: entry?.type || metadata?.type || metadata?.file_type || metadata?.source_type,
          sourceName: filename
        })
      }
    })

  const resolveMatchDate = (entry) => {
    const metadata = getMetadata(entry)
    return resolveDateOnly(
      metadata?.last_edit_date || metadata?.edited || metadata?.updated_at || metadata?.created_at || metadata?.date
    )
  }

  return {
    previewTitle,
    previewType,
    previewCreatedAt,
    previewSize,
    previewLink,
    uniquePointer,
    normalizeMatches,
    resolveMatchDate,
    resolveSource
  }
}
