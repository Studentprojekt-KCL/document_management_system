/* SearchMatches Tests */
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import SearchMatches from '@/components/SearchMatches.vue'

/* ──────────────────────────────────────────────
   Mock useSearchMetadata so the component can
   normalise matches without hitting real logic
   ────────────────────────────────────────────── */
vi.mock('@/composables/useSearchMetadata', () => ({
  useSearchMetadata: () => ({
    normalizeMatches: (matches) =>
      (matches || []).map((m, i) => ({
        rawMatch: m,
        filename: m?.metadata?.name || m?.name || `result-${i + 1}`,
        title: m?.metadata?.name || m?.name || `result-${i + 1}`,
        type: m?.metadata?.file_type_description || ''
      })),
    resolveDateOnly: (m) => m?.last_edit_date?.split('T')[0] || 'N/A',
    resolveSource: (m) => m?.source_system || 'Unknown',
    resolveDocumentType: (m) => m?.file_type_description || 'Document',
    resolveSecurityClass: (m) => m?.security_class || 'Unknown'
  }),
  resolveLink: (m) => m?.clickable_url || '#'
}))

/* ──────────────────────────────────────────────
   Helpers
   ────────────────────────────────────────────── */
const makeMatch = (overrides = {}) => ({
  name: 'test-file.pdf',
  file_type_description: 'PDF Document',
  source_system: 'SharePoint',
  last_edit_date: '2025-04-01T12:00:00Z',
  clickable_url: 'https://example.com/test-file.pdf',
  security_class: 'Internal',
  unique_pointer: 'ptr-001',
  ...overrides
})

const defaultProps = {
  matches: [makeMatch(), makeMatch({ name: 'second.docx', unique_pointer: 'ptr-002' })],
  loading: false,
  selected: '',
  query: 'test query'
}

const mountComponent = (props = {}) =>
  mount(SearchMatches, {
    props: { ...defaultProps, ...props },
    global: { stubs: { Calendar: true, FileText: true, ExternalLink: true } }
  })

/* ═══════════════════════════════════════════════ */

describe('SearchMatches.vue', () => {
  /* ─── Rendering ─── */

  describe('rendering', () => {
    it('renders the correct number of result items', () => {
      const wrapper = mountComponent()
      expect(wrapper.findAll('.result-item')).toHaveLength(2)
    })

    it('shows the results count label', () => {
      const wrapper = mountComponent()
      expect(wrapper.find('.results-count').text()).toContain('Found 2 results for "test query"')
    })

    it('shows singular label for one result', () => {
      const wrapper = mountComponent({ matches: [makeMatch()] })
      expect(wrapper.find('.results-count').text()).toContain('1 result')
    })

    it('shows "No results" message when matches is empty', () => {
      const wrapper = mountComponent({ matches: [], query: 'missing' })
      expect(wrapper.find('.results-count').text()).toContain('No results found for "missing"')
    })

    it('shows loading text when loading is true', () => {
      const wrapper = mountComponent({ loading: true })
      expect(wrapper.find('.state-text').text()).toBe('Searching…')
    })

    it('does not show results count when loading', () => {
      const wrapper = mountComponent({ loading: true })
      expect(wrapper.find('.results-count').exists()).toBe(false)
    })

    it('does not show results count when query is empty', () => {
      const wrapper = mountComponent({ query: '' })
      expect(wrapper.find('.results-count').exists()).toBe(false)
    })

    it('renders match titles', () => {
      const wrapper = mountComponent()
      const titles = wrapper.findAll('.result-title')
      expect(titles[0].text()).toBe('test-file.pdf')
      expect(titles[1].text()).toBe('second.docx')
    })
  })

  /* ─── Selection (default mode) ─── */

  describe('selection — default mode (not selectable)', () => {
    it('emits "select" with the raw match on card click', async () => {
      const wrapper = mountComponent()
      await wrapper.findAll('.result-card')[0].trigger('click')

      expect(wrapper.emitted('select')).toHaveLength(1)
      expect(wrapper.emitted('select')[0][0]).toMatchObject({ name: 'test-file.pdf' })
    })
  })

  /* ─── Selectable (multi-select) mode ─── */

  describe('selection — selectable mode', () => {
    const selectableProps = {
      selectable: true,
      selectedPointers: ['ptr-001']
    }

    it('does not emit "select" in selectable mode', async () => {
      const wrapper = mountComponent(selectableProps)
      await wrapper.findAll('.result-card')[0].trigger('click')

      expect(wrapper.emitted('select')).toBeUndefined()
    })

    it('emits update:selectedPointers to remove a pointer when already selected', async () => {
      const wrapper = mountComponent(selectableProps)
      await wrapper.findAll('.result-card')[0].trigger('click')

      const emitted = wrapper.emitted('update:selectedPointers')
      expect(emitted).toHaveLength(1)
      // ptr-001 was selected, clicking it should remove it
      expect(emitted[0][0]).toEqual([])
    })

    it('emits update:selectedPointers to add a pointer when not selected', async () => {
      const wrapper = mountComponent(selectableProps)
      await wrapper.findAll('.result-card')[1].trigger('click')

      const emitted = wrapper.emitted('update:selectedPointers')
      expect(emitted).toHaveLength(1)
      expect(emitted[0][0]).toContain('ptr-002')
      expect(emitted[0][0]).toContain('ptr-001')
    })
  })

  /* ─── Badge modes ─── */

  describe('badge modes', () => {
    it('shows security class in default badge mode', () => {
      const wrapper = mountComponent({ badgeMode: 'security' })
      const badge = wrapper.find('.security-badge')
      expect(badge.text()).toBe('Internal')
    })

    it('shows score in score badge mode', () => {
      const match = makeMatch({ scorePercent: '85.0%' })
      const wrapper = mountComponent({ matches: [match], badgeMode: 'score' })
      const badge = wrapper.find('.security-badge')
      expect(badge.text()).toBe('85.0%')
      expect(badge.classes()).toContain('score-badge')
    })

    it('shows "N/A" when score is missing in score mode', () => {
      const match = makeMatch() // no scorePercent
      const wrapper = mountComponent({ matches: [match], badgeMode: 'score' })
      const badge = wrapper.find('.security-badge')
      expect(badge.text()).toBe('N/A')
    })

    it('shows "Unknown" when security_class is missing', () => {
      const match = makeMatch({ security_class: '' })
      const wrapper = mountComponent({ matches: [match], badgeMode: 'security' })
      const badge = wrapper.find('.security-badge')
      expect(badge.text()).toBe('Unknown')
    })
  })

  /* ─── External link ─── */

  describe('external link', () => {
    it('renders a link to the source with target="_blank"', () => {
      const wrapper = mountComponent()
      const link = wrapper.find('.meta-row a')
      expect(link.attributes('target')).toBe('_blank')
      expect(link.attributes('rel')).toContain('noopener')
    })

    it('stops propagation on link click (does not trigger card select)', async () => {
      const wrapper = mountComponent()
      const link = wrapper.find('.meta-row a')
      await link.trigger('click')

      // The link has @click.stop so it should not emit 'select'
      expect(wrapper.emitted('select')).toBeUndefined()
    })
  })
})
