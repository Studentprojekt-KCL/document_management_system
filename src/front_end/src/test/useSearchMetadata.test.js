import { describe, test, expect } from 'vitest'
import {
  getMetadata,
  resolveDocumentExtension,
  resolveFilename,
  resolveDocumentType,
  resolveDateOnly,
  resolveSource,
  resolveLink,
  resolveSecurityClass
} from '@/composables/useSearchMetadata'

/* Test valid metadata extraction */
describe('useSearchMetadata', () => {
  /* Unique pointer resolution */
  test('returns unique pointer from metadata', () => {
    const entry = {
      metadata: {
        unique_pointer: 'pointer-1'
      }
    }

    expect(getMetadata(entry)).toEqual({ unique_pointer: 'pointer-1' })
  })

  test('falls back to entry unique pointer', () => {
    const entry = {
      unique_pointer: 'pointer-2'
    }

    expect(getMetadata(entry)).toEqual({ unique_pointer: 'pointer-2' })
  })

  test('returns empty object for no entry', () => {
    const entry = {}

    expect(getMetadata(entry)).toEqual({})
  })

  /* Filename resolution */
  test('uses metadata name when available', () => {
    const entry = {
      metadata: {
        name: 'test.pdf'
      }
    }

    expect(resolveFilename(entry)).toBe('test.pdf')
  })

  test('falls back to entry name', () => {
    const entry = {
      name: 'fallback.pdf'
    }

    expect(resolveFilename(entry)).toBe('fallback.pdf')
  })

  test('returns generated fallback when no name exists', () => {
    const entry = {}

    expect(resolveFilename(entry, 2)).toBe('result-3')
  })

  test('handles missing metadata safely', () => {
    expect(resolveFilename(null)).toBe('result-1')
  })

  /* Document type resolution */
  test('returns Unknown when document type is missing', () => {
    expect(resolveDocumentType({})).toBe('Unknown')
  })

  /* Document extension resolution */
  test('returns Unknown when document extension is missing', () => {
    expect(resolveDocumentExtension({})).toBe('Unknown')
  })

  /* Source system resolution */
  test('returns Unknown when source system is missing', () => {
    const entry = {}
    expect(resolveSource(entry)).toBe('Unknown')
  })

  /* Date resolution */
  test('extracts date correctly', () => {
    const entry = {
      metadata: {
        last_edit_date: '2026-05-07T10:30:00'
      }
    }

    expect(resolveDateOnly(entry)).toBe('2026-05-07')
  })

  test('handles invalid dates safely', () => {
    const entry = {
      metadata: {
        last_edit_date: null
      }
    }

    expect(resolveDateOnly(entry)).toBe('Unknown date')
  })

  /* Clickble link resolution */
  test('returns nothing when clickable url is missing', () => {
    const entry = {}
    expect(resolveLink(entry)).toBe('')
  })

  /* Security classification resolution */
  test('returns Pending when security classifications is pending', () => {
    const entry = {}
    expect(resolveSecurityClass(entry)).toBe('Pending')
  })
})
