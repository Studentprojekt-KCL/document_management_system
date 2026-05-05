/* useReload Tests */
import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { useReload, clearAllSearchState } from '@/composables/useReload'

describe('useReload', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  afterEach(() => {
    localStorage.clear()
  })

  describe('state', () => {
    it('initializes with default value when nothing in localStorage', () => {
      const { state } = useReload('test-key', 'default')
      expect(state.value).toBe('default')
    })

    it('restores value from localStorage', () => {
      localStorage.setItem('test-key', JSON.stringify('saved-value'))
      const { state } = useReload('test-key', 'default')
      expect(state.value).toBe('saved-value')
    })

    it('restores complex objects from localStorage', () => {
      const obj = { name: 'test', items: [1, 2, 3] }
      localStorage.setItem('complex-key', JSON.stringify(obj))
      const { state } = useReload('complex-key', {})
      expect(state.value).toEqual(obj)
    })

    it('restores arrays from localStorage', () => {
      localStorage.setItem('arr-key', JSON.stringify([1, 2, 3]))
      const { state } = useReload('arr-key', [])
      expect(state.value).toEqual([1, 2, 3])
    })

    it('restores booleans from localStorage', () => {
      localStorage.setItem('bool-key', JSON.stringify(true))
      const { state } = useReload('bool-key', false)
      expect(state.value).toBe(true)
    })

    it('persists changes to localStorage on set', () => {
      const { state } = useReload('persist-key', 'initial')
      state.value = 'updated'
      expect(JSON.parse(localStorage.getItem('persist-key'))).toBe('updated')
    })

    it('persists complex objects to localStorage', () => {
      const { state } = useReload('obj-key', {})
      state.value = { a: 1, b: [2, 3] }
      expect(JSON.parse(localStorage.getItem('obj-key'))).toEqual({ a: 1, b: [2, 3] })
    })

    it('is reactive — reads updated value after set', () => {
      const { state } = useReload('reactive-key', 'old')
      state.value = 'new'
      expect(state.value).toBe('new')
    })
  })

  describe('clear', () => {
    it('resets state to default value', () => {
      const { state, clear } = useReload('clear-key', 'default')
      state.value = 'changed'
      clear()
      expect(state.value).toBe('default')
    })

    it('removes key from localStorage', () => {
      const { state, clear } = useReload('remove-key', 'default')
      state.value = 'something'
      expect(localStorage.getItem('remove-key')).not.toBeNull()
      clear()
      expect(localStorage.getItem('remove-key')).toBeNull()
    })
  })

  describe('isolation', () => {
    it('different keys are independent', () => {
      const { state: a } = useReload('key-a', 'a')
      const { state: b } = useReload('key-b', 'b')
      a.value = 'changed-a'
      expect(b.value).toBe('b')
    })
  })
})

describe('clearAllSearchState', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  afterEach(() => {
    localStorage.clear()
  })

  it('removes all search-related keys', () => {
    const keys = [
      'searchMatches',
      'searchAllMatches',
      'selectedFile',
      'selectedMatch',
      'lastQuery',
      'isPreviewOpen',
      'aiSummary',
      'aiSummaryHtmlRaw',
      'summaryPointer',
      'summaryError',
      'isGeneratingSummary'
    ]

    keys.forEach((key) => localStorage.setItem(key, 'value'))
    clearAllSearchState()
    keys.forEach((key) => {
      expect(localStorage.getItem(key)).toBeNull()
    })
  })

  it('does not remove unrelated keys', () => {
    localStorage.setItem('unrelated-key', 'keep-me')
    localStorage.setItem('searchMatches', 'remove-me')
    clearAllSearchState()
    expect(localStorage.getItem('unrelated-key')).toBe('keep-me')
  })
})
