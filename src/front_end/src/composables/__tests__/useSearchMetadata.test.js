import { describe, it, expect } from 'vitest'
import {
  useSearchMetadata,
  resolveFilename,
  resolveDocumentType,
  resolveDocumentExtension,
  resolveSource,
  resolveDateOnly,
  resolveLink,
  resolveSecurityClass
} from '@/composables/useSearchMetadata'

/* ──────────────────────────────────────────────
   Helper: builds a match object that mirrors
   the shape returned by the search API
   ────────────────────────────────────────────── */
const makeMatch = (overrides = {}, metaOverrides = null) => {
  const base = {
    name: 'report.pdf',
    file_type: 'pdf',
    file_type_description: 'PDF Document',
    source_system: 'SharePoint',
    last_edit_date: '2025-03-12T10:30:00Z',
    clickable_url: 'https://example.com/report.pdf',
    security_class: 'Internal',
    unique_pointer: 'ptr-abc-123',
    size: 204800,
    ...overrides
  }

  if (metaOverrides) {
    return { metadata: { ...base, ...metaOverrides }, ...overrides }
  }

  return base
}

/* ═══════════════════════════════════════════════
   1. Pure utility functions (exported standalone)
   ═══════════════════════════════════════════════ */

describe('resolveFilename', () => {
  it('returns metadata.name when present', () => {
    const entry = { metadata: { name: 'from-meta.docx' }, name: 'from-root.docx' }
    expect(resolveFilename(entry)).toBe('from-meta.docx')
  })

  it('falls back to entry.name when metadata.name is missing', () => {
    const entry = { name: 'root-only.txt' }
    expect(resolveFilename(entry)).toBe('root-only.txt')
  })

  it('returns indexed fallback when no name exists', () => {
    expect(resolveFilename({}, 4)).toBe('result-5')
  })

  it('returns indexed fallback for null entry', () => {
    expect(resolveFilename(null, 0)).toBe('result-1')
  })

  it('ignores whitespace-only names', () => {
    expect(resolveFilename({ name: '   ' }, 2)).toBe('result-3')
  })
})

describe('resolveDocumentType', () => {
  it('returns file_type_description from metadata', () => {
    const entry = { metadata: { file_type_description: 'Word Document' } }
    expect(resolveDocumentType(entry)).toBe('Word Document')
  })

  it('falls back to entry-level file_type_description', () => {
    const entry = { file_type_description: 'Spreadsheet' }
    expect(resolveDocumentType(entry)).toBe('Spreadsheet')
  })

  it('returns empty string when missing', () => {
    expect(resolveDocumentType({})).toBe('')
  })
})

describe('resolveDocumentExtension', () => {
  it('returns file_type from metadata', () => {
    const entry = { metadata: { file_type: 'xlsx' } }
    expect(resolveDocumentExtension(entry)).toBe('xlsx')
  })

  it('falls back to entry-level file_type', () => {
    expect(resolveDocumentExtension({ file_type: 'csv' })).toBe('csv')
  })
})

describe('resolveSource', () => {
  it('returns source_system from metadata', () => {
    const entry = { metadata: { source_system: 'Confluence' } }
    expect(resolveSource(entry)).toBe('Confluence')
  })

  it('falls back to entry-level source_system', () => {
    expect(resolveSource({ source_system: 'Teams' })).toBe('Teams')
  })

  it('returns empty string for missing source', () => {
    expect(resolveSource({})).toBe('')
  })
})

describe('resolveDateOnly', () => {
  it('extracts date portion from ISO datetime', () => {
    expect(resolveDateOnly({ last_edit_date: '2025-03-12T10:30:00Z' })).toBe('2025-03-12')
  })

  it('works with date-only strings', () => {
    expect(resolveDateOnly({ last_edit_date: '2024-01-15' })).toBe('2024-01-15')
  })

  it('reads from metadata.last_edit_date first', () => {
    const entry = {
      metadata: { last_edit_date: '2025-06-01T00:00:00Z' },
      last_edit_date: '2024-01-01T00:00:00Z'
    }
    expect(resolveDateOnly(entry)).toBe('2025-06-01')
  })

  it('returns empty string when no date exists', () => {
    expect(resolveDateOnly({})).toBe('')
  })
})

describe('resolveLink', () => {
  it('returns clickable_url from metadata', () => {
    const entry = { metadata: { clickable_url: 'https://a.com/doc' } }
    expect(resolveLink(entry)).toBe('https://a.com/doc')
  })

  it('falls back to entry-level clickable_url', () => {
    expect(resolveLink({ clickable_url: 'https://b.com' })).toBe('https://b.com')
  })

  it('returns empty string when missing', () => {
    expect(resolveLink({})).toBe('')
  })
})

describe('resolveSecurityClass', () => {
  it('returns security_class from metadata', () => {
    const entry = { metadata: { security_class: 'Confidential' } }
    expect(resolveSecurityClass(entry)).toBe('Confidential')
  })

  it('falls back to entry-level security_class', () => {
    expect(resolveSecurityClass({ security_class: 'Public' })).toBe('Public')
  })

  it('returns empty string when missing', () => {
    expect(resolveSecurityClass({})).toBe('')
  })
})

/* ═══════════════════════════════════════════════
   2. useSearchMetadata composable (computed props)
   ═══════════════════════════════════════════════ */

describe('useSearchMetadata composable', () => {
  const match = makeMatch()

  const createProps = (selectedMatch = null) => ({
    selectedMatch,
    matches: selectedMatch ? [selectedMatch] : []
  })

  it('returns all expected keys', () => {
    const meta = useSearchMetadata(createProps(match))
    const keys = [
      'uniquePointer',
      'previewTitle',
      'previewSize',
      'previewFileDescription',
      'previewFileExtension',
      'previewCreatedAt',
      'sourceSystem',
      'previewLink',
      'previewSecurityClass',
      'normalizeMatches',
      'resolveSecurityClass',
      'resolveDateOnly',
      'resolveSource',
      'resolveDocumentType',
      'resolveDocumentExtension'
    ]
    keys.forEach((key) => {
      expect(meta).toHaveProperty(key)
    })
  })

  describe('computed properties from selectedMatch', () => {
    const meta = useSearchMetadata(createProps(match))

    it('previewTitle resolves filename', () => {
      expect(meta.previewTitle.value).toBe('report.pdf')
    })

    it('previewSize resolves size', () => {
      expect(meta.previewSize.value).toBe(204800)
    })

    it('previewFileDescription resolves document type', () => {
      expect(meta.previewFileDescription.value).toBe('PDF Document')
    })

    it('previewFileExtension resolves extension', () => {
      expect(meta.previewFileExtension.value).toBe('pdf')
    })

    it('previewCreatedAt resolves date only', () => {
      expect(meta.previewCreatedAt.value).toBe('2025-03-12')
    })

    it('sourceSystem resolves source', () => {
      expect(meta.sourceSystem.value).toBe('SharePoint')
    })

    it('previewLink resolves clickable url', () => {
      expect(meta.previewLink.value).toBe('https://example.com/report.pdf')
    })

    it('previewSecurityClass resolves classification', () => {
      expect(meta.previewSecurityClass.value).toBe('Internal')
    })

    it('uniquePointer resolves pointer', () => {
      expect(meta.uniquePointer.value).toBe('ptr-abc-123')
    })
  })

  describe('computed properties with null selectedMatch', () => {
    const meta = useSearchMetadata(createProps(null))

    it('returns empty strings for all fields', () => {
      expect(meta.previewTitle.value).toBe('result-1')
      expect(meta.previewSize.value).toBe('')
      expect(meta.sourceSystem.value).toBe('')
      expect(meta.previewLink.value).toBe('')
      expect(meta.previewSecurityClass.value).toBe('')
    })
  })

  describe('normalizeMatches', () => {
    it('normalizes an array of matches', () => {
      const { normalizeMatches } = useSearchMetadata(createProps())
      const matches = [makeMatch({ name: 'alpha.pdf' }), makeMatch({ name: 'beta.docx' })]
      const result = normalizeMatches(matches)

      expect(result).toHaveLength(2)
      expect(result[0].title).toBe('alpha.pdf')
      expect(result[1].title).toBe('beta.docx')
    })

    it('preserves rawMatch reference', () => {
      const { normalizeMatches } = useSearchMetadata(createProps())
      const original = makeMatch({ name: 'test.txt' })
      const [normalized] = normalizeMatches([original])

      expect(normalized.rawMatch).toBe(original)
    })

    it('assigns indexed filename when name is missing', () => {
      const { normalizeMatches } = useSearchMetadata(createProps())
      const result = normalizeMatches([{}])
      expect(result[0].filename).toBe('result-1')
    })

    it('returns empty array for empty input', () => {
      const { normalizeMatches } = useSearchMetadata(createProps())
      expect(normalizeMatches([])).toEqual([])
    })

    it('returns empty array for undefined input', () => {
      const { normalizeMatches } = useSearchMetadata(createProps())
      expect(normalizeMatches()).toEqual([])
    })
  })
})
