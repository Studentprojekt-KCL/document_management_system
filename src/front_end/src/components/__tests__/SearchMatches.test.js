import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'

/* Mock useSearchMetadata */
vi.mock('@/composables/useSearchMetadata', () => {
  const { computed } = require('vue')
  return {
    useSearchMetadata: (props) => ({
      normalizeMatches: (matches = []) =>
        matches.map((entry, index) => ({
          rawMatch: entry,
          filename: entry.name || `result-${index + 1}`,
          title: entry.name || `result-${index + 1}`,
          type: entry.type || 'Unknown'
        })),
      resolveDateOnly: (entry) => (entry?.last_edit_date || '').split('T')[0] || '',
      resolveSource: (entry) => entry?.source_system || '',
      resolveSecurityClass: (entry) => entry?.security_class || ''
    })
  }
})

import SearchMatches from '@/components/SearchMatches.vue'

describe('SearchMatches', () => {
  const mockMatches = [
    {
      name: 'report.pdf',
      type: 'PDF Document',
      last_edit_date: '2026-04-15T14:30:00.000Z',
      source_system: 'GitLab',
      security_class: 'Public'
    },
    {
      name: 'memo.docx',
      type: 'Word Document',
      last_edit_date: '2026-04-14T10:00:00.000Z',
      source_system: 'GitHub',
      security_class: 'Confidential'
    },
    {
      name: 'data.xlsx',
      type: 'Excel Spreadsheet',
      last_edit_date: '2026-04-13T08:00:00.000Z',
      source_system: 'GitLab',
      security_class: 'Internal'
    }
  ]

  const mountMatches = (props = {}) => {
    return mount(SearchMatches, {
      props: {
        matches: [],
        loading: false,
        selected: '',
        query: '',
        ...props
      }
    })
  }

  /* ── Empty / Loading states ── */
  describe('states', () => {
    it('shows "Searching…" when loading', () => {
      const wrapper = mountMatches({ loading: true })
      expect(wrapper.find('.state-text').text()).toBe('Searching…')
    })

    it('does not show results count when loading', () => {
      const wrapper = mountMatches({ loading: true, query: 'test' })
      expect(wrapper.find('.results-count').exists()).toBe(false)
    })

    it('shows no results message when query exists but matches is empty', () => {
      const wrapper = mountMatches({ query: 'something', matches: [] })
      expect(wrapper.find('.results-count').text()).toContain('No results found')
      expect(wrapper.find('.results-count').text()).toContain('something')
    })

    it('shows nothing when there is no query and not loading', () => {
      const wrapper = mountMatches()
      expect(wrapper.find('.state-text').exists()).toBe(false)
      expect(wrapper.find('.results-count').exists()).toBe(false)
    })
  })

  /* ── Results display ── */
  describe('results display', () => {
    it('renders correct number of result cards', () => {
      const wrapper = mountMatches({ matches: mockMatches, query: 'test' })
      expect(wrapper.findAll('.result-item')).toHaveLength(3)
    })

    it('shows results count with correct number', () => {
      const wrapper = mountMatches({ matches: mockMatches, query: 'test' })
      expect(wrapper.find('.results-count').text()).toContain('Found 3 results')
    })

    it('shows singular "result" for single match', () => {
      const wrapper = mountMatches({ matches: [mockMatches[0]], query: 'test' })
      expect(wrapper.find('.results-count').text()).toContain('Found 1 result for')
    })

    it('displays the file title', () => {
      const wrapper = mountMatches({ matches: mockMatches, query: 'test' })
      const titles = wrapper.findAll('.result-title')
      expect(titles[0].text()).toBe('report.pdf')
      expect(titles[1].text()).toBe('memo.docx')
      expect(titles[2].text()).toBe('data.xlsx')
    })

    it('displays file type in metadata row', () => {
      const wrapper = mountMatches({ matches: mockMatches, query: 'test' })
      const firstCard = wrapper.findAll('.result-card')[0]
      expect(firstCard.text()).toContain('PDF Document')
    })

    it('displays date in metadata row', () => {
      const wrapper = mountMatches({ matches: mockMatches, query: 'test' })
      const firstCard = wrapper.findAll('.result-card')[0]
      expect(firstCard.text()).toContain('2026-04-15')
    })

    it('displays source in metadata row', () => {
      const wrapper = mountMatches({ matches: mockMatches, query: 'test' })
      const firstCard = wrapper.findAll('.result-card')[0]
      expect(firstCard.text()).toContain('GitLab')
    })

    it('displays security badge', () => {
      const wrapper = mountMatches({ matches: mockMatches, query: 'test' })
      const badges = wrapper.findAll('.security-badge')
      expect(badges).toHaveLength(3)
      expect(badges[0].text()).toBe('Public')
      expect(badges[1].text()).toBe('Confidential')
      expect(badges[2].text()).toBe('Internal')
    })

    it('applies correct security class to badge', () => {
      const wrapper = mountMatches({ matches: mockMatches, query: 'test' })
      const badges = wrapper.findAll('.security-badge')
      expect(badges[0].classes()).toContain('security-public')
      expect(badges[1].classes()).toContain('security-confidential')
      expect(badges[2].classes()).toContain('security-internal')
    })
  })

  /* ── Selection ── */
  describe('selection', () => {
    it('emits select with raw match when card is clicked', async () => {
      const wrapper = mountMatches({ matches: mockMatches, query: 'test' })

      await wrapper.findAll('.result-card')[0].trigger('click')

      expect(wrapper.emitted('select')).toBeTruthy()
      expect(wrapper.emitted('select')[0][0]).toEqual(mockMatches[0])
    })

    it('emits select with correct match for second item', async () => {
      const wrapper = mountMatches({ matches: mockMatches, query: 'test' })

      await wrapper.findAll('.result-card')[1].trigger('click')

      expect(wrapper.emitted('select')[0][0]).toEqual(mockMatches[1])
    })

    it('highlights the selected card', () => {
      const wrapper = mountMatches({
        matches: mockMatches,
        query: 'test',
        selected: 'report.pdf'
      })

      const cards = wrapper.findAll('.result-card')
      expect(cards[0].classes()).toContain('active')
      expect(cards[1].classes()).not.toContain('active')
    })

    it('no card is highlighted when nothing is selected', () => {
      const wrapper = mountMatches({
        matches: mockMatches,
        query: 'test',
        selected: ''
      })

      const activeCards = wrapper.findAll('.result-card.active')
      expect(activeCards).toHaveLength(0)
    })
  })

  /* ── Edge cases ── */
  describe('edge cases', () => {
    it('handles matches with missing fields gracefully', () => {
      const sparseMatches = [
        { name: 'file.txt' },
        {}
      ]

      const wrapper = mountMatches({ matches: sparseMatches, query: 'test' })
      const items = wrapper.findAll('.result-item')
      expect(items).toHaveLength(2)
    })

    it('shows "Unknown" for missing security class', () => {
      const noSecurity = [{ name: 'file.txt' }]

      const wrapper = mountMatches({ matches: noSecurity, query: 'test' })
      const badge = wrapper.find('.security-badge')
      expect(badge.text()).toBe('Unknown')
    })

    it('includes query text in results label', () => {
      const wrapper = mountMatches({ matches: mockMatches, query: 'keycloak config' })
      expect(wrapper.find('.results-count').text()).toContain('keycloak config')
    })
  })
})