import { describe, it, expect } from 'vitest'
import {
  resolveFilename,
  resolveDocumentType,
  resolveDocumentExtension,
  resolveSource,
  resolveDateOnly,
  resolveLink,
  resolveSecurityClass,
  useSearchMetadata
} from '../useSearchMetadata'

/* ── resolveFilename ── */
describe('resolveFilename', () => {
  it('returns name from metadata object', () => {
    const entry = { metadata: { name: 'report.pdf' } }
    expect(resolveFilename(entry)).toBe('report.pdf')
  })

  it('returns name from entry directly when no metadata wrapper', () => {
    const entry = { name: 'document.txt' }
    expect(resolveFilename(entry)).toBe('document.txt')
  })

  it('returns indexed fallback when no name exists', () => {
    expect(resolveFilename({}, 0)).toBe('result-1')
    expect(resolveFilename({}, 4)).toBe('result-5')
  })

  it('returns result-1 for null or undefined input', () => {
    expect(resolveFilename(null)).toBe('result-1')
    expect(resolveFilename(undefined)).toBe('result-1')
  })

  it('skips empty string names', () => {
    const entry = { metadata: { name: '' }, name: 'fallback.md' }
    expect(resolveFilename(entry)).toBe('fallback.md')
  })

  it('skips whitespace-only names', () => {
    const entry = { metadata: { name: '   ' } }
    expect(resolveFilename(entry, 2)).toBe('result-3')
  })
})

/* ── resolveDocumentType (now reads file_type_description from entry) ── */
describe('resolveDocumentType', () => {
  it('returns file_type_description from metadata', () => {
    const entry = { metadata: { file_type_description: 'PDF Document' } }
    expect(resolveDocumentType(entry)).toBe('PDF Document')
  })

  it('returns file_type_description from entry directly', () => {
    const entry = { file_type_description: 'Word Document' }
    expect(resolveDocumentType(entry)).toBe('Word Document')
  })

  it('returns empty string when no description exists', () => {
    expect(resolveDocumentType({})).toBe('')
  })

  it('handles null input', () => {
    expect(resolveDocumentType(null)).toBe('')
  })

  it('handles undefined input', () => {
    expect(resolveDocumentType(undefined)).toBe('')
  })

  it('prefers metadata value over entry value', () => {
    const entry = { metadata: { file_type_description: 'From metadata' }, file_type_description: 'From entry' }
    expect(resolveDocumentType(entry)).toBe('From metadata')
  })
})

/* ── resolveDocumentExtension ── */
describe('resolveDocumentExtension', () => {
  it('returns file_type from metadata', () => {
    const entry = { metadata: { file_type: '.pdf' } }
    expect(resolveDocumentExtension(entry)).toBe('.pdf')
  })

  it('returns file_type from entry directly', () => {
    const entry = { file_type: '.docx' }
    expect(resolveDocumentExtension(entry)).toBe('.docx')
  })

  it('returns empty string when no file_type exists', () => {
    expect(resolveDocumentExtension({})).toBe('')
  })

  it('handles null input', () => {
    expect(resolveDocumentExtension(null)).toBe('')
  })

  it('handles undefined input', () => {
    expect(resolveDocumentExtension(undefined)).toBe('')
  })
})

/* ── resolveSource ── */
describe('resolveSource', () => {
  it('returns source_system from metadata', () => {
    const entry = { metadata: { source_system: 'GitLab' } }
    expect(resolveSource(entry)).toBe('GitLab')
  })

  it('returns source_system from entry directly', () => {
    const entry = { source_system: 'GitHub' }
    expect(resolveSource(entry)).toBe('GitHub')
  })

  it('returns empty string when no source exists', () => {
    expect(resolveSource({})).toBe('')
  })

  it('handles null input', () => {
    expect(resolveSource(null)).toBe('')
  })
})

/* ── resolveDateOnly ── */
describe('resolveDateOnly', () => {
  it('extracts date from ISO datetime with timezone', () => {
    const entry = { last_edit_date: '2026-04-15T14:30:00.000Z' }
    expect(resolveDateOnly(entry)).toBe('2026-04-15')
  })

  it('extracts date from metadata last_edit_date', () => {
    const entry = { metadata: { last_edit_date: '2026-02-17T08:42:57.000-05:00' } }
    expect(resolveDateOnly(entry)).toBe('2026-02-17')
  })

  it('returns date as-is if no T separator', () => {
    const entry = { last_edit_date: '2026-04-15' }
    expect(resolveDateOnly(entry)).toBe('2026-04-15')
  })

  it('returns empty string when no date exists', () => {
    expect(resolveDateOnly({})).toBe('')
  })

  it('handles null input', () => {
    expect(resolveDateOnly(null)).toBe('')
  })
})

/* ── resolveLink ── */
describe('resolveLink', () => {
  it('returns clickable_url from metadata', () => {
    const entry = { metadata: { clickable_url: 'https://gitlab.com/file' } }
    expect(resolveLink(entry)).toBe('https://gitlab.com/file')
  })

  it('returns clickable_url from entry directly', () => {
    const entry = { clickable_url: 'https://github.com/file' }
    expect(resolveLink(entry)).toBe('https://github.com/file')
  })

  it('returns empty string when no link exists', () => {
    expect(resolveLink({})).toBe('')
  })

  it('handles null input', () => {
    expect(resolveLink(null)).toBe('')
  })
})

/* ── resolveSecurityClass ── */
describe('resolveSecurityClass', () => {
  it('returns security_class from metadata', () => {
    const entry = { metadata: { security_class: 'Confidential' } }
    expect(resolveSecurityClass(entry)).toBe('Confidential')
  })

  it('returns security_class from entry directly', () => {
    const entry = { security_class: 'Public' }
    expect(resolveSecurityClass(entry)).toBe('Public')
  })

  it('returns empty string when no classification exists', () => {
    expect(resolveSecurityClass({})).toBe('')
  })

  it('handles null input', () => {
    expect(resolveSecurityClass(null)).toBe('')
  })
})

/* ── useSearchMetadata composable ── */
describe('useSearchMetadata', () => {
  const createProps = (selectedMatch = null) => ({
    selectedMatch,
    matches: []
  })

  it('returns empty/default values when selectedMatch is null', () => {
    const props = createProps(null)
    const { previewTitle, previewSize, previewLink, previewSecurityClass, uniquePointer } = useSearchMetadata(props)

    expect(previewTitle.value).toBe('result-1')
    expect(previewSize.value).toBe('')
    expect(previewLink.value).toBe('')
    expect(previewSecurityClass.value).toBe('')
    expect(uniquePointer.value).toBe('')
  })

  it('extracts title from match name', () => {
    const props = createProps({ name: 'test_file.py' })
    const { previewTitle } = useSearchMetadata(props)
    expect(previewTitle.value).toBe('test_file.py')
  })

  it('extracts uniquePointer', () => {
    const pointer = 'https://gitlab.com/api/v4/projects/1/repository/files/test.py'
    const props = createProps({ unique_pointer: pointer })
    const { uniquePointer } = useSearchMetadata(props)
    expect(uniquePointer.value).toBe(pointer)
  })

  it('extracts file size', () => {
    const props = createProps({ size: '44982' })
    const { previewSize } = useSearchMetadata(props)
    expect(previewSize.value).toBe('44982')
  })

  it('extracts source system', () => {
    const props = createProps({ source_system: 'GitLab' })
    const { sourceSystem } = useSearchMetadata(props)
    expect(sourceSystem.value).toBe('GitLab')
  })

  it('extracts clickable URL', () => {
    const url = 'https://gitlab.com/project/-/blob/main/file.py'
    const props = createProps({ clickable_url: url })
    const { previewLink } = useSearchMetadata(props)
    expect(previewLink.value).toBe(url)
  })

  it('extracts security class', () => {
    const props = createProps({ security_class: 'Sensitive' })
    const { previewSecurityClass } = useSearchMetadata(props)
    expect(previewSecurityClass.value).toBe('Sensitive')
  })

  it('extracts date from last_edit_date', () => {
    const props = createProps({ last_edit_date: '2026-02-17T08:42:57.000-05:00' })
    const { previewCreatedAt } = useSearchMetadata(props)
    expect(previewCreatedAt.value).toBe('2026-02-17')
  })

  it('extracts file description', () => {
    const props = createProps({ file_type_description: 'PDF Document' })
    const { previewFileDescription } = useSearchMetadata(props)
    expect(previewFileDescription.value).toBe('PDF Document')
  })

  it('extracts file extension', () => {
    const props = createProps({ file_type: '.pdf' })
    const { previewFileExtension } = useSearchMetadata(props)
    expect(previewFileExtension.value).toBe('.pdf')
  })

  /* ── normalizeMatches ── */
  describe('normalizeMatches', () => {
    it('normalizes an array of matches', () => {
      const props = createProps()
      const { normalizeMatches } = useSearchMetadata(props)

      const matches = [
        { name: 'file1.pdf', file_type_description: 'PDF Document' },
        { name: 'file2.md', file_type_description: 'Markdown Document' }
      ]

      const result = normalizeMatches(matches)
      expect(result).toHaveLength(2)
      expect(result[0].title).toBe('file1.pdf')
      expect(result[1].title).toBe('file2.md')
    })

    it('returns empty array for empty input', () => {
      const props = createProps()
      const { normalizeMatches } = useSearchMetadata(props)
      expect(normalizeMatches([])).toEqual([])
    })

    it('returns empty array for undefined input', () => {
      const props = createProps()
      const { normalizeMatches } = useSearchMetadata(props)
      expect(normalizeMatches()).toEqual([])
    })

    it('preserves rawMatch reference', () => {
      const props = createProps()
      const { normalizeMatches } = useSearchMetadata(props)
      const original = { name: 'test.txt', unique_pointer: 'ptr' }
      const result = normalizeMatches([original])
      expect(result[0].rawMatch).toBe(original)
    })

    it('generates fallback filenames with correct index', () => {
      const props = createProps()
      const { normalizeMatches } = useSearchMetadata(props)
      const result = normalizeMatches([{}, {}, {}])
      expect(result[0].filename).toBe('result-1')
      expect(result[1].filename).toBe('result-2')
      expect(result[2].filename).toBe('result-3')
    })
  })
})
