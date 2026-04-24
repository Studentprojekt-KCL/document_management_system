import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'

/* ── Mock dependencies ── */

/* Mock api.js */
const mockAuthFetch = vi.hoisted(() => vi.fn())
vi.mock('@/utils/api', () => ({
  authFetch: mockAuthFetch,
  API_PATHS: {
    search: '/api/search_engine/search'
  },
  FRONTEND_DMISAPI_BASE_URL: '/api'
}))

/* Mock composables */
vi.mock('@/composables/useSearchMetadata', () => ({
  resolveFilename: (entry) => entry?.name || 'unknown',
  resolveDocumentExtension: (entry) => entry?.file_type || '',
  resolveSecurityClass: (entry) => entry?.security_class || ''
}))

/* Mock useReload */
vi.mock('@/composables/useReload', () => {
  const { ref } = require('vue')
  return {
    useReload: (key, defaultValue) => ({
      state: ref(defaultValue),
      clear: vi.fn()
    }),
    clearAllSearchState: vi.fn()
  }
})

/* Stub all child components */
vi.mock('@/components/SearchBar.vue', () => ({
  default: {
    name: 'SearchBar',
    template: '<div class="mock-search-bar" />',
    props: ['loading'],
    emits: ['search']
  }
}))

vi.mock('@/components/SearchFiltersCard.vue', () => ({
  default: {
    name: 'SearchFiltersCard',
    template: '<div class="mock-filters" />',
    props: ['selectedFilters'],
    emits: ['update:filters']
  }
}))

vi.mock('@/components/SearchMatches.vue', () => ({
  default: {
    name: 'SearchMatches',
    template: '<div class="mock-matches" />',
    props: ['matches', 'loading', 'selected', 'query'],
    emits: ['select']
  }
}))

vi.mock('@/components/SearchPreviewDrawer.vue', () => ({
  default: {
    name: 'SearchPreviewDrawer',
    template: '<div class="mock-drawer" />',
    props: ['open', 'selectedFile', 'selectedMatch', 'matches'],
    emits: ['close']
  }
}))

import SearchView from '@/views/SearchView.vue'

describe('SearchView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.setItem('access_token', 'test-token')
    sessionStorage.setItem('access_token', 'test-token')
    vi.spyOn(console, 'log').mockImplementation(() => {})
  })

  afterEach(() => {
    sessionStorage.clear()
    localStorage.clear()
    vi.restoreAllMocks()
  })

  const mountView = () => {
    return mount(SearchView)
  }

  /* Sample search results */
  const mockResults = [
    { name: 'report.pdf', security_class: 'Public', unique_pointer: 'ptr1', file_type: '.pdf' },
    { name: 'memo.docx', security_class: 'Internal', unique_pointer: 'ptr2', file_type: '.docx' },
    { name: 'data.xlsx', security_class: 'Sensitive', unique_pointer: 'ptr3', file_type: '.xlsx' },
    { name: 'readme.md', security_class: 'Public', unique_pointer: 'ptr4', file_type: '.md' },
    { name: 'notes.txt', security_class: 'Confidential', unique_pointer: 'ptr5', file_type: '.txt' }
  ]

  const mockSuccessResponse = () => {
    mockAuthFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResults),
      text: () => Promise.resolve('')
    })
  }

  /* ── Rendering ── */
  describe('rendering', () => {
    it('renders all child components', () => {
      const wrapper = mountView()
      expect(wrapper.findComponent({ name: 'SearchBar' }).exists()).toBe(true)
      expect(wrapper.findComponent({ name: 'SearchFiltersCard' }).exists()).toBe(true)
      expect(wrapper.findComponent({ name: 'SearchMatches' }).exists()).toBe(true)
      expect(wrapper.findComponent({ name: 'SearchPreviewDrawer' }).exists()).toBe(true)
    })

    it('passes loading false to SearchBar initially', () => {
      const wrapper = mountView()
      expect(wrapper.findComponent({ name: 'SearchBar' }).props('loading')).toBe(false)
    })

    it('passes empty matches initially', () => {
      const wrapper = mountView()
      expect(wrapper.findComponent({ name: 'SearchMatches' }).props('matches')).toEqual([])
    })

    it('passes drawer closed initially', () => {
      const wrapper = mountView()
      expect(wrapper.findComponent({ name: 'SearchPreviewDrawer' }).props('open')).toBe(false)
    })
  })

  /* ── Search flow ── */
  describe('search', () => {
    it('fetches results on search event', async () => {
      mockSuccessResponse()
      const wrapper = mountView()
      wrapper.findComponent({ name: 'SearchBar' }).vm.$emit('search', 'test query')
      await flushPromises()

      const [url] = mockAuthFetch.mock.calls[0]
      expect(url).toContain('hello%20world')
    })

    it('encodes the query parameter', async () => {
      mockSuccessResponse()

      const wrapper = mountView()
      wrapper.findComponent({ name: 'SearchBar' }).vm.$emit('search', 'hello world')
      await flushPromises()

      const [url] = mockAuthFetch.mock.calls[0]
      expect(url).toContain('hello%20world')
    })

    it('passes results to SearchMatches after successful search', async () => {
      mockSuccessResponse()

      const wrapper = mountView()
      wrapper.findComponent({ name: 'SearchBar' }).vm.$emit('search', 'test')
      await flushPromises()

      const matches = wrapper.findComponent({ name: 'SearchMatches' })
      expect(matches.props('matches')).toEqual(mockResults)
    })

    it('passes query to SearchMatches', async () => {
      mockSuccessResponse()

      const wrapper = mountView()
      wrapper.findComponent({ name: 'SearchBar' }).vm.$emit('search', 'my query')
      await flushPromises()

      expect(wrapper.findComponent({ name: 'SearchMatches' }).props('query')).toBe('my query')
    })

    it('handles empty search query', async () => {
      const wrapper = mountView()
      wrapper.findComponent({ name: 'SearchBar' }).vm.$emit('search', '')
      await flushPromises()

      expect(mockAuthFetch).not.toHaveBeenCalled()
    })

    it('handles whitespace-only search query', async () => {
      const wrapper = mountView()
      wrapper.findComponent({ name: 'SearchBar' }).vm.$emit('search', '   ')
      await flushPromises()

      expect(mockAuthFetch).not.toHaveBeenCalled()
    })

    it('handles API error response', async () => {
      mockAuthFetch.mockResolvedValue({
        ok: false,
        status: 500,
        text: () => Promise.resolve('Internal Server Error')
      })

      const wrapper = mountView()
      wrapper.findComponent({ name: 'SearchBar' }).vm.$emit('search', 'test')
      await flushPromises()

      expect(wrapper.findComponent({ name: 'SearchMatches' }).props('matches')).toEqual([])
    })

    it('handles network error', async () => {
      mockAuthFetch.mockRejectedValue(new Error('Network error'))

      const wrapper = mountView()
      wrapper.findComponent({ name: 'SearchBar' }).vm.$emit('search', 'test')
      await flushPromises()

      expect(wrapper.findComponent({ name: 'SearchMatches' }).props('matches')).toEqual([])
    })

    it('handles response with nested results property', async () => {
      mockAuthFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ results: mockResults }),
        text: () => Promise.resolve('')
      })

      const wrapper = mountView()
      wrapper.findComponent({ name: 'SearchBar' }).vm.$emit('search', 'test')
      await flushPromises()

      expect(wrapper.findComponent({ name: 'SearchMatches' }).props('matches')).toEqual(mockResults)
    })

    it('handles response with nested matches property', async () => {
      mockAuthFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ matches: mockResults }),
        text: () => Promise.resolve('')
      })

      const wrapper = mountView()
      wrapper.findComponent({ name: 'SearchBar' }).vm.$emit('search', 'test')
      await flushPromises()

      expect(wrapper.findComponent({ name: 'SearchMatches' }).props('matches')).toEqual(mockResults)
    })

    it('resets state before each new search', async () => {
      mockSuccessResponse()

      const wrapper = mountView()
      wrapper.findComponent({ name: 'SearchBar' }).vm.$emit('search', 'first')
      await flushPromises()

      mockAuthFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve([]),
        text: () => Promise.resolve('')
      })

      wrapper.findComponent({ name: 'SearchBar' }).vm.$emit('search', 'second')
      await flushPromises()

      expect(wrapper.findComponent({ name: 'SearchPreviewDrawer' }).props('open')).toBe(false)
    })
  })

  /* ── Match selection ── */
  describe('match selection', () => {
    it('opens the drawer when a match is selected', async () => {
      mockSuccessResponse()

      const wrapper = mountView()
      wrapper.findComponent({ name: 'SearchBar' }).vm.$emit('search', 'test')
      await flushPromises()

      wrapper.findComponent({ name: 'SearchMatches' }).vm.$emit('select', mockResults[0])
      await nextTick()

      expect(wrapper.findComponent({ name: 'SearchPreviewDrawer' }).props('open')).toBe(true)
    })

    it('passes selected match to drawer', async () => {
      mockSuccessResponse()

      const wrapper = mountView()
      wrapper.findComponent({ name: 'SearchBar' }).vm.$emit('search', 'test')
      await flushPromises()

      wrapper.findComponent({ name: 'SearchMatches' }).vm.$emit('select', mockResults[0])
      await nextTick()

      expect(wrapper.findComponent({ name: 'SearchPreviewDrawer' }).props('selectedMatch')).toEqual(mockResults[0])
    })
  })

  /* ── Drawer close ── */
  describe('drawer close', () => {
    it('closes the drawer on close event', async () => {
      mockSuccessResponse()

      const wrapper = mountView()
      wrapper.findComponent({ name: 'SearchBar' }).vm.$emit('search', 'test')
      await flushPromises()

      wrapper.findComponent({ name: 'SearchMatches' }).vm.$emit('select', mockResults[0])
      await nextTick()
      expect(wrapper.findComponent({ name: 'SearchPreviewDrawer' }).props('open')).toBe(true)

      wrapper.findComponent({ name: 'SearchPreviewDrawer' }).vm.$emit('close')
      await nextTick()
      expect(wrapper.findComponent({ name: 'SearchPreviewDrawer' }).props('open')).toBe(false)
    })
  })

  /* ── Filter logic ── */
  describe('filtering', () => {
    beforeEach(() => {
      mockSuccessResponse()
    })

    it('shows all results when no filters are active', async () => {
      const wrapper = mountView()
      wrapper.findComponent({ name: 'SearchBar' }).vm.$emit('search', 'test')
      await flushPromises()

      wrapper.findComponent({ name: 'SearchFiltersCard' }).vm.$emit('update:filters', {
        source: [],
        type: [],
        security: []
      })
      await nextTick()

      expect(wrapper.findComponent({ name: 'SearchMatches' }).props('matches')).toHaveLength(5)
    })

    it('filters by file type extension', async () => {
      const wrapper = mountView()
      wrapper.findComponent({ name: 'SearchBar' }).vm.$emit('search', 'test')
      await flushPromises()

      wrapper.findComponent({ name: 'SearchFiltersCard' }).vm.$emit('update:filters', {
        source: [],
        type: ['.pdf'],
        security: []
      })
      await nextTick()

      const filtered = wrapper.findComponent({ name: 'SearchMatches' }).props('matches')
      expect(filtered).toHaveLength(1)
      expect(filtered[0].name).toBe('report.pdf')
    })

    it('filters by security — Public only', async () => {
      const wrapper = mountView()
      wrapper.findComponent({ name: 'SearchBar' }).vm.$emit('search', 'test')
      await flushPromises()

      wrapper.findComponent({ name: 'SearchFiltersCard' }).vm.$emit('update:filters', {
        source: [],
        type: [],
        security: ['Public']
      })
      await nextTick()

      const filtered = wrapper.findComponent({ name: 'SearchMatches' }).props('matches')
      expect(filtered).toHaveLength(2)
    })

    it('filters by security — Confidential only', async () => {
      const wrapper = mountView()
      wrapper.findComponent({ name: 'SearchBar' }).vm.$emit('search', 'test')
      await flushPromises()

      wrapper.findComponent({ name: 'SearchFiltersCard' }).vm.$emit('update:filters', {
        source: [],
        type: [],
        security: ['Confidential']
      })
      await nextTick()

      const filtered = wrapper.findComponent({ name: 'SearchMatches' }).props('matches')
      expect(filtered).toHaveLength(1)
      expect(filtered[0].name).toBe('notes.txt')
    })

    it('combines type and security filters', async () => {
      const wrapper = mountView()
      wrapper.findComponent({ name: 'SearchBar' }).vm.$emit('search', 'test')
      await flushPromises()

      wrapper.findComponent({ name: 'SearchFiltersCard' }).vm.$emit('update:filters', {
        source: [],
        type: ['.txt', '.md'],
        security: ['Public']
      })
      await nextTick()

      const filtered = wrapper.findComponent({ name: 'SearchMatches' }).props('matches')
      expect(filtered).toHaveLength(1)
      expect(filtered[0].name).toBe('readme.md')
    })

    it('returns empty when no matches pass filters', async () => {
      const wrapper = mountView()
      wrapper.findComponent({ name: 'SearchBar' }).vm.$emit('search', 'test')
      await flushPromises()

      wrapper.findComponent({ name: 'SearchFiltersCard' }).vm.$emit('update:filters', {
        source: [],
        type: ['.pdf'],
        security: ['Confidential']
      })
      await nextTick()

      const filtered = wrapper.findComponent({ name: 'SearchMatches' }).props('matches')
      expect(filtered).toHaveLength(0)
    })

    it('restores all results when filters are cleared', async () => {
      const wrapper = mountView()
      wrapper.findComponent({ name: 'SearchBar' }).vm.$emit('search', 'test')
      await flushPromises()

      wrapper.findComponent({ name: 'SearchFiltersCard' }).vm.$emit('update:filters', {
        source: [],
        type: ['.pdf'],
        security: []
      })
      await nextTick()
      expect(wrapper.findComponent({ name: 'SearchMatches' }).props('matches')).toHaveLength(1)

      wrapper.findComponent({ name: 'SearchFiltersCard' }).vm.$emit('update:filters', {
        source: [],
        type: [],
        security: []
      })
      await nextTick()
      expect(wrapper.findComponent({ name: 'SearchMatches' }).props('matches')).toHaveLength(5)
    })
  })
})
