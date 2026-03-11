import { computed } from 'vue'

// Find first non-empty value
export const pick = (...values) => {
  const found = values.find((value) => value !== undefined && value !== null)
  return found ?? ''
}

// Filnamn
export const resolveFilename = (entry, index = 0) => pick(entry?.metadata?.name, `result-${index + 1}`)

// Datum
export const resolveDateOnly = (value) => pick((value || '').split('T')[0])

// Oklart om vi ens ska ha sen men vill kunna se att vi får content atm
export const decodeContent = (encoded) => {
  try {
    return atob(encoded)
  } catch {
    return encoded
  }
}

// Maybe we can get the file type from the header or content later.
const TYPE_KEYWORDS = {
  'PDF Document': ['pdf'],
  'Word Document': ['word', 'doc', 'docx'],
  'Excel Spreadsheet': ['excel', 'sheet', 'xlsx'],
  'Text Document': ['txt'],
  'Markdown Document': ['markdown', 'md']
}

// Har bara hittat markdown och text i test annars returnerar den source_file
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

export const useSearchMetadata = (props) => {
  const metadata = computed(() => props.selectedMatch?.metadata || {})

  const previewTitle = computed(() => pick(metadata.value.name, 'Untitled'))

  const previewType = computed(() => {
    const sourceType = pick(props.selectedMatch?.type, metadata.value.type)
    const sourceName = pick(metadata.value.name, props.selectedFile)

    return resolveDocumentType({ sourceType, sourceName })
  })

  const previewCreatedAt = computed(() => resolveDateOnly(metadata.value.edited))
  const previewSize = computed(() => pick(metadata.value.size))

  const previewSummary = computed(() => {
    const rawText = pick(props.fileContent, props.selectedMatch?.content)
    const decoded = decodeContent(rawText)
    const cleaned = String(decoded).replace(/\s+/g, ' ').trim()
    return cleaned.slice(0, 500) || 'No preview text available'
  })

  const normalizeMatches = (matches = []) =>
    matches.map((entry, index) => {
      const filename = resolveFilename(entry, index)

      return {
        rawMatch: entry,
        filename,
        title: filename,
        type: resolveDocumentType({
          sourceType: entry?.type || entry?.metadata?.type,
          sourceName: filename
        })
      }
    })

  const resolveMatchDate = (entry) => resolveDateOnly(entry?.metadata?.edited)

  return {
    previewTitle,
    previewType,
    previewCreatedAt,
    previewSize,
    previewSummary,
    normalizeMatches,
    resolveMatchDate
  }
}
